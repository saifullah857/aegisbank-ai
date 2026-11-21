import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AgentPipeline, AgentState } from "../components/AgentPipeline";
import { Citations } from "../components/Citations";
import { DecisionPanel } from "../components/DecisionPanel";
import { Timeline } from "../components/Timeline";
import { Async, Card, KV, PageHeader, RiskBadge, StatusBadge } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { useAsync } from "../hooks/useAsync";
import { api, errorMessage, statusOf } from "../services/api";
import type { Investigation } from "../types";
import { CAN_INVESTIGATE, dt, pkr } from "../utils/format";

const ORDER = ["fraud_detection", "transaction_analysis", "customer_risk", "investigation", "rag_policy", "decision"];

export default function CaseDetail() {
  const { ref = "" } = useParams();
  const { user } = useAuth();
  const c = useAsync(() => api.case(ref), [ref]);
  const tl = useAsync(() => api.caseTimeline(ref), [ref]);
  const [inv, setInv] = useState<Investigation | null>(null);
  const [invLoading, setInvLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [step, setStep] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const timer = useRef<number>();

  const loadInv = () => {
    setInvLoading(true);
    api.investigation(ref).then(setInv).catch((e) => { if (statusOf(e) === 404) setInv(null); else setErr(errorMessage(e)); }).finally(() => setInvLoading(false));
  };
  useEffect(() => { setInv(null); loadInv(); /* eslint-disable-next-line */ }, [ref]);
  useEffect(() => () => window.clearInterval(timer.current), []);

  async function run() {
    if (!c.data) return;
    setRunning(true); setErr(null); setStep(0);
    timer.current = window.setInterval(() => setStep((s) => Math.min(s + 1, ORDER.length - 1)), 600);
    try { const r = await api.analyze(c.data.transaction.id); if (r.investigation) setInv(r.investigation); c.reload(); tl.reload(); }
    catch (e) { setErr(errorMessage(e)); } finally { window.clearInterval(timer.current); setRunning(false); }
  }
  const states: Record<string, AgentState> = Object.fromEntries(ORDER.map((n, i) => [n, i < step ? "done" : i === step ? "running" : "pending"]));
  const canRun = CAN_INVESTIGATE(user?.role);
  const finalDecision = inv && (inv.decision_status === "APPROVED" || inv.decision_status === "REJECTED");

  return (
    <>
      <Async state={c}>
        {(k) => {
          const t = k.transaction;
          return (
            <div className="space-y-4">
              <PageHeader crumbs={[{ label: "Fraud Cases", to: "/cases" }, { label: k.case_number }]} title={k.case_number}
                subtitle={`Opened ${dt(k.created_at)}`}
                actions={<><RiskBadge level={k.risk_level} /><StatusBadge status={k.status} />
                  {canRun && !finalDecision && <button className="btn-primary" onClick={run} disabled={running}>{running ? "Investigating…" : inv ? "Re-run AI investigation" : "Run AI investigation"}</button>}</>} />
              {err && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{err}</p>}
              <div className="grid gap-4 lg:grid-cols-3">
                <Card title="Risk assessment">
                  <div className="flex items-end gap-2"><span className="text-5xl font-semibold tabular-nums text-ink-900">{k.risk_score}</span><span className="pb-1.5 text-sm text-ink-500">/ 100</span></div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink-100"><div className={`h-full ${k.risk_level === "CRITICAL" ? "bg-red-600" : "bg-brand-500"}`} style={{ width: `${k.risk_score}%` }} /></div>
                  <p className="mt-3 text-xs text-ink-500">Combined score: 60% deterministic rules + 40% Isolation Forest anomaly score.</p>
                  <h4 className="mb-1 mt-4 text-[11px] font-semibold uppercase tracking-wide text-ink-500">Why it was flagged</h4>
                  <ul className="space-y-2">{k.risk_indicators.map((i) => (
                    <li key={i.code} className="rounded-lg bg-red-50 px-3 py-2 text-sm"><div className="flex justify-between font-semibold text-red-800"><span>{i.label}</span><span>+{i.points}</span></div><p className="mt-0.5 text-xs text-red-900/80">{i.detail}</p></li>))}</ul>
                </Card>
                <Card title="Transaction" className="lg:col-span-1">
                  <dl className="divide-y divide-ink-50">
                    <KV k="Transaction" v={t.ref} /><KV k="Amount" v={<span className="text-base font-semibold">{pkr(t.amount)}</span>} /><KV k="Type" v={t.type} /><KV k="Merchant" v={t.merchant} />
                    <KV k="Location" v={t.location} /><KV k="Device" v={<span className="font-mono text-xs">{t.device_id}</span>} /><KV k="Beneficiary" v={t.beneficiary_account ? <span className="font-mono text-xs">{t.beneficiary_account}</span> : "—"} /><KV k="Timestamp" v={dt(t.occurred_at)} />
                  </dl>
                </Card>
                <Card title="Customer">
                  <dl className="divide-y divide-ink-50"><KV k="Name" v={<Link className="text-brand-600 hover:underline" to={`/customers/${k.customer.id}`}>{k.customer.name}</Link>} /><KV k="Customer ID" v={k.customer.code} /><KV k="Home city" v={k.customer.home_city} /><KV k="Status" v={<StatusBadge status={k.status} />} /></dl>
                  <p className="mt-3 text-xs text-ink-500">Fund movement and account freezes are never automated; this case only records analyst decisions.</p>
                </Card>
              </div>
              <Card title="Customer timeline" right={<span className="text-xs text-ink-500">Anomaly highlighted</span>}>
                <Async state={tl}>{(d) => <Timeline items={d.timeline} />}</Async>
              </Card>
              <Card title="AI investigation" right={inv && <span className="text-xs text-ink-500">{inv.llm_used ? "LLM-assisted" : "Deterministic analysis"}</span>}>
                {invLoading && !running ? <p className="text-sm text-ink-500">Loading…</p> : running ? <AgentPipeline agents={[]} states={states} /> : !inv ? (
                  <div className="py-8 text-center"><p className="text-sm font-medium text-ink-800">No investigation has been run for this case yet.</p>
                    <p className="mt-1 text-sm text-ink-500">{canRun ? "Run the six-agent pipeline to get evidence, cited policy and a recommendation." : "A fraud analyst needs to run the investigation."}</p></div>
                ) : (
                  <div className="space-y-5">
                    {inv.fallback_notice && <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{inv.fallback_notice}</p>}
                    <AgentPipeline agents={inv.agents} />
                    <div><h3 className="mb-2 text-sm font-semibold">Retrieved policy sources</h3><Citations items={inv.policy_citations} unavailable={inv.agents.find((a) => a.agent === "rag_policy")?.status !== "completed"} /></div>
                    <DecisionPanel caseNumber={k.case_number} inv={inv} onDone={() => { loadInv(); c.reload(); }} />
                  </div>
                )}
              </Card>
            </div>
          );
        }}
      </Async>
    </>
  );
}
