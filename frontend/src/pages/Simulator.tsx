import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AgentPipeline } from "../components/AgentPipeline";
import { Async, Card, ErrorState, Field, IndicatorChip, PageHeader, RiskBadge, ScoreBar, Spinner } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api, errorMessage } from "../services/api";
import type { AnalyzeResponse, Txn, TxnDraft } from "../types";
import { pkr, RECOMMENDATION_LABEL, pct } from "../utils/format";
import { useAuth } from "../hooks/useAuth";
import { CAN_INVESTIGATE } from "../utils/format";

const TYPES = ["TRANSFER", "WITHDRAWAL", "DEPOSIT", "CARD_PAYMENT", "BILL_PAYMENT", "ONLINE_PURCHASE"];
const CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Quetta"];
const localInput = (iso: string) => { const d = new Date(iso); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 16); };

export default function Simulator() {
  const { user } = useAuth();
  const customers = useAsync(() => api.customers(1, 100), []);
  const [form, setForm] = useState<TxnDraft | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<{ txn: Txn; analysis: AnalyzeResponse } | null>(null);

  useEffect(() => { if (customers.data && !form) setForm({ customer_id: customers.data.items[0]?.id ?? 0, amount: 10000, transaction_type: "CARD_PAYMENT", merchant: "Al-Fatah Supermarket", merchant_category: "Grocery", location: "Lahore", device_id: "", beneficiary_account: null, occurred_at: new Date().toISOString() }); }, [customers.data, form]);
  const set = <K extends keyof TxnDraft>(k: K, v: TxnDraft[K]) => setForm((f) => (f ? { ...f, [k]: v } : f));

  async function generate(kind: "normal" | "anomalous") {
    if (!form) return;
    setBusy(kind); setErr(null); setResult(null);
    try { setForm(await api.simulate(form.customer_id, kind)); } catch (e) { setErr(errorMessage(e)); } finally { setBusy(null); }
  }
  async function analyze() {
    if (!form) return;
    setBusy("analyze"); setErr(null);
    try {
      const txn = await api.createTransaction({ ...form, occurred_at: new Date(form.occurred_at).toISOString(), beneficiary_account: form.beneficiary_account || null });
      const analysis = await api.analyze(txn.id);
      setResult({ txn, analysis });
    } catch (e) { setErr(errorMessage(e)); } finally { setBusy(null); }
  }
  if (!CAN_INVESTIGATE(user?.role)) return (<><PageHeader title="Transaction Simulator" /><Card><p className="py-10 text-center text-sm text-ink-600">The simulator creates transactions, so it requires the Fraud Analyst or Admin role.</p></Card></>);
  const agents = result?.analysis.investigation?.agents ?? result?.analysis.agents ?? [];

  return (
    <>
      <PageHeader title="Transaction Simulator" subtitle="Build a synthetic transaction from a customer's real baseline, then watch it get scored and investigated"
        actions={<Link to="/demo" className="btn-primary !px-5 !py-2.5 font-semibold tracking-wide">▶ RUN FRAUD INVESTIGATION DEMO</Link>} />
      <Async state={customers}>
        {() => !form ? null : (
          <div className="grid gap-4 lg:grid-cols-5">
            <Card title="Transaction" className="lg:col-span-2">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2"><Field label="Customer"><select className="input" value={form.customer_id} onChange={(e) => set("customer_id", Number(e.target.value))}>{customers.data!.items.map((c) => <option key={c.id} value={c.id}>{c.customer_code} · {c.full_name} ({c.home_city})</option>)}</select></Field></div>
                <Field label="Amount (PKR)"><input className="input" type="number" min={1} value={form.amount} onChange={(e) => set("amount", Number(e.target.value))} /></Field>
                <Field label="Type"><select className="input" value={form.transaction_type} onChange={(e) => set("transaction_type", e.target.value)}>{TYPES.map((t) => <option key={t}>{t}</option>)}</select></Field>
                <Field label="Merchant"><input className="input" value={form.merchant} onChange={(e) => set("merchant", e.target.value)} /></Field>
                <Field label="Merchant category"><input className="input" value={form.merchant_category} onChange={(e) => set("merchant_category", e.target.value)} /></Field>
                <Field label="Location"><select className="input" value={form.location} onChange={(e) => set("location", e.target.value)}>{CITIES.map((c) => <option key={c}>{c}</option>)}</select></Field>
                <Field label="Device ID"><input className="input font-mono text-xs" value={form.device_id} onChange={(e) => set("device_id", e.target.value)} /></Field>
                <Field label="Time"><input className="input" type="datetime-local" value={localInput(form.occurred_at)} onChange={(e) => e.target.value && set("occurred_at", new Date(e.target.value).toISOString())} /></Field>
                <Field label="Beneficiary (optional)"><input className="input font-mono text-xs" value={form.beneficiary_account ?? ""} onChange={(e) => set("beneficiary_account", e.target.value || null)} /></Field>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button className="btn-secondary" onClick={() => generate("normal")} disabled={!!busy}>{busy === "normal" ? "Generating…" : "Generate Normal Transaction"}</button>
                <button className="btn-secondary" onClick={() => generate("anomalous")} disabled={!!busy}>{busy === "anomalous" ? "Generating…" : "Generate Suspicious Transaction"}</button>
                <button className="btn-primary" onClick={analyze} disabled={!!busy || !form.device_id || !form.merchant}>{busy === "analyze" ? <><Spinner className="h-4 w-4" /> Analyzing…</> : "Analyze Transaction"}</button>
              </div>
              {err && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{err}</p>}
              <p className="mt-3 text-xs text-ink-500">Analyzing stores this synthetic transaction, scores it (rules + ML) and runs the six-agent pipeline. Nothing is blocked or frozen.</p>
            </Card>
            <div className="space-y-4 lg:col-span-3">
              {!result ? <Card><p className="py-16 text-center text-sm text-ink-500">Generate or edit a transaction, then click <b>Analyze Transaction</b>.</p></Card> : (
                <>
                  <Card title="Risk result" right={<RiskBadge level={result.analysis.risk_level} />}>
                    <div className="grid grid-cols-3 gap-3 text-center">
                      <div><p className="text-xs text-ink-500">Rule score</p><p className="text-2xl font-semibold">{result.analysis.rule_score ?? "—"}</p></div>
                      <div><p className="text-xs text-ink-500">ML anomaly</p><p className="text-2xl font-semibold">{result.analysis.ml_anomaly_score != null ? result.analysis.ml_anomaly_score.toFixed(2) : "n/a"}</p></div>
                      <div><p className="text-xs text-ink-500">Combined</p><div className="flex justify-center pt-1.5"><ScoreBar score={result.analysis.risk_score} level={result.analysis.risk_level} /></div></div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1">{result.txn.risk_indicators.map((i) => <IndicatorChip key={i.code} code={i.code} />)}{!result.txn.risk_indicators.length && <span className="text-sm text-ink-500">No risk indicators — consistent with the customer's baseline.</span>}</div>
                    <p className="mt-3 text-sm">{pkr(result.txn.amount)} · {result.txn.merchant} · {result.txn.location}</p>
                    {result.analysis.case_number ? <Link className="mt-2 inline-block text-sm font-medium text-brand-600 hover:underline" to={`/cases/${result.analysis.case_number}`}>Open {result.analysis.case_number} to review and decide →</Link> : <p className="mt-2 text-sm text-ink-500">Risk is below HIGH, so no fraud case was opened.</p>}
                  </Card>
                  {result.analysis.investigation && <Card title="AI recommendation"><p className="font-semibold uppercase">{RECOMMENDATION_LABEL[result.analysis.investigation.ai_recommendation]} · {pct(result.analysis.investigation.confidence)}</p><p className="mt-1 text-sm text-ink-600">{result.analysis.investigation.recommendation_reason}</p></Card>}
                  <Card title="Agent pipeline">{(result.analysis.investigation?.fallback_notice ?? result.analysis.fallback_notice) && <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{result.analysis.investigation?.fallback_notice ?? result.analysis.fallback_notice}</p>}<AgentPipeline agents={agents} /></Card>
                </>
              )}
            </div>
          </div>
        )}
      </Async>
      {customers.error && <ErrorState message={customers.error} />}
    </>
  );
}
