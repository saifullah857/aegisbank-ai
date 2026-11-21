import json
from datetime import datetime, timezone
from types import SimpleNamespace as NS

import httpx
import numpy as np
import pytest
from sqlalchemy.exc import OperationalError

from app.db.base import Transaction
from app.db.session import get_db
from app.main import app
from app.ml import inference
from app.ml.features import FEATURE_NAMES, extract_features
from app.ml.model import AnomalyDetector
from app.rag import policy_service
from app.rag.chunking import load_all
from app.services import agents
from app.services.llm import GroqClient, set_llm_client
from app.services.scoring import assess
from tests.test_cases import API, investigate, make_case

NOW = datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc)
CUST = NS(avg_transaction_amount=10000, known_devices=["d1"], typical_locations=["Lahore"], known_beneficiaries=["A1"])


def T(**kw):
    base = dict(amount=9000, device_id="d1", location="Lahore", beneficiary_account=None, merchant_category="Grocery", status="COMPLETED", occurred_at=NOW)
    return NS(**{**base, **kw})


# ------------------------------------------------------------------------------------------------ ML
class TestMachineLearning:
    def _detector(self):
        rng = np.random.default_rng(0)
        normal = [[9000 + rng.normal(0, 800), rng.normal(0, 0.3), 1, 14, 0, 0, 1] for _ in range(300)]
        outliers = [[250000, 24, 4, 3, 1, 1, 3], [300000, 29, 5, 2, 1, 1, 4], [280000, 27, 4, 1, 1, 1, 3.5]]
        return AnomalyDetector(contamination=0.02).fit(normal + outliers), len(normal)

    def test_features_capture_the_signals(self):
        f = dict(zip(FEATURE_NAMES, extract_features(T(device_id="new", location="Quetta", amount=200000, occurred_at=NOW.replace(hour=3)), CUST)))
        assert (f["device_novelty"], f["location_deviation"], f["hour_of_day"]) == (1.0, 1.0, 3.0) and f["amount_deviation"] > 15
        burst = [T(occurred_at=NOW.replace(minute=m)) for m in (2, 5)]
        assert dict(zip(FEATURE_NAMES, extract_features(T(), CUST, burst)))["velocity_15min"] == 3

    def test_detector_separates_outliers_and_round_trips(self, tmp_path):
        det, n = self._detector()
        X = [[9000, 0, 1, 14, 0, 0, 1], [280000, 27, 4, 1, 1, 1, 3.5]]
        s = det.normalized_scores(X)
        assert s[0] < 0.4 < 0.6 < s[1]
        det.save(tmp_path / "m.joblib")
        assert list(AnomalyDetector.load(tmp_path / "m.joblib").normalized_scores(X)) == list(s)
        with pytest.raises(RuntimeError):
            AnomalyDetector().normalized_scores(X)

    def test_blend_is_60_40_and_degrades_to_rules_without_a_model(self):
        txn = T(device_id="new", location="Quetta", amount=80000, beneficiary_account="A9")
        rules_only = assess(txn, CUST)
        assert rules_only.ml_score is None and rules_only.risk_score == rules_only.rule.risk_score == 75
        det, _ = self._detector()
        blended = assess(txn, CUST, detector=det)
        assert blended.ml_score is not None
        assert blended.risk_score == min(100, round(0.6 * 75 + 0.4 * blended.ml_score * 100))

    def test_seed_trains_a_model_and_finds_the_injected_anomalies(self):
        from app.db.base import Base, Customer
        from app.db.seed import seed
        from app.db.session import SessionLocal, engine
        Base.metadata.drop_all(engine)
        res = seed(150, 1500)
        assert inference.model_path().exists() and res["cases"] > 0
        db = SessionLocal()
        cust = {c.id: c for c in db.query(Customer).all()}
        txns = db.query(Transaction).all()
        gt = {t.id for t in txns if t.device_id not in cust[t.customer_id].known_devices and t.location not in cust[t.customer_id].typical_locations
              and float(t.amount) > 8 * float(cust[t.customer_id].avg_transaction_amount)}
        caught = {t.id for t in txns if t.risk_level in ("HIGH", "CRITICAL")} & gt
        assert gt and len(caught) / len(gt) >= 0.9
        assert all(t.ml_anomaly_score is not None for t in txns)
        db.close()
        Base.metadata.drop_all(engine)


# ------------------------------------------------------------------------------------------------ RAG
class TestPolicyRetrieval:
    def test_five_documents_with_metadata(self):
        chunks = load_all()
        assert {c.category for c in chunks} == {"Transaction Monitoring", "Escalation", "Account Security", "Verification", "Card Fraud"}
        assert all(c.policy_id and c.section and c.content for c in chunks)

    @pytest.mark.parametrize("query,expected", [("stolen card unauthorised purchases", "Card Fraud"),
                                                ("how fast must critical cases be reviewed", "Escalation"),
                                                ("verify customer identity before release", "Verification"),
                                                ("new device account takeover", "Account Security")])
    def test_retrieves_the_relevant_policy(self, query, expected):
        hits = policy_service.retrieve(query, 3)
        assert expected in hits[0]["document"] and all(0 <= h["score"] <= 1 for h in hits)
        assert [h["score"] for h in hits] == sorted((h["score"] for h in hits), reverse=True)

    def test_missing_index_degrades_gracefully_and_pipeline_continues(self, client, analyst, world, monkeypatch):
        monkeypatch.setattr(policy_service, "retrieve", lambda q, k=3: [])
        r = investigate(client, analyst, make_case(client, analyst, world)["id"])["investigation"]
        by = {a["agent"]: a for a in r["agents"]}
        assert by["rag_policy"]["status"] == "unavailable" and by["decision"]["status"] == "completed" and r["policy_citations"] == []


# ------------------------------------------------------------------------------------------------ Groq
def completion(payload) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": payload if isinstance(payload, str) else json.dumps(payload)}}]})


def use_llm(handler):
    calls = []
    set_llm_client(GroqClient("test-key", "m", transport=httpx.MockTransport(lambda req: (calls.append(req), handler(req))[1])))
    return calls


GOOD = {"risk_findings": ["BLOCK_AND_INVESTIGATE", "LLM-worded reason"], "confidence": 0.93, "evidence": ["LLM evidence"]}


class TestGroqIntegration:
    def run(self, client, analyst, world):
        return investigate(client, analyst, make_case(client, analyst, world)["id"])["investigation"]

    def test_valid_replies_are_used_and_reported(self, client, analyst, world):
        calls = use_llm(lambda req: completion(GOOD))
        inv = self.run(client, analyst, world)
        by = {a["agent"]: a for a in inv["agents"]}
        assert len(calls) == 5 and calls[0].headers["authorization"] == "Bearer test-key"
        assert all(by[n]["used_llm"] for n in agents.LLM_AGENTS) and not by["rag_policy"]["used_llm"]
        assert inv["llm_used"] is True and inv["fallback_notice"] is None and inv["ai_recommendation"] == "BLOCK_AND_INVESTIGATE"

    @pytest.mark.parametrize("handler", [lambda r: completion("this is not json"),
                                         lambda r: httpx.Response(500, json={"error": "boom"}),
                                         lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("slow")),
                                         lambda r: completion({"risk_findings": ["x"], "confidence": 5, "evidence": []}),
                                         lambda r: completion({"unexpected": "shape"}), lambda r: completion([1, 2, 3])])
    def test_any_llm_failure_falls_back_to_deterministic(self, client, analyst, world, handler):
        use_llm(handler)
        inv = self.run(client, analyst, world)
        assert not any(a["used_llm"] for a in inv["agents"]) and inv["llm_used"] is False
        assert inv["fallback_notice"] == "AI provider unavailable — running deterministic fallback analysis."
        assert [a["status"] for a in inv["agents"]].count("failed") == 0 and inv["ai_recommendation"] in ("ESCALATE_FOR_REVIEW", "BLOCK_AND_INVESTIGATE")

    def test_llm_cannot_wave_through_a_high_risk_case(self, client, analyst, world):
        use_llm(lambda r: completion({"risk_findings": ["APPROVE_TRANSACTION", "looks fine"], "confidence": 0.99, "evidence": ["e"]}))
        inv = self.run(client, analyst, world)
        by = {a["agent"]: a for a in inv["agents"]}
        assert not by["decision"]["used_llm"] and inv["ai_recommendation"] != "APPROVE_TRANSACTION"  # rejected, deterministic kept

    def test_invented_action_is_rejected(self, client, analyst, world):
        use_llm(lambda r: completion({"risk_findings": ["FREEZE_ACCOUNT", "do it"], "confidence": 0.9, "evidence": ["e"]}))
        inv = self.run(client, analyst, world)
        assert inv["ai_recommendation"] in agents.ACTIONS and inv["ai_recommendation"] != "FREEZE_ACCOUNT"

    def test_no_key_means_no_network_call(self, client, analyst, world):
        calls = []
        set_llm_client(GroqClient(None, "m", transport=httpx.MockTransport(lambda r: calls.append(r) or completion(GOOD))))
        self.run(client, analyst, world)
        assert calls == []


# ------------------------------------------------------------------------------------------------ insights
class TestDashboardAndInsights:
    def test_stats_are_aggregated_from_the_database(self, client, analyst, world):
        empty = client.get(f"{API}/dashboard/stats", headers=analyst).json()
        assert empty["totals"]["total_cases"] == 0 and empty["totals"]["total_transactions"] == 6
        t = make_case(client, analyst, world)
        investigate(client, analyst, t["id"])
        s = client.get(f"{API}/dashboard/stats", headers=analyst).json()
        tot = s["totals"]
        assert (tot["total_transactions"], tot["total_cases"], tot["cases_under_investigation"], tot["open_cases"]) == (7, 1, 1, 0)
        assert sum(x["count"] for x in s["risk_distribution"]) == 1  # only the scored transaction
        assert s["fraud_by_location"] == [{"label": "Quetta", "count": 1}] and s["fraud_by_transaction_type"] == [{"label": "TRANSFER", "count": 1}]
        assert s["recent_high_risk_cases"][0]["case_number"] == t["case_number"] and s["cases_over_time"]
        assert client.get(f"{API}/dashboard/stats?days=0", headers=analyst).status_code == 422

    def test_analytics(self, client, analyst, world):
        a0 = client.get(f"{API}/dashboard/analytics", headers=analyst).json()
        assert a0["fraud_rate_percent"] == 0 and len(a0["fraud_by_hour"]) == 24 and [s["count"] for s in a0["case_resolution_status"]] == [0] * 5
        make_case(client, analyst, world)
        a = client.get(f"{API}/dashboard/analytics", headers=analyst).json()
        assert a["flagged_transactions"] == 1 and a["fraud_rate_percent"] == round(1 / 7 * 100, 2)
        assert sum(h["count"] for h in a["fraud_by_hour"]) == 1 and sum(b["count"] for b in a["risk_score_histogram"]) == 1
        assert a["fraud_by_device_novelty"] == [{"label": "New device", "count": 1}, {"label": "Known device", "count": 0}]
        assert a["fraud_by_merchant_category"] == [{"label": "Transfer", "count": 1}]

    def test_agents_registry_reflects_real_runs(self, client, analyst, world):
        before = client.get(f"{API}/agents", headers=analyst).json()
        assert [a["name"] for a in before["agents"]] == agents.AGENT_ORDER and before["mode"] == "deterministic_fallback"
        investigate(client, analyst, make_case(client, analyst, world)["id"])
        after = client.get(f"{API}/agents", headers=analyst).json()
        assert all(a["total_runs"] == 1 and a["deterministic_runs"] == 1 for a in after["agents"])

    def test_policies_list_detail_search_and_citation_counts(self, client, analyst, world):
        lst = client.get(f"{API}/policies", headers=analyst).json()
        assert len(lst) == 5 and all(p["sections"] and p["description"] for p in lst)
        assert client.get(f"{API}/policies/{lst[0]['id']}", headers=analyst).json()["full_sections"]
        assert client.get(f"{API}/policies/nope", headers=analyst).status_code == 404
        found = client.get(f"{API}/policies/search?q=stolen card", headers=analyst).json()
        assert found["rag_available"] and "Card Fraud" in found["results"][0]["document"]
        assert client.get(f"{API}/policies/search?q=x", headers=analyst).status_code == 422
        assert sum(p["relevant_cases"] for p in lst) == 0
        investigate(client, analyst, make_case(client, analyst, world)["id"])
        assert sum(p["relevant_cases"] for p in client.get(f"{API}/policies", headers=analyst).json()) >= 1

    def test_system_health_reports_real_checks(self, client, analyst, world):
        client.get(f"{API}/customers", headers=analyst)
        h = client.get(f"{API}/system/health", headers=analyst).json()
        by = {s["name"]: s for s in h["services"]}
        assert set(by) == {"API", "PostgreSQL", "Redis", "AI Service (groq)", "Vector DB (ChromaDB)", "Agent Orchestrator"}
        assert by["PostgreSQL"]["status"] == "ONLINE" and by["Vector DB (ChromaDB)"]["status"] == "ONLINE"
        assert by["AI Service (groq)"]["status"] == "OFFLINE" and by["Redis"]["status"] == "OFFLINE"   # honestly unconfigured
        assert h["overall_status"] == "ONLINE"  # optional services being absent must not mark the platform down
        assert h["metrics"]["request_count"] >= 1 and 0 <= h["metrics"]["cpu_percent"] <= 100 and h["metrics"]["memory_used_mb"] > 0

    def test_all_insight_endpoints_require_auth(self, client):
        for p in ("/dashboard/stats", "/dashboard/analytics", "/agents", "/policies", "/policies/search?q=abc", "/system/health"):
            assert client.get(f"{API}{p}").status_code == 401


# ------------------------------------------------------------------------------------------------ security & resilience
class TestSecurityAndResilience:
    def test_security_headers(self, client):
        r = client.get(f"{API}/health")
        assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
        assert r.headers["cache-control"] == "no-store" and "default-src 'none'" in r.headers["content-security-policy"]

    def test_login_is_rate_limited(self, client, users, monkeypatch):
        import app.main as main
        monkeypatch.setattr(main.settings, "LOGIN_RATE_LIMIT_PER_MINUTE", 3)
        main._login_attempts.clear()
        codes = [client.post(f"{API}/auth/login", json={"username": "analyst01", "password": "wrong"}).status_code for _ in range(5)]
        assert codes == [401, 401, 401, 429, 429]
        assert client.post(f"{API}/auth/login", json={"username": "analyst01", "password": "wrong"}).headers["retry-after"] == "60"
        main._login_attempts.clear()

    def test_readiness_vs_liveness(self, client):
        assert client.get(f"{API}/health/ready").json() == {"status": "ready"}

        class Broken:
            def execute(self, *a, **k):
                raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        app.dependency_overrides[get_db] = lambda: (yield Broken())
        r = client.get(f"{API}/health/ready")
        assert r.status_code == 503 and "refused" not in r.text
        assert client.get(f"{API}/health").status_code == 200  # liveness unaffected by a DB outage

    def test_database_outage_is_a_clean_503(self, client):
        def broken():
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))
            yield
        app.dependency_overrides[get_db] = broken
        r = client.get(f"{API}/customers", headers={"Authorization": "Bearer x"})
        assert r.status_code == 503 and r.json()["code"] == "database_unavailable" and "refused" not in r.text


def test_alembic_migrations_apply_and_match_the_models(tmp_path, monkeypatch):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/migrated.db")
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(cfg, "head")
    command.check(cfg)  # raises if the models have drifted from the migrations


def test_langgraph_pipeline_runs_agents_in_the_declared_order():
    nodes = [n for n in agents.GRAPH.get_graph().nodes if not n.startswith("__")]
    assert sorted(nodes) == sorted(agents.AGENT_ORDER)
