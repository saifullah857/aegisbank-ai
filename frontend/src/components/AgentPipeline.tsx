import { useState } from "react";
import type { AgentResult } from "../types";
import { AGENT_LABEL, pct } from "../utils/format";
import { Spinner } from "./ui";

export type AgentState = "pending" | "running" | "done";
const ORDER = ["fraud_detection", "transaction_analysis", "customer_risk", "investigation", "rag_policy", "decision"];

/** Vertical agent pipeline: status, confidence, findings, evidence, execution time. No reasoning traces exist in the data. */
export function AgentPipeline({ agents, states }: { agents: AgentResult[]; states?: Record<string, AgentState> }) {
  const [open, setOpen] = useState<string | null>(null);
  const byName = Object.fromEntries(agents.map((a) => [a.agent, a]));
  return (
    <ol className="space-y-2">
      {ORDER.map((name, i) => {
        const a = byName[name];
        const st: AgentState = states ? states[name] ?? "pending" : a ? "done" : "pending";
        const shown = st === "done" && a;
        const bad = a && a.status !== "completed";
        return (
          <li key={name} className={`animate-fadeUp rounded-lg border bg-white ${st === "running" ? "border-brand-300 ring-2 ring-brand-100" : bad ? "border-amber-200" : "border-ink-100"}`}>
            <button className="flex w-full items-center gap-3 px-3 py-2.5 text-left" onClick={() => shown && setOpen(open === name ? null : name)} disabled={!shown} aria-expanded={open === name}>
              <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${st === "done" ? (bad ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700") : st === "running" ? "bg-brand-50" : "bg-ink-100 text-ink-400"}`}>
                {st === "running" ? <Spinner className="h-4 w-4" /> : st === "done" ? (bad ? "!" : "✓") : i + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium text-ink-900">{AGENT_LABEL[name]}</span>
                <span className="block text-xs text-ink-500">
                  {st === "pending" && "Waiting"}{st === "running" && "Running…"}
                  {shown && `${a.status === "completed" ? "Completed" : a.status === "unavailable" ? "Unavailable — continued safely" : "Failed — continued safely"} · confidence ${pct(a.confidence)} · ${a.execution_time_ms} ms${a.used_llm ? " · LLM-refined" : " · deterministic"}`}
                </span>
              </span>
              {shown && <span className="text-xs text-ink-400">{open === name ? "Hide" : "Details"}</span>}
            </button>
            {shown && open === name && (
              <div className="grid gap-3 border-t border-ink-100 px-4 py-3 text-sm md:grid-cols-2">
                <div><h4 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-ink-500">Risk findings</h4>
                  {a.risk_findings.length ? <ul className="list-disc space-y-1 pl-4 text-ink-800">{a.risk_findings.map((f, k) => <li key={k}>{f}</li>)}</ul> : <p className="text-ink-500">None</p>}</div>
                <div><h4 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-ink-500">Evidence</h4>
                  {a.evidence.length ? <ul className="list-disc space-y-1 pl-4 text-ink-700">{a.evidence.map((f, k) => <li key={k}>{f}</li>)}</ul> : <p className="text-ink-500">None</p>}</div>
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
