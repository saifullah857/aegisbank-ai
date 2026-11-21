import { Async, Card, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { pct } from "../utils/format";

export default function Agents() {
  const s = useAsync(() => api.agents(), []);
  return (
    <>
      <PageHeader title="AI Agents" subtitle="Six-agent LangGraph pipeline — structured findings and evidence only, never reasoning traces" />
      <Async state={s}>
        {(d) => (
          <div className="space-y-4">
            <div className={`rounded-lg px-4 py-3 text-sm ${d.llm_configured ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>
              {d.llm_configured ? `LLM provider (${d.llm_provider}) is configured. Agent wording may be refined by the LLM; every result is schema-validated and falls back to deterministic output on any problem.` : "AI provider unavailable — running deterministic fallback analysis. All agents still work end-to-end."}
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {d.agents.map((a) => (
                <Card key={a.name}>
                  <div className="flex items-start gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink-900 text-sm font-bold text-white">{a.order}</span>
                    <div><h3 className="font-semibold">{a.display_name}</h3><p className="mt-0.5 text-sm text-ink-500">{a.description}</p></div>
                  </div>
                  <dl className="mt-4 grid grid-cols-3 gap-2 border-t border-ink-100 pt-3 text-center">
                    <div><dd className="text-lg font-semibold tabular-nums">{a.total_runs}</dd><dt className="text-[11px] text-ink-500">Runs</dt></div>
                    <div><dd className="text-lg font-semibold tabular-nums">{a.avg_confidence != null ? pct(a.avg_confidence) : "—"}</dd><dt className="text-[11px] text-ink-500">Avg confidence</dt></div>
                    <div><dd className="text-lg font-semibold tabular-nums">{a.avg_execution_time_ms != null ? `${a.avg_execution_time_ms} ms` : "—"}</dd><dt className="text-[11px] text-ink-500">Avg time</dt></div>
                  </dl>
                  <p className="mt-2 text-xs text-ink-500">{a.llm_runs} LLM-refined · {a.deterministic_runs} deterministic</p>
                </Card>
              ))}
            </div>
          </div>
        )}
      </Async>
    </>
  );
}
