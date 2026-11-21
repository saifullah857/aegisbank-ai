import { Link, useParams } from "react-router-dom";
import { Timeline } from "../components/Timeline";
import { Async, Card, KV, PageHeader, RiskBadge, StatusBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { pkr } from "../utils/format";

export default function CustomerDetail() {
  const { id = "" } = useParams();
  const s = useAsync(() => api.customer(id), [id]);
  return (
    <Async state={s}>
      {(c) => (
        <>
          <PageHeader crumbs={[{ label: "Customers", to: "/customers" }, { label: c.customer_code }]} title={c.full_name} subtitle={`${c.customer_code} · ${c.home_city}`} />
          <div className="grid gap-4 lg:grid-cols-3">
            <Card title="Behavioural baseline">
              <dl className="divide-y divide-ink-50">
                <KV k="Average transaction" v={pkr(c.avg_transaction_amount)} /><KV k="Typical locations" v={c.typical_locations.join(", ")} /><KV k="Known devices" v={c.known_devices.length} />
                <KV k="Known beneficiaries" v={c.known_beneficiaries_count} /><KV k="Transactions" v={c.total_transactions} /><KV k="High / critical flags" v={c.flagged_transactions} />
              </dl>
            </Card>
            <Card title="Fraud cases" className="lg:col-span-2">
              {c.cases.length === 0 ? <p className="text-sm text-ink-500">No fraud cases for this customer.</p> : (
                <ul className="divide-y divide-ink-100">{c.cases.map((k) => (
                  <li key={k.id} className="flex items-center justify-between py-2"><Link className="font-medium text-brand-600 hover:underline" to={`/cases/${k.case_number}`}>{k.case_number}</Link><span className="flex items-center gap-2"><span className="text-sm tabular-nums">{k.risk_score}</span><RiskBadge level={k.risk_level} /><StatusBadge status={k.status} /></span></li>))}</ul>)}
            </Card>
          </div>
          <Card title="Accounts" className="mt-4">
            {c.accounts.length === 0 ? <p className="text-sm text-ink-500">No account on file.</p> : (
              <ul className="divide-y divide-ink-100">{c.accounts.map((a) => (
                <li key={a.id} className="flex items-center justify-between py-2 text-sm"><span className="font-mono text-xs">{a.account_number}</span><span className="flex items-center gap-3"><span className="font-semibold tabular-nums">{pkr(a.balance)}</span><StatusBadge status={a.status === "ACTIVE" ? "COMPLETED" : a.status} /></span></li>))}</ul>)}
            <p className="mt-2 text-xs text-ink-500">Copy an account number into a TRANSFER beneficiary to see a real two-sided ledger posting.</p>
          </Card>
          <Card title="Recent activity" className="mt-4" right={<span className="text-xs text-ink-500">Last {c.timeline.length} transactions</span>}><Timeline items={c.timeline} /></Card>
        </>
      )}
    </Async>
  );
}
