import { useState } from "react";
import { Link } from "react-router-dom";
import { Async, Card, IndicatorChip, PageHeader, Pagination, RiskBadge, ScoreBar, StatusBadge, TableWrap } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { useAsync } from "../hooks/useAsync";
import { api, errorMessage } from "../services/api";
import { CAN_INVESTIGATE, dt, pkr } from "../utils/format";

export default function Transactions() {
  const [page, setPage] = useState(1);
  const [level, setLevel] = useState("");
  const s = useAsync(() => api.transactions({ page, page_size: 20, risk_level: level || undefined }), [page, level]);
  const { user } = useAuth();
  const [msg, setMsg] = useState<string | null>(null);
  const review = async (id: number, action: "release" | "decline") => {
    const notes = window.prompt(`Optional note for the audit log (${action}):`) ?? undefined;
    if (notes === undefined && !window.confirm(`${action === "release" ? "Release" : "Decline"} this held transaction?`)) return;
    try { const r = await (action === "release" ? api.releaseTransaction(id, notes) : api.declineTransaction(id, notes)); setMsg(`${r.transaction_ref}: ${r.status}`); s.reload(); }
    catch (e) { setMsg(errorMessage(e)); }
  };
  return (
    <>
      <PageHeader title="Transactions" subtitle="Scored by rules + ML. HIGH/CRITICAL payments are held (funds do not move) until an analyst releases or declines them" />
      {msg && <div className="mb-3 rounded-lg bg-ink-100 px-3 py-2 text-sm text-ink-800" role="status">{msg}</div>}
      <Card pad={false}>
        <div className="border-b border-ink-100 p-3"><select className="input !w-auto" value={level} onChange={(e) => { setLevel(e.target.value); setPage(1); }} aria-label="Risk filter"><option value="">All risk levels</option>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((l) => <option key={l}>{l}</option>)}</select></div>
        <Async state={s} empty={(d) => d.items.length === 0}>
          {(d) => (<>
            <TableWrap>
              <thead><tr><th className="th">Reference</th><th className="th">Customer</th><th className="th">Amount</th><th className="th">Type</th><th className="th">Merchant</th><th className="th">Location</th><th className="th">Rule</th><th className="th">ML</th><th className="th">Combined</th><th className="th">Status</th><th className="th">Level</th><th className="th">Indicators</th><th className="th">Time</th><th className="th">Review</th></tr></thead>
              <tbody className="divide-y divide-ink-100">{d.items.map((t) => (
                <tr key={t.id} className="hover:bg-ink-50">
                  <td className="td font-mono text-xs">{t.transaction_ref}</td><td className="td"><Link className="text-brand-600 hover:underline" to={`/customers/${t.customer_id}`}>#{t.customer_id}</Link></td>
                  <td className="td tabular-nums">{pkr(t.amount)}</td><td className="td">{t.transaction_type}</td><td className="td">{t.merchant}</td><td className="td">{t.location}</td>
                  <td className="td tabular-nums">{t.rule_score ?? "—"}</td><td className="td tabular-nums">{t.ml_anomaly_score != null ? t.ml_anomaly_score.toFixed(2) : "—"}</td>
                  <td className="td">{t.risk_score != null && t.risk_level ? <ScoreBar score={t.risk_score} level={t.risk_level} /> : "—"}</td><td className="td"><span title={t.failure_reason ?? undefined}><StatusBadge status={t.status} /></span></td><td className="td"><RiskBadge level={t.risk_level} /></td>
                  <td className="td"><div className="flex max-w-[220px] flex-wrap gap-1">{t.risk_indicators.slice(0, 2).map((i) => <IndicatorChip key={i.code} code={i.code} />)}</div></td><td className="td text-ink-500">{dt(t.occurred_at)}</td>
                  <td className="td whitespace-nowrap">{t.status === "FLAGGED" && t.account_id && CAN_INVESTIGATE(user?.role) ? (<><button className="btn-secondary !px-2 !py-1 text-xs" onClick={() => review(t.id, "release")}>Release</button> <button className="btn-danger !px-2 !py-1 text-xs" onClick={() => review(t.id, "decline")}>Decline</button></>) : "—"}</td>
                </tr>))}</tbody>
            </TableWrap>
            <Pagination page={d.page} pageSize={d.page_size} total={d.total} onChange={setPage} />
          </>)}
        </Async>
      </Card>
    </>
  );
}
