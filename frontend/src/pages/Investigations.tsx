import { Link } from "react-router-dom";
import { Async, Card, PageHeader, RiskBadge, StatusBadge, TableWrap } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { dt, pkr } from "../utils/format";

export default function Investigations() {
  const s = useAsync(async () => {
    const r = await api.cases({ page_size: 100 });
    return { ...r, items: r.items.filter((c) => c.has_investigation) };
  }, []);
  return (
    <>
      <PageHeader title="Investigations" subtitle="Cases with an AI investigation on record (up to the 100 highest-risk cases)" />
      <Card pad={false}>
        <Async state={s} empty={(d) => d.items.length === 0}>
          {(d) => (
            <TableWrap>
              <thead><tr><th className="th">Case</th><th className="th">Customer</th><th className="th">Amount</th><th className="th">Level</th><th className="th">Status</th><th className="th">Opened</th><th className="th" /></tr></thead>
              <tbody className="divide-y divide-ink-100">{d.items.map((c) => (
                <tr key={c.id} className="hover:bg-ink-50"><td className="td font-medium">{c.case_number}</td><td className="td">{c.customer.name}</td><td className="td tabular-nums">{pkr(c.transaction.amount)}</td>
                  <td className="td"><RiskBadge level={c.risk_level} /></td><td className="td"><StatusBadge status={c.status} /></td><td className="td text-ink-500">{dt(c.created_at)}</td>
                  <td className="td text-right"><Link className="font-medium text-brand-600 hover:underline" to={`/cases/${c.case_number}`}>Open</Link></td></tr>))}</tbody>
            </TableWrap>
          )}
        </Async>
      </Card>
      <p className="mt-3 text-xs text-ink-500">No investigations yet? Open a case and click “Run AI investigation”, or use the one-click fraud demo.</p>
    </>
  );
}
