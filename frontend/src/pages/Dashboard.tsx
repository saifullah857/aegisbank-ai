import { Link } from "react-router-dom";
import { AreaSimple, BarSimple, ChartCard, Donut, LinesTwo } from "../components/charts";
import { Async, Card, PageHeader, RiskBadge, ScoreBar, StatCard, StatusBadge, TableWrap } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { dt, pkr } from "../utils/format";

export default function Dashboard() {
  const s = useAsync(() => api.dashboard(30), []);
  return (
    <>
      <PageHeader title="Dashboard" subtitle="Live fraud-monitoring overview — last 30 days" actions={<button className="btn-secondary" onClick={s.reload}>Refresh</button>} />
      <Async state={s}>
        {(d) => (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatCard label="Total Transactions" value={d.totals.total_transactions} hint="All time" />
              <StatCard label="Suspicious Transactions" value={d.totals.suspicious_transactions} hint="Medium risk or higher" tone="orange" />
              <StatCard label="High Risk Cases" value={d.totals.high_risk_cases} hint={`${d.totals.open_cases} still open`} tone="red" />
              <StatCard label="Cases Under Investigation" value={d.totals.cases_under_investigation} hint={`${d.totals.resolved_cases} resolved`} tone="violet" />
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              <ChartCard title="Fraud cases over time" className="lg:col-span-2" empty={!d.cases_over_time.length}><AreaSimple data={d.cases_over_time} /></ChartCard>
              <ChartCard title="Risk distribution" empty={!d.risk_distribution.some((r) => r.count)}><Donut data={d.risk_distribution} levelColors /></ChartCard>
              <ChartCard title="Fraud by transaction type" empty={!d.fraud_by_transaction_type.length}><BarSimple data={d.fraud_by_transaction_type} horizontal /></ChartCard>
              <ChartCard title="Fraud by location" empty={!d.fraud_by_location.length}><BarSimple data={d.fraud_by_location} color="#1B2A4A" /></ChartCard>
              <ChartCard title="Transaction anomaly trend" empty={!d.anomaly_trend.length}><LinesTwo data={d.anomaly_trend} x="date" a="transactions" b="flagged" aName="Transactions" bName="Flagged (medium+)" /></ChartCard>
            </div>
            <Card title="Recent high-risk cases" pad={false} right={<Link to="/cases" className="text-sm font-medium text-brand-600 hover:underline">View all</Link>}>
              <TableWrap>
                <thead><tr><th className="th">Case</th><th className="th">Customer</th><th className="th">Amount</th><th className="th">Location</th><th className="th">Risk</th><th className="th">Level</th><th className="th">Status</th><th className="th">When</th></tr></thead>
                <tbody className="divide-y divide-ink-100">
                  {d.recent_high_risk_cases.map((c) => (
                    <tr key={c.id} className="hover:bg-ink-50">
                      <td className="td"><Link className="font-medium text-brand-600 hover:underline" to={`/cases/${c.case_number}`}>{c.case_number}</Link></td>
                      <td className="td">{c.customer.name}</td><td className="td tabular-nums">{pkr(c.transaction.amount)}</td><td className="td">{c.transaction.location}</td>
                      <td className="td"><ScoreBar score={c.risk_score} level={c.risk_level} /></td><td className="td"><RiskBadge level={c.risk_level} /></td><td className="td"><StatusBadge status={c.status} /></td><td className="td text-ink-500">{dt(c.transaction.occurred_at)}</td>
                    </tr>
                  ))}
                  {!d.recent_high_risk_cases.length && <tr><td className="td py-8 text-center text-ink-500" colSpan={8}>No cases yet.</td></tr>}
                </tbody>
              </TableWrap>
            </Card>
          </div>
        )}
      </Async>
    </>
  );
}
