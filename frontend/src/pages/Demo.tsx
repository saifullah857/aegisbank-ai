import { useEffect, useRef, useState } from "react";
import { AgentPipeline, AgentState } from "../components/AgentPipeline";
import { Citations } from "../components/Citations";
import { DecisionPanel } from "../components/DecisionPanel";
import { Card, ErrorState, IndicatorChip, PageHeader, RiskBadge, Spinner } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { api, errorMessage } from "../services/api";
import type { AnalyzeResponse, DecisionResult, DemoTxn, Investigation } from "../types";
import { CAN_INVESTIGATE, pkr } from "../utils/format";
import { Link } from "react-router-dom";

const AGENTS = ["fraud_detection", "transaction_analysis", "customer_risk", "investigation", "rag_policy", "decision"];
const STAGES = ["Transaction Received", "Risk Analysis", "ML Anomaly Detection", "AI Agents", "Policy Retrieval", "Investigation", "Recommendation", "Human Review"];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** One-click demo. The transaction, scores, agents, citations and recommendation are all REAL backend results; only the reveal is paced. */
export default function Demo() {
  const { user } = useAuth();
  const [fast, setFast] = useState(false);
  const [stage, setStage] = useState(-1);          // index of the stage currently revealed (-1 = idle)
  const [txn, setTxn] = useState<DemoTxn | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>({});
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const runId = useRef(0);
  useEffect(() => () => { runId.current++; }, []);
  useEffect(() => { if (!running) return; const t0 = Date.now() - elapsed * 1000; const t = setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 500); return () => clearInterval(t); /* eslint-disable-next-line */ }, [running]);

  async function run() {
    const id = ++runId.current;
    const alive = () => id === runId.current;
    const pace = (ms: number) => sleep(fast ? 250 : ms);
    setRunning(true); setErr(null); setTxn(null); setAnalysis(null); setAgentStates({}); setStage(-1); setElapsed(0);
    try {
      const t = await api.demoTransaction();                 // real: synthetic anomalous txn, scored by rules + ML
      if (!alive()) return;
      const analysisPromise = api.analyze(t.transaction_id); // real: six-agent pipeline (started now, revealed step by step)
      analysisPromise.catch(() => undefined);
      setTxn(t); setStage(0); await pace(2600); if (!alive()) return;
      setStage(1); await pace(2600); if (!alive()) return;
      setStage(2); await pace(2600); if (!alive()) return;
      setStage(3);
      const a = await analysisPromise; if (!alive()) return;
      setAnalysis(a);
      for (const name of AGENTS) {
        setAgentStates((s) => ({ ...s, [name]: "running" })); await pace(1800); if (!alive()) return;
        setAgentStates((s) => ({ ...s, [name]: "done" }));
      }
      setStage(4); await pace(2600); if (!alive()) return;
      setStage(5); await pace(2600); if (!alive()) return;
      setStage(6); await pace(2600); if (!alive()) return;
      setStage(7);
    } catch (e) { if (alive()) setErr(errorMessage(e)); } finally { if (alive()) setRunning(false); }
  }
  const inv: Investigation | null = analysis?.investigation ?? null;
  // Apply the server's decision answer immediately, then refresh in the background (a failed refresh can no longer hide the result).
  const onDecided = (r?: DecisionResult) => {
    if (!inv) return;
    if (r) setAnalysis((a) => (a?.investigation ? { ...a, investigation: { ...a.investigation, decision_status: r.decision_status, decided_by: r.decided_by, decided_at: r.decided_at ?? new Date().toISOString(), case_status: r.case_status as Investigation["case_status"] } } : a));
    api.investigation(inv.case_number).then((i) => setAnalysis((a) => (a ? { ...a, investigation: i } : a))).catch(() => undefined);
  };

  if (!CAN_INVESTIGATE(user?.role)) return (<><PageHeader title="Fraud Investigation Demo" /><Card><p className="py-10 text-center text-sm text-ink-600">The demo creates and investigates a synthetic transaction, so it requires the Fraud Analyst or Admin role.</p></Card></>);

  return (
    <>
      <PageHeader title="Fraud Investigation Demo" subtitle="A fresh synthetic anomalous transaction runs through rules → ML → six agents → policy RAG → recommendation → you"
        actions={<>
          <label className="flex items-center gap-2 text-sm text-ink-600"><input type="checkbox" checked={fast} onChange={(e) => setFast(e.target.checked)} disabled={running} /> Quick mode</label>
          <button className="btn-primary !px-5 !py-2.5 font-semibold tracking-wide" onClick={run} disabled={running}>{running ? <><Spinner className="h-4 w-4" /> Running… {elapsed}s</> : stage >= 0 ? "▶ RUN AGAIN" : "▶ RUN FRAUD INVESTIGATION DEMO"}</button></>} />
      {err && <ErrorState message={err} onRetry={run} />}
      {stage < 0 && !running && !err && (
        <Card><div className="py-14 text-center"><p className="text-lg font-semibold">Ready when you are</p><p className="mx-auto mt-2 max-w-lg text-sm text-ink-500">Click the button to generate a suspicious synthetic transaction and watch the platform investigate it end to end in about 30 seconds. You make the final decision.</p></div></Card>
      )}
      {(stage >= 0 || running) && (
        <div className="grid gap-4 lg:grid-cols-4">
          <Card title="Progress" className="lg:col-span-1 h-fit">
            <ol className="space-y-0">
              {STAGES.map((s, i) => {
                const done = stage > i || (i === 7 && stage === 7), active = stage === i && !done && running;
                return (
                  <li key={s} className="relative flex items-center gap-3 pb-4 last:pb-0">
                    {i < STAGES.length - 1 && <span className={`absolute left-[11px] top-6 h-full w-0.5 ${stage > i ? "bg-emerald-300" : "bg-ink-100"}`} />}
                    <span className={`relative z-10 flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold ${done ? "bg-emerald-500 text-white" : stage === i ? "bg-brand-500 text-white animate-pulseRing" : "bg-ink-100 text-ink-400"}`}>{done ? "✓" : active ? <Spinner className="h-3.5 w-3.5 text-white" /> : i + 1}</span>
                    <span className={`text-sm ${stage >= i ? "font-medium text-ink-900" : "text-ink-400"}`}>{s}</span>
                  </li>
                );
              })}
            </ol>
          </Card>
          <div className="space-y-4 lg:col-span-3">
            {txn && stage >= 0 && (
              <Card title="Incoming transaction" right={<span className="text-xs text-ink-500">{txn.transaction_ref}</span>}>
                <div className="grid gap-3 text-sm sm:grid-cols-4">
                  <div><p className="text-xs text-ink-500">Customer</p><p className="font-medium">{txn.customer_name}</p></div><div><p className="text-xs text-ink-500">Amount</p><p className="font-semibold text-red-700">{pkr(txn.amount)}</p></div>
                  <div><p className="text-xs text-ink-500">Location</p><p className="font-medium">{txn.location}</p></div><div><p className="text-xs text-ink-500">Case</p><p className="font-medium">{txn.case_number ?? "—"}</p></div>
                </div>
              </Card>
            )}
            {txn && stage >= 1 && <Card title="Rule-based risk analysis" right={<span className="text-sm font-semibold">{txn.rule_score}/100</span>}><div className="flex flex-wrap gap-1.5">{txn.risk_indicators.map((i) => <IndicatorChip key={i.code} code={i.code} />)}</div><ul className="mt-3 space-y-1 text-sm text-ink-700">{txn.risk_indicators.map((i) => <li key={i.code}>+{i.points} · {i.detail}</li>)}</ul></Card>}
            {txn && stage >= 2 && <Card title="ML anomaly detection (Isolation Forest)" right={<RiskBadge level={txn.risk_level} />}>
              <div className="flex items-center gap-6 text-sm"><div><p className="text-xs text-ink-500">Anomaly score</p><p className="text-2xl font-semibold">{txn.ml_anomaly_score != null ? txn.ml_anomaly_score.toFixed(2) : "n/a"}</p></div><div><p className="text-xs text-ink-500">Combined risk (60% rules + 40% ML)</p><p className="text-2xl font-semibold">{txn.risk_score}/100</p></div></div>
              {txn.ml_anomaly_score == null && <p className="mt-2 text-sm text-amber-800">No trained model was found — scoring used the deterministic rule engine only.</p>}</Card>}
            {stage >= 3 && analysis && <Card title="AI agent pipeline" right={<span className="text-xs text-ink-500">{inv?.llm_used ? "LLM-assisted" : "Deterministic"}</span>}>
              {(inv?.fallback_notice) && <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{inv.fallback_notice}</p>}
              <AgentPipeline agents={inv?.agents ?? analysis.agents ?? []} states={agentStates} /></Card>}
            {stage >= 3 && !analysis && !err && <Card><div className="flex items-center gap-3 py-6 text-sm text-ink-500"><Spinner /> Agents are working…</div></Card>}
            {stage >= 4 && inv && <Card title="Policy retrieval (RAG)"><Citations items={inv.policy_citations} unavailable /></Card>}
            {stage >= 5 && inv && <Card title="Investigation summary"><p className="text-sm text-ink-700">{inv.summary}</p><ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink-600">{inv.evidence.slice(0, 6).map((e, i) => <li key={i}>{e}</li>)}</ul></Card>}
            {stage >= 6 && inv && stage < 7 && <Card><p className="text-sm text-ink-600">Recommendation ready — preparing human review…</p></Card>}
            {stage >= 7 && inv && <><DecisionPanel caseNumber={inv.case_number} inv={inv} onDone={onDecided} /><p className="text-sm text-ink-500">{inv.decision_status !== "PENDING" ? <>Decision recorded in the <Link className="text-brand-600 hover:underline" to="/audit">audit log</Link>. · </> : <>Your decision will be recorded in the <Link className="text-brand-600 hover:underline" to="/audit">audit log</Link>. · </>}<Link className="text-brand-600 hover:underline" to={`/cases/${inv.case_number}`}>Open full case</Link></p></>}
            {stage >= 7 && !inv && analysis && <Card><p className="text-sm text-ink-600">This transaction scored below HIGH risk, so no case was opened and no human decision is required.</p></Card>}
          </div>
        </div>
      )}
    </>
  );
}
