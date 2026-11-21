import { Link, useSearchParams } from "react-router-dom";
import { Async, Card, IndicatorChip, PageHeader, Pagination, RiskBadge, ScoreBar, StatusBadge, TableWrap } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { dt, pkr } from "../utils/format";

const STATUSES = ["OPEN", "INVESTIGATING", "ESCALATED", "APPROVED", "REJECTED"];
export default function Cases() {
  const [sp, setSp] = useSearchParams();
  const page = Number(sp.get("page") || 1), status = sp.get("status") || "", level = sp.get("risk_level") || "";
  const set = (k: string, v: string) => { const n = new URLSearchParams(sp); v ? n.set(k, v) : n.delete(k); if (k !== "page") n.delete("page"); setSp(n); };
  const s = useAsync(() => api.cases({ page, page_size: 15, status: status || undefined, risk_level: level || undefined }), [page, status, level]);
  return (
    <>
      <PageHeader title="Fraud Cases" subtitle="HIGH and CRITICAL transactions open a case automatically. Highest risk first." />
      <Card pad={false}>
        <div className="flex flex-wrap gap-3 border-b border-ink-100 p-3">
          <select className="input !w-auto" value={status} onChange={(e) => set("status", e.target.value)} aria-label="Status filter"><option value="">All statuses</option>{STATUSES.map((x) => <option key={x}>{x}</option>)}</select>
          <select className="input !w-auto" value={level} onChange={(e) => set("risk_level", e.target.value)} aria-label="Risk filter"><option value="">All risk levels</option><option>HIGH</option><option>CRITICAL</option></select>
        </div>
        <Async state={s} empty={(d) => d.items.length === 0}>
          {(d) => (<>
            <TableWrap>
              <thead><tr><th className="th">Case</th><th className="th">Customer</th><th className="th">Amount</th><th className="th">Location</th><th className="th">Indicators</th><th className="th">Risk</th><th className="th">Level</th><th className="th">Status</th><th className="th">When</th></tr></thead>
              <tbody className="divide-y divide-ink-100">{d.items.map((c) => (
                <tr key={c.id} className="hover:bg-ink-50">
                  <td className="td"><Link className="font-medium text-brand-600 hover:underline" to={`/cases/${c.case_number}`}>{c.case_number}</Link></td>
                  <td className="td">{c.customer.name}</td><td className="td tabular-nums">{pkr(c.transaction.amount)}</td><td className="td">{c.transaction.location}</td>
                  <td className="td"><div className="flex max-w-xs flex-wrap gap-1">{c.risk_indicators.slice(0, 3).map((i) => <IndicatorChip key={i.code} code={i.code} />)}{c.risk_indicators.length > 3 && <span className="text-xs text-ink-400">+{c.risk_indicators.length - 3}</span>}</div></td>
                  <td className="td"><ScoreBar score={c.risk_score} level={c.risk_level} /></td><td className="td"><RiskBadge level={c.risk_level} /></td><td className="td"><StatusBadge status={c.status} /></td><td className="td text-ink-500">{dt(c.transaction.occurred_at)}</td>
                </tr>))}</tbody>
            </TableWrap>
            <Pagination page={d.page} pageSize={d.page_size} total={d.total} onChange={(p) => set("page", String(p))} />
          </>)}
        </Async>
      </Card>
    </>
  );
}
