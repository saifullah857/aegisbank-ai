"""Customer detail, case timeline, simulator and one-click-demo endpoints; global rate limit."""
from app.db.base import AuditLog

API = "/api/v1"


class TestCustomerDetail:
    def test_detail_with_timeline(self, client, analyst, world):
        r = client.get(f"{API}/customers/{world.id}", headers=analyst)
        assert r.status_code == 200
        b = r.json()
        assert b["customer_code"] == "CUST-T1" and b["total_transactions"] == 6 and len(b["timeline"]) == 6
        assert all(t["known_device"] and t["usual_location"] for t in b["timeline"])

    def test_404_and_auth(self, client, analyst, world):
        assert client.get(f"{API}/customers/9999", headers=analyst).status_code == 404
        assert client.get(f"{API}/customers/{world.id}").status_code == 401


class TestSimulator:
    def test_normal_is_in_baseline_and_not_flagged(self, client, analyst, world):
        d = client.post(f"{API}/simulator/generate", json={"customer_id": world.id, "kind": "normal"}, headers=analyst).json()
        assert d["location"] in world.typical_locations and d["device_id"] in world.known_devices
        r = client.post(f"{API}/transactions", json={k: v for k, v in d.items()}, headers=analyst)
        assert r.status_code == 201 and r.json()["risk_level"] in ("LOW", "MEDIUM")

    def test_anomalous_is_detected_by_the_engine(self, client, analyst, world):
        d = client.post(f"{API}/simulator/generate", json={"customer_id": world.id, "kind": "anomalous"}, headers=analyst).json()
        assert d["location"] not in world.typical_locations and d["device_id"] not in world.known_devices
        r = client.post(f"{API}/transactions", json=d, headers=analyst).json()
        assert r["risk_level"] in ("HIGH", "CRITICAL") and r["case_number"]

    def test_viewer_cannot_generate_and_invalid_kind(self, client, viewer, analyst, world):
        assert client.post(f"{API}/simulator/generate", json={"customer_id": world.id}, headers=viewer).status_code == 403
        assert client.post(f"{API}/simulator/generate", json={"customer_id": world.id, "kind": "bogus"}, headers=analyst).status_code == 422
        assert client.post(f"{API}/simulator/generate", json={"customer_id": 9999}, headers=analyst).status_code == 404


class TestDemo:
    def test_demo_creates_scored_case_and_audits(self, client, analyst, world, db):
        r = client.post(f"{API}/demo/transaction", headers=analyst)
        assert r.status_code == 201
        b = r.json()
        assert b["risk_level"] in ("HIGH", "CRITICAL") and b["case_number"] and b["risk_indicators"]
        assert db.query(AuditLog).filter(AuditLog.action == "DEMO_TRANSACTION_CREATED").count() == 1
        a = client.post(f"{API}/fraud/analyze", json={"transaction_id": b["transaction_id"]}, headers=analyst).json()
        assert [x["agent"] for x in a["investigation"]["agents"]][-1] == "decision"

    def test_demo_without_customers_is_409_and_viewer_403(self, client, analyst, viewer):
        assert client.post(f"{API}/demo/transaction", headers=analyst).status_code == 409
        assert client.post(f"{API}/demo/transaction", headers=viewer).status_code == 403


class TestCaseTimeline:
    def test_focus_is_the_case_transaction(self, client, analyst, world, db):
        d = client.post(f"{API}/simulator/generate", json={"customer_id": world.id, "kind": "anomalous"}, headers=analyst).json()
        case_no = client.post(f"{API}/transactions", json=d, headers=analyst).json()["case_number"]
        tl = client.get(f"{API}/fraud/cases/{case_no}/timeline", headers=analyst).json()["timeline"]
        assert tl[-1]["is_focus"] and tl[-1]["is_anomaly"] and not tl[0]["is_anomaly"]
        assert client.get(f"{API}/fraud/cases/NOPE/timeline", headers=analyst).status_code == 404


def test_global_rate_limit(client, analyst, monkeypatch):
    from app import main
    monkeypatch.setattr(main.settings, "API_RATE_LIMIT_PER_MINUTE", 3)
    main._api_hits.clear()
    codes = [client.get(f"{API}/health").status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[-1] == 429
    main._api_hits.clear()
