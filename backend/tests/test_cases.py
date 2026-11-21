import pytest

from app.db.base import AgentExecution, FraudCase, Transaction
from app.services import agents
from app.services.agents import AGENT_ORDER
from tests.test_api import ANOMALOUS, NORMAL

API = "/api/v1"


def make_case(client, headers, world, **over):
    r = client.post(f"{API}/transactions", json={"customer_id": world.id, **{**ANOMALOUS, **over}}, headers=headers).json()
    assert r["case_number"], r
    return r


def investigate(client, headers, txn_id):
    r = client.post(f"{API}/fraud/analyze", json={"transaction_id": txn_id}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def investigated(client, headers, world):
    t = make_case(client, headers, world)
    return t["case_number"], investigate(client, headers, t["id"])


class TestCaseOpening:
    def test_anomalous_opens_case_normal_does_not(self, client, analyst, world):
        assert client.post(f"{API}/transactions", json={"customer_id": world.id, **NORMAL}, headers=analyst).json()["case_number"] is None
        t = make_case(client, analyst, world)
        case = client.get(f"{API}/fraud/cases/{t['case_number']}", headers=analyst).json()
        assert case["status"] == "OPEN" and case["risk_level"] in ("HIGH", "CRITICAL") and not case["has_investigation"]
        assert {i["code"] for i in case["risk_indicators"]} >= {"NEW_DEVICE", "NEW_LOCATION", "UNUSUAL_AMOUNT"}

    def test_lookup_by_id_or_number_and_filters(self, client, analyst, world):
        t = make_case(client, analyst, world)
        by_num = client.get(f"{API}/fraud/cases/{t['case_number']}", headers=analyst).json()
        assert client.get(f"{API}/fraud/cases/{by_num['id']}", headers=analyst).json()["case_number"] == t["case_number"]
        assert client.get(f"{API}/fraud/cases?status=OPEN", headers=analyst).json()["total"] == 1
        assert client.get(f"{API}/fraud/cases?status=ESCALATED", headers=analyst).json()["total"] == 0
        assert client.get(f"{API}/fraud/cases?status=NOPE", headers=analyst).status_code == 422
        assert client.get(f"{API}/fraud/cases/99999", headers=analyst).status_code == 404

    def test_auth_runs_before_lookup(self, client, world):
        # Anonymous callers must get 401 for real AND nonexistent cases alike — never a 404 that reveals what exists.
        for path in ("/fraud/cases/1", "/fraud/cases/FRD-0000-00000", "/investigations/1", "/audit"):
            assert client.get(f"{API}{path}").status_code == 401


class TestAnalyze:
    def test_runs_six_agents_in_order_with_fallback_notice(self, client, analyst, world):
        number, r = investigated(client, analyst, world)
        inv = r["investigation"]
        assert [a["agent"] for a in inv["agents"]] == AGENT_ORDER
        assert inv["ai_recommendation"] in ("ESCALATE_FOR_REVIEW", "BLOCK_AND_INVESTIGATE")
        assert inv["decision_status"] == "PENDING" and inv["case_status"] == "INVESTIGATING"
        assert inv["llm_used"] is False and inv["fallback_notice"] == "AI provider unavailable — running deterministic fallback analysis."
        rag = next(a for a in inv["agents"] if a["agent"] == "rag_policy")
        assert rag["status"] == "completed" and rag["risk_findings"]
        assert inv["policy_citations"] and {"document", "section", "content", "score"} <= set(inv["policy_citations"][0])
        assert set(inv["agents"][0]) == {"agent", "status", "confidence", "risk_findings", "evidence", "execution_time_ms", "used_llm"}

    def test_rerun_replaces_executions_instead_of_accumulating(self, client, analyst, world, db):
        t = make_case(client, analyst, world)
        investigate(client, analyst, t["id"])
        investigate(client, analyst, t["id"])
        assert db.query(AgentExecution).count() == 6 and db.query(FraudCase).count() == 1

    def test_low_risk_shows_reasoning_but_opens_no_case(self, client, analyst, world, db):
        t = client.post(f"{API}/transactions", json={"customer_id": world.id, **NORMAL}, headers=analyst).json()
        r = investigate(client, analyst, t["id"])
        assert r["case_number"] is None and r["investigation"] is None
        assert next(a for a in r["agents"] if a["agent"] == "decision")["risk_findings"][0] == "APPROVE_TRANSACTION"
        assert db.query(FraudCase).count() == 0 and db.query(AgentExecution).count() == 0

    def test_validation_and_unknown_transaction(self, client, analyst):
        assert client.post(f"{API}/fraud/analyze", json={"transaction_id": 99999}, headers=analyst).status_code == 404
        assert client.post(f"{API}/fraud/analyze", json={"transaction_id": 0}, headers=analyst).status_code == 422
        assert client.post(f"{API}/fraud/analyze", json={}, headers=analyst).status_code == 422


class TestHumanDecisions:
    @pytest.mark.parametrize("action,status,audit_action", [("approve", "APPROVED", "RECOMMENDATION_APPROVED"),
                                                            ("escalate", "ESCALATED", "CASE_ESCALATED"),
                                                            ("reject", "REJECTED", "RECOMMENDATION_REJECTED")])
    def test_decision_updates_state_and_is_audited(self, client, analyst, admin, world, action, status, audit_action):
        number, _ = investigated(client, analyst, world)
        r = client.post(f"{API}/investigations/{number}/{action}", json={"notes": "checked with customer"}, headers=analyst)
        assert r.status_code == 200 and r.json()["case_status"] == status and r.json()["decided_by"] == "analyst01"
        entry = client.get(f"{API}/audit?action={audit_action}", headers=admin).json()["items"][0]
        assert (entry["actor"], entry["previous_status"], entry["new_status"]) == ("analyst01", "INVESTIGATING", status)
        assert entry["details"]["notes"] == "checked with customer"

    def test_decision_requires_an_investigation_first(self, client, analyst, world):
        t = make_case(client, analyst, world)
        r = client.post(f"{API}/investigations/{t['case_number']}/approve", headers=analyst)
        assert r.status_code == 409 and "Run the AI investigation" in r.json()["detail"]

    def test_final_decisions_cannot_be_changed_but_escalated_can_be_resolved(self, client, analyst, world):
        number, _ = investigated(client, analyst, world)
        assert client.post(f"{API}/investigations/{number}/escalate", headers=analyst).status_code == 200
        assert client.post(f"{API}/investigations/{number}/escalate", headers=analyst).status_code == 409  # already escalated
        assert client.post(f"{API}/investigations/{number}/reject", headers=analyst).status_code == 200   # escalated -> resolved
        for action in ("approve", "reject", "escalate"):
            assert client.post(f"{API}/investigations/{number}/{action}", headers=analyst).status_code == 409

    def test_rerunning_analysis_never_overwrites_a_final_human_decision(self, client, analyst, world):
        t = make_case(client, analyst, world)
        investigate(client, analyst, t["id"])
        client.post(f"{API}/investigations/{t['case_number']}/approve", headers=analyst)
        again = investigate(client, analyst, t["id"])
        assert again["investigation"]["decision_status"] == "APPROVED" and again["investigation"]["case_status"] == "APPROVED"

    def test_deciding_takes_no_account_action(self, client, analyst, world, db):
        t = make_case(client, analyst, world)
        investigate(client, analyst, t["id"])
        client.post(f"{API}/investigations/{t['case_number']}/approve", headers=analyst)
        db.expire_all()
        assert db.get(Transaction, t["id"]).status == "FLAGGED"  # labelled only; nothing frozen, reversed or blocked


class TestPermissions:
    def test_viewer_is_read_only_and_denial_is_audited(self, client, viewer, analyst, admin, world):
        number, _ = investigated(client, analyst, world)
        assert client.get(f"{API}/fraud/cases", headers=viewer).status_code == 200
        assert client.get(f"{API}/investigations/{number}", headers=viewer).status_code == 200
        assert client.post(f"{API}/investigations/{number}/approve", headers=viewer).status_code == 403
        assert client.post(f"{API}/fraud/analyze", json={"transaction_id": 1}, headers=viewer).status_code == 403
        denied = client.get(f"{API}/audit?action=ACCESS_DENIED", headers=admin).json()
        assert denied["total"] == 2 and denied["items"][0]["actor"] == "viewer01"
        assert denied["items"][0]["details"]["actual_role"] == "VIEWER"

    def test_audit_log_is_for_auditors_and_admins_only(self, client, analyst, auditor, admin, viewer):
        assert client.get(f"{API}/audit", headers=analyst).status_code == 403
        assert client.get(f"{API}/audit", headers=viewer).status_code == 403
        assert client.get(f"{API}/audit", headers=auditor).status_code == 200
        assert client.get(f"{API}/audit", headers=admin).status_code == 200

    def test_auditor_can_read_investigations_but_not_decide(self, client, analyst, auditor, world):
        number, _ = investigated(client, analyst, world)
        assert client.get(f"{API}/investigations/{number}", headers=auditor).status_code == 200
        assert client.post(f"{API}/investigations/{number}/approve", headers=auditor).status_code == 403

    def test_role_change_applies_to_an_already_issued_token(self, client, analyst, users, db):
        from app.db.base import User
        assert client.get(f"{API}/audit", headers=analyst).status_code == 403
        db.query(User).filter(User.username == "analyst01").one().role = "AUDITOR"
        db.commit()
        assert client.get(f"{API}/audit", headers=analyst).status_code == 200  # no re-login needed


class TestAgents:
    def _ctx(self, world, txn, db):
        from app.services.scoring import score_and_store
        return txn, world, score_and_store(db, txn, world)

    def test_critical_blocks_and_low_approves(self, client, analyst, world, db):
        crit = db.get(Transaction, make_case(client, analyst, world)["id"])
        out = agents.run_pipeline(*self._ctx(world, crit, db), prior_cases=0)
        assert out["decision"].risk_findings[0] in ("ESCALATE_FOR_REVIEW", "BLOCK_AND_INVESTIGATE")
        low = db.get(Transaction, client.post(f"{API}/transactions", json={"customer_id": world.id, **NORMAL}, headers=analyst).json()["id"])
        assert agents.run_pipeline(*self._ctx(world, low, db), prior_cases=0)["decision"].risk_findings[0] == "APPROVE_TRANSACTION"

    def test_a_failing_agent_does_not_stop_the_pipeline(self, client, analyst, world, db, monkeypatch):
        def boom(ctx):
            raise RuntimeError("simulated agent failure")
        monkeypatch.setitem(agents._AGENTS, "customer_risk", boom)
        txn = db.get(Transaction, make_case(client, analyst, world)["id"])
        out = agents.run_pipeline(*self._ctx(world, txn, db), prior_cases=0)
        assert out["customer_risk"].status == "failed"
        assert all(out[n].status in ("completed", "unavailable") for n in AGENT_ORDER if n != "customer_risk")
        assert list(out) == AGENT_ORDER


def test_seed_opens_one_case_per_high_or_critical_transaction():
    from app.db.base import Base
    from app.db.seed import seed
    from app.db.session import SessionLocal, engine
    Base.metadata.drop_all(engine)
    result = seed(80, 800, train_model=False)
    db = SessionLocal()
    flagged = db.query(Transaction).filter(Transaction.risk_level.in_(["HIGH", "CRITICAL"])).count()
    assert result["customers"] == 80 and result["cases"] == flagged > 0
    from app.db.base import Account
    assert db.query(Account).filter(Account.account_type == "CUSTOMER").count() == 80  # every customer got a funded account
    assert db.query(Account).filter(Account.account_type == "SYSTEM").count() == 1       # plus the clearing account
    assert seed(80, 800, train_model=False) == {"skipped": True, "accounts_created": 0}  # idempotent, no duplicate accounts
    db.close()
