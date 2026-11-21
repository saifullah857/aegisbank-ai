"""The six-agent investigation pipeline, orchestrated with LangGraph.

fraud_detection -> transaction_analysis -> customer_risk -> investigation -> rag_policy -> decision

Every agent first produces a deterministic result (this is also the complete fallback). If a Groq key is
configured, five agents may then have their wording refined by the LLM; the refinement is schema-validated
and discarded on ANY problem. Output is only status / concise findings / confidence / evidence — there is no
field for reasoning traces. The final recommendation is advisory: a human analyst decides.
"""
import json
import time
from dataclasses import dataclass, field
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.rag import policy_service
from app.services.llm import get_llm_client

ACTIONS = ["APPROVE_TRANSACTION", "ESCALATE_FOR_REVIEW", "BLOCK_AND_INVESTIGATE"]
LEVEL_TO_ACTION = {"LOW": ACTIONS[0], "MEDIUM": ACTIONS[1], "HIGH": ACTIONS[1], "CRITICAL": ACTIONS[2]}
AGENT_ORDER = ["fraud_detection", "transaction_analysis", "customer_risk", "investigation", "rag_policy", "decision"]
LLM_AGENTS = {"fraud_detection", "transaction_analysis", "customer_risk", "investigation", "decision"}
QUERY_TERMS = {"NEW_DEVICE": "new device account takeover", "NEW_LOCATION": "unusual location", "UNUSUAL_AMOUNT": "unusually large amount high-value",
               "HIGH_VELOCITY": "rapid repeated transactions velocity", "NEW_BENEFICIARY": "new beneficiary transfer",
               "UNUSUAL_MERCHANT": "unusual merchant category", "FAILED_ATTEMPTS": "repeated failed attempts"}


@dataclass
class AgentOutput:
    agent: str
    status: str
    risk_findings: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    execution_time_ms: int = 0
    used_llm: bool = False
    citations: list[dict] = field(default_factory=list)  # persisted with the investigation, not part of agent output


def fraud_detection(ctx) -> AgentOutput:
    r = ctx["risk"]
    evidence = [f"Rule-based score {r.rule.risk_score}/100."]
    if r.ml_score is not None:
        evidence.append(f"ML anomaly score {r.ml_score:.2f} ({'flagged anomalous' if r.ml_is_anomaly else 'within normal range'}).")
    evidence.append(f"Combined score {r.risk_score}/100 ({r.risk_level}).")
    return AgentOutput("fraud_detection", "completed", [f"{f.label}: {f.detail}" for f in r.triggered] or ["No fraud indicators detected."],
                       round(r.risk_score / 100, 2), evidence)


def transaction_analysis(ctx) -> AgentOutput:
    t, c = ctx["txn"], ctx["customer"]
    ratio = float(t.amount) / (float(c.avg_transaction_amount) or 1.0)
    findings = []
    if ratio > 5:
        findings.append(f"Amount is {ratio:.1f}x the customer's average.")
    if t.location not in c.typical_locations:
        findings.append(f"Location '{t.location}' is outside the customer's usual {list(c.typical_locations)}.")
    if t.device_id not in c.known_devices:
        findings.append("Transaction came from a device never seen on this account.")
    if t.occurred_at.hour in (0, 1, 2, 3, 4):
        findings.append(f"Occurred at {t.occurred_at.hour:02d}:00 — inside the 00:00–04:59 high-risk window.")
    if t.beneficiary_account and t.beneficiary_account not in c.known_beneficiaries:
        findings.append("Funds sent to a beneficiary the customer has not used before.")
    return AgentOutput("transaction_analysis", "completed", findings or ["Transaction is consistent with the customer's baseline."],
                       round(min(1.0, len(findings) / 4), 2),
                       [f"{t.transaction_type} of {float(t.amount):,.0f} PKR at {t.merchant} ({t.merchant_category})."])


def customer_risk(ctx) -> AgentOutput:
    prior, c = ctx["prior_cases"], ctx["customer"]
    return AgentOutput("customer_risk", "completed",
                       [f"{prior} prior fraud case(s) on this customer."] if prior else ["Customer has a clean fraud history."],
                       round(min(1.0, 0.3 + 0.2 * prior), 2),
                       [f"Baseline: {len(c.known_devices)} known device(s), locations {list(c.typical_locations)}, "
                        f"average transaction {float(c.avg_transaction_amount):,.0f} PKR."])


def investigation(ctx) -> AgentOutput:
    prior = [ctx["results"][n] for n in ("fraud_detection", "transaction_analysis", "customer_risk")]
    findings, evidence = [], []
    for out in prior:
        findings += [f for f in out.risk_findings if f not in findings]
        evidence += out.evidence
    return AgentOutput("investigation", "completed", findings, round(sum(o.confidence for o in prior) / len(prior), 2), evidence)


def rag_policy(ctx) -> AgentOutput:
    codes = [f.code for f in ctx["risk"].triggered]
    query = " ".join(QUERY_TERMS[c] for c in codes) + f" {ctx['txn'].transaction_type.lower()} escalation recommendation " + ctx["risk"].risk_level
    hits = ctx["retriever"](query.strip(), 3)
    if not hits:
        return AgentOutput("rag_policy", "unavailable", [], 0.0, ["Policy retrieval is unavailable (index not built) — no policies were cited."])
    cites = [{k: h[k] for k in ("document", "policy_id", "slug", "section", "content", "score")} for h in hits]
    return AgentOutput("rag_policy", "completed", [f"{h['document']} — {h['section']} (relevance {h['score']:.2f})" for h in hits],
                       round(hits[0]["score"], 2), [h["content"][:240] for h in hits], citations=cites)


def decision(ctx) -> AgentOutput:
    r, inv = ctx["risk"], ctx["results"]["investigation"]
    action = LEVEL_TO_ACTION[r.risk_level]
    reason = (f"{len(r.triggered)} independent risk indicator(s) at {r.risk_level} risk (score {r.risk_score}/100)."
              if r.triggered else "No risk indicators detected.")
    return AgentOutput("decision", "completed", [action, reason], round(max(inv.confidence, r.risk_score / 100), 2), [reason])


_AGENTS = {"fraud_detection": fraud_detection, "transaction_analysis": transaction_analysis, "customer_risk": customer_risk,
           "investigation": investigation, "rag_policy": rag_policy, "decision": decision}


def _refine_with_llm(name: str, base: AgentOutput, ctx) -> AgentOutput | None:
    """Ask Groq to improve the wording. Returns None (keep deterministic) unless the reply passes validation."""
    r = ctx["risk"]
    system = (f"You are the {name.replace('_', ' ')} agent in a bank fraud-investigation system. Respond ONLY with a JSON object "
              'with keys "risk_findings" (list of at most 5 short strings), "confidence" (number 0-1) and "evidence" (list of short '
              "strings). State conclusions and evidence only — no reasoning steps. The data is synthetic.")
    user = json.dumps({"risk_level": r.risk_level, "risk_score": r.risk_score, "triggered": [f.code for f in r.triggered],
                       "draft_findings": base.risk_findings, "draft_evidence": base.evidence})
    reply = get_llm_client().complete_json(system, user)
    try:
        findings, evidence, conf = reply["risk_findings"], reply["evidence"], float(reply["confidence"])
        if not (isinstance(findings, list) and isinstance(evidence, list) and 0.0 <= conf <= 1.0 and 0 < len(findings) <= 5
                and all(isinstance(x, str) and x for x in findings + evidence)):
            return None
        if name == "decision":  # the action must be a real one and a CRITICAL case must never be waved through
            if findings[0] not in ACTIONS or (r.risk_level in ("HIGH", "CRITICAL") and findings[0] == ACTIONS[0]) \
                    or (r.risk_level == "CRITICAL" and findings[0] != ACTIONS[2]):
                return None
            if len(findings) < 2:
                findings.append(base.risk_findings[1])
        return AgentOutput(name, "completed", findings, round(conf, 2), evidence, used_llm=True)
    except (TypeError, KeyError, ValueError):
        return None


def _run_agent(name: str, ctx) -> AgentOutput:
    start = time.perf_counter()
    try:
        out = _AGENTS[name](ctx)
        if out.status == "completed" and name in LLM_AGENTS and get_llm_client().available:
            out = _refine_with_llm(name, out, ctx) or out
    except Exception as exc:  # one failing agent must never stop the pipeline
        out = AgentOutput(name, "failed", [], 0.0, [f"Agent failed: {type(exc).__name__}"])
    out.execution_time_ms = round((time.perf_counter() - start) * 1000)
    return out


class PipelineState(TypedDict):
    ctx: dict


def _node(name: str):
    def run(state: PipelineState) -> PipelineState:
        ctx = state["ctx"]
        ctx["results"][name] = _run_agent(name, ctx)
        return {"ctx": ctx}
    return run


def _build_graph():
    g = StateGraph(PipelineState)
    for n in AGENT_ORDER:
        g.add_node(n, _node(n))
    g.add_edge(START, AGENT_ORDER[0])
    for a, b in zip(AGENT_ORDER, AGENT_ORDER[1:]):
        g.add_edge(a, b)
    g.add_edge(AGENT_ORDER[-1], END)
    return g.compile()


GRAPH = _build_graph()


def run_pipeline(txn, customer, risk, prior_cases: int, retriever=None) -> dict[str, AgentOutput]:
    ctx = {"txn": txn, "customer": customer, "risk": risk, "prior_cases": prior_cases, "results": {},
           "retriever": retriever or policy_service.retrieve}
    GRAPH.invoke({"ctx": ctx})
    return ctx["results"]
