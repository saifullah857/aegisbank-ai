import base64
import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import Settings, get_settings, validate_production_secrets
from app.core.security import decode_access_token
from tests.conftest import PASSWORD

API = "/api/v1"
NORMAL = dict(amount=8000, transaction_type="CARD_PAYMENT", merchant="Al-Fatah", merchant_category="Grocery",
              location="Lahore", device_id="device-known")
ANOMALOUS = dict(amount=200000, transaction_type="TRANSFER", merchant="Raast", merchant_category="Transfer",
                 location="Quetta", device_id="device-new", beneficiary_account="ACC-9999")


class TestAuth:
    def test_login_ok_and_bad_credentials(self, client, users):
        ok = client.post(f"{API}/auth/login", json={"username": "analyst01", "password": PASSWORD})
        assert ok.status_code == 200 and ok.json()["role"] == "FRAUD_ANALYST"
        for body in ({"username": "analyst01", "password": "nope"}, {"username": "ghost", "password": "x"}):
            r = client.post(f"{API}/auth/login", json=body)
            assert r.status_code == 401 and r.json()["detail"] == "Incorrect username or password"  # same message either way

    def test_protected_endpoints_reject_anonymous_and_garbage_tokens(self, client):
        for path in ("/customers", "/transactions"):
            assert client.get(f"{API}{path}").status_code == 401
            assert client.get(f"{API}{path}", headers={"Authorization": "Bearer not.a.token"}).status_code == 401

    def test_deactivated_users_token_stops_working(self, client, users, db):
        h = {"Authorization": client.post(f"{API}/auth/login", json={"username": "viewer01", "password": PASSWORD}).json()["access_token"]}
        h = {"Authorization": f"Bearer {h['Authorization']}"}
        assert client.get(f"{API}/customers", headers=h).status_code == 200
        from app.db.base import User
        db.query(User).filter(User.username == "viewer01").one().is_active = False
        db.commit()
        assert client.get(f"{API}/customers", headers=h).status_code == 401


class TestTransactions:
    def test_normal_transaction_scores_low(self, client, analyst, world):
        r = client.post(f"{API}/transactions", json={"customer_id": world.id, **NORMAL}, headers=analyst)
        assert r.status_code == 201 and r.json()["risk_level"] == "LOW" and r.json()["status"] == "COMPLETED"

    def test_anomalous_transaction_is_flagged_not_blocked(self, client, analyst, world):
        r = client.post(f"{API}/transactions", json={"customer_id": world.id, **ANOMALOUS}, headers=analyst).json()
        assert r["risk_level"] in ("HIGH", "CRITICAL") and r["status"] == "FLAGGED"
        assert {i["code"] for i in r["risk_indicators"]} >= {"NEW_DEVICE", "NEW_LOCATION", "UNUSUAL_AMOUNT", "NEW_BENEFICIARY"}

    @pytest.mark.parametrize("override,code", [({"amount": -1}, 422), ({"amount": 0}, 422), ({"transaction_type": "BOGUS"}, 422),
                                               ({"merchant": ""}, 422), ({"customer_id": 9999}, 404)])
    def test_invalid_requests(self, client, analyst, world, override, code):
        assert client.post(f"{API}/transactions", json={"customer_id": world.id, **NORMAL, **override}, headers=analyst).status_code == code

    def test_viewer_can_read_but_not_create(self, client, viewer, world):
        assert client.get(f"{API}/transactions", headers=viewer).status_code == 200
        assert client.post(f"{API}/transactions", json={"customer_id": world.id, **NORMAL}, headers=viewer).status_code == 403

    def test_list_filter_and_pagination_limits(self, client, analyst, world):
        client.post(f"{API}/transactions", json={"customer_id": world.id, **ANOMALOUS}, headers=analyst)
        assert client.get(f"{API}/transactions?risk_level=CRITICAL", headers=analyst).json()["total"] + \
               client.get(f"{API}/transactions?risk_level=HIGH", headers=analyst).json()["total"] == 1
        assert client.get(f"{API}/transactions?page_size=1000", headers=analyst).status_code == 422


class TestJwtHardening:
    def claims(self):
        return {"sub": "admin", "role": "ADMIN", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}

    def test_round_trip(self):
        from app.core.security import create_access_token
        assert decode_access_token(create_access_token("admin", "ADMIN"))["sub"] == "admin"

    def test_alg_none_rejected(self):
        b = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()  # noqa: E731
        assert decode_access_token(f"{b({'alg': 'none', 'typ': 'JWT'})}.{b({'sub': 'admin', 'exp': 9999999999})}.") is None

    def test_wrong_secret_other_algorithm_and_expired_rejected(self):
        s = get_settings()
        assert decode_access_token(jwt.encode(self.claims(), "attacker-guess-" + "y" * 30, algorithm="HS256")) is None
        assert decode_access_token(jwt.encode(self.claims(), s.JWT_SECRET, algorithm="HS512")) is None  # right secret, unpinned alg
        expired = {**self.claims(), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}
        assert decode_access_token(jwt.encode(expired, s.JWT_SECRET, algorithm="HS256")) is None


class TestProductionSecretGuard:
    def test_placeholders_and_short_secrets_rejected_in_production(self):
        for bad in ("CHANGE_ME_IN_ENV", "replace-with-a-long-random-secret", "REPLACE_ME", "short"):
            with pytest.raises(RuntimeError, match="JWT_SECRET"):
                validate_production_secrets(Settings(_env_file=None, ENVIRONMENT="production", JWT_SECRET=bad))

    def test_strong_secret_ok_and_dev_unaffected(self):
        validate_production_secrets(Settings(_env_file=None, ENVIRONMENT="production", JWT_SECRET="x" * 48))
        validate_production_secrets(Settings(_env_file=None, ENVIRONMENT="development", JWT_SECRET="CHANGE_ME_IN_ENV"))
