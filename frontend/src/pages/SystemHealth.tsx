import { useEffect } from "react";
import { Async, Card, PageHeader, StatCard } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

const DOT = { ONLINE: "bg-emerald-500", DEGRADED: "bg-amber-500", OFFLINE: "bg-red-500" } as const;
const PILL = { ONLINE: "bg-emerald-50 text-emerald-700 ring-emerald-200", DEGRADED: "bg-amber-50 text-amber-700 ring-amber-200", OFFLINE: "bg-red-50 text-red-700 ring-red-200" } as const;
const uptime = (s: number) => (s < 3600 ? `${Math.round(s / 60)} min` : `${(s / 3600).toFixed(1)} h`);

export default function SystemHealth() {
  const s = useAsync(() => api.health(), []);
  useEffect(() => { const t = setInterval(s.reload, 15000); return () => clearInterval(t); /* eslint-disable-next-line */ }, []);
  return (
    <>
      <PageHeader title="System Health" subtitle="Live service checks — refreshes every 15 seconds" actions={<button className="btn-secondary" onClick={s.reload}>Refresh</button>} />
      <Async state={s}>
        {(d) => (
          <div className="space-y-4">
            <div className="flex items-center gap-3"><span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ring-1 ring-inset ${PILL[d.overall_status]}`}><span className={`h-2 w-2 rounded-full ${DOT[d.overall_status]}`} />Platform {d.overall_status}</span><span className="text-xs text-ink-500">Uptime {uptime(d.metrics.uptime_seconds)}</span></div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {d.services.map((x) => (
                <Card key={x.name}><div className="flex items-center justify-between"><h3 className="font-semibold">{x.name}</h3><span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${PILL[x.status]}`}><span className={`h-1.5 w-1.5 rounded-full ${DOT[x.status]}`} />{x.status}</span></div><p className="mt-2 text-sm text-ink-500">{x.detail}</p></Card>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatCard label="CPU" value={`${d.metrics.cpu_percent}%`} />
              <StatCard label="Memory" value={`${d.metrics.memory_percent}%`} hint={`${d.metrics.memory_used_mb} / ${d.metrics.memory_total_mb} MB`} />
              <StatCard label="API latency (avg / p95)" value={d.metrics.api_latency_ms_avg != null ? `${d.metrics.api_latency_ms_avg} ms` : "—"} hint={d.metrics.api_latency_ms_p95 != null ? `p95 ${d.metrics.api_latency_ms_p95} ms` : undefined} />
              <StatCard label="Requests" value={d.metrics.request_count} hint="Since last restart" />
              <StatCard label="Error rate" value={`${d.metrics.error_rate_percent}%`} hint="HTTP 5xx" tone={d.metrics.error_rate_percent > 1 ? "red" : "ink"} />
              <StatCard label="Agent execution time" value={d.metrics.agent_avg_execution_time_ms != null ? `${d.metrics.agent_avg_execution_time_ms} ms` : "—"} hint="Average per agent" tone="orange" />
              <StatCard label="Agent executions" value={d.metrics.agent_execution_count} />
            </div>
          </div>
        )}
      </Async>
    </>
  );
}
