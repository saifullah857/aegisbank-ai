import { BarSimple, ChartCard, Donut } from "../components/charts";
import { Async, PageHeader, StatCard } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { LEVEL_COLOR } from "../utils/format";

export default function Analytics() {
  const s = useAsync(() => api.analytics(), []);
  return (
    <>
      <PageHeader title="Fraud Analytics" subtitle="Computed live from the transaction and case tables" actions={<button className="btn-secondary" onClick={s.reload}>Refresh</button>} />
      <Async state={s}>
        {(d) => (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
              <StatCard label="Fraud rate" value={`${d.fraud_rate_percent}%`} hint="Medium risk or higher" tone="orange" />
              <StatCard label="Flagged transactions" value={d.flagged_transactions} tone="red" />
              <StatCard label="Total transactions" value={d.total_transactions} />
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <ChartCard title="Risk score distribution" empty={!d.risk_score_histogram.some((b) => b.count)}><BarSimple data={d.risk_score_histogram} x="bucket" color="#1B2A4A" /></ChartCard>
              <ChartCard title="High-risk transactions over time" empty={!d.high_risk_trend.length}><BarSimple data={d.high_risk_trend} x="date" /></ChartCard>
              <ChartCard title="Fraud by merchant category" empty={!d.fraud_by_merchant_category.length}><BarSimple data={d.fraud_by_merchant_category} horizontal /></ChartCard>
              <ChartCard title="Fraud by device" empty={!d.fraud_by_device_novelty.some((x) => x.count)}><Donut data={d.fraud_by_device_novelty} /></ChartCard>
              <ChartCard title="Fraud by hour of day" empty={!d.fraud_by_hour.some((x) => x.count)}><BarSimple data={d.fraud_by_hour} x="hour" /></ChartCard>
              <ChartCard title="Case resolution status" empty={!d.case_resolution_status.some((x) => x.count)}><BarSimple data={d.case_resolution_status} colorBy={(x: { label: string }) => ({ OPEN: "#3B82F6", INVESTIGATING: "#8B5CF6", ESCALATED: LEVEL_COLOR.HIGH, APPROVED: "#10B981", REJECTED: "#8592AD" }[x.label] ?? "#8592AD")} /></ChartCard>
            </div>
          </div>
        )}
      </Async>
    </>
  );
}
