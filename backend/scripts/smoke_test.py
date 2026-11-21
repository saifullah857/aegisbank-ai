"""End-to-end smoke test against a RUNNING API (CI integration + post-deploy check).

    API_URL=http://localhost:8000/api/v1 python scripts/smoke_test.py
Exits non-zero on the first failed expectation."""

import json
import os
import sys
import urllib.request as u

B = os.environ.get("API_URL", "http://localhost:8000/api/v1")


def call(m, p, body=None, tok=None):
    h = {"content-type": "application/json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    r = u.Request(
        B + p,
        method=m,
        headers=h,
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with u.urlopen(r) as x:
            return x.status, json.loads(x.read())
    except u.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


PW = os.environ.get("DEMO_PASSWORD", "AegisDemo123!")
def login(n):
    return call("POST", "/auth/login", {"username": n, "password": PW})[1]["access_token"]


def expect(label, got, want):
    print(f"{label}: {got}")
    if got != want:
        print(f"FAILED: {label} expected {want!r}, got {got!r}")
        sys.exit(1)


A, AU, V = login("analyst01"), login("auditor01"), login("viewer01")
s, d = call("POST", "/demo/transaction", tok=A)
expect("demo transaction (201)", s, 201)
assert d["risk_level"] in ("HIGH", "CRITICAL") and d["case_number"], d
s, a = call("POST", "/fraud/analyze", {"transaction_id": d["transaction_id"]}, tok=A)
inv = a["investigation"]
expect("analyze (200)", s, 200)
assert [x["agent"] for x in inv["agents"]] == [
    "fraud_detection",
    "transaction_analysis",
    "customer_risk",
    "investigation",
    "rag_policy",
    "decision",
]
print(
    "agents", [(x["agent"], x["status"], x["execution_time_ms"]) for x in inv["agents"]]
)
print(
    "rec",
    inv["ai_recommendation"],
    inv["confidence"],
    "| notice:",
    inv["fallback_notice"],
)
print(
    "citations",
    [
        c["document"] + " / " + c["section"] + " " + str(c["score"])
        for c in inv["policy_citations"]
    ],
)
s, t = call("GET", "/fraud/cases/%s/timeline" % a["case_number"], tok=A)
print("timeline", s, len(t["timeline"]), "focus:", t["timeline"][-1]["is_focus"])
expect(
    "escalate",
    call(
        "POST",
        "/investigations/%s/escalate" % a["case_number"],
        {"notes": "smoke"},
        tok=A,
    )[1]["case_status"],
    "ESCALATED",
)
expect(
    "approve",
    call("POST", "/investigations/%s/approve" % a["case_number"], {}, tok=A)[1][
        "decision_status"
    ],
    "APPROVED",
)
expect(
    "reject after final (409)",
    call("POST", "/investigations/%s/reject" % a["case_number"], {}, tok=A)[0],
    409,
)
s, au = call("GET", "/audit?page_size=5", tok=AU)
print(
    "audit(auditor)",
    s,
    [
        (r["actor"], r["action"], r["previous_status"], r["new_status"])
        for r in au["items"]
    ],
)
expect("audit as analyst (403)", call("GET", "/audit", tok=A)[0], 403)
expect(
    "auditor decide (403)",
    call("POST", "/investigations/%s/approve" % a["case_number"], {}, tok=AU)[0],
    403,
)
expect("viewer demo (403)", call("POST", "/demo/transaction", tok=V)[0], 403)
expect("no token (401)", call("GET", "/fraud/cases")[0], 401)
s, dsh = call("GET", "/dashboard/stats", tok=A)
print("dash", dsh["totals"])
s, hl = call("GET", "/system/health", tok=A)
print(
    "health", hl["overall_status"], [(x["name"], x["status"]) for x in hl["services"]]
)
expect(
    "bad login (401)",
    call("POST", "/auth/login", {"username": "x", "password": "y"})[0],
    401,
)
print(
    "customer detail",
    call("GET", "/customers/%d" % d["customer_id"], tok=A)[1]["total_transactions"],
)
print(
    "policy search",
    [
        r["document"]
        for r in call(
            "GET", "/policies/search?q=new%20device%20account%20takeover", tok=A
        )[1]["results"]
    ][:2],
)
