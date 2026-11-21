import { useState } from "react";
import { Async, Card, PageHeader, Pagination, StatusBadge, TableWrap } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { CAN_AUDIT, dt } from "../utils/format";

const ACTIONS = ["INVESTIGATION_RUN", "RECOMMENDATION_APPROVED", "CASE_ESCALATED", "RECOMMENDATION_REJECTED", "TRANSACTION_ANALYZED", "ACCESS_DENIED", "DEMO_TRANSACTION_CREATED"];

export default function Audit() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const s = useAsync(() => (CAN_AUDIT(user?.role) ? api.audit({ page, page_size: 20, actor: actor || undefined, action: action || undefined }) : Promise.reject(new Error("forbidden"))), [page, actor, action, user?.role]);
  if (!CAN_AUDIT(user?.role)) return (<><PageHeader title="Audit Logs" /><Card><p className="py-10 text-center text-sm text-ink-600">Audit logs are visible to Auditors and Administrators only. Your role: {user?.role}.</p></Card></>);
  return (
    <>
      <PageHeader title="Audit Logs" subtitle="Append-only record of analyst actions and access denials" />
      <Card pad={false}>
        <div className="flex flex-wrap gap-3 border-b border-ink-100 p-3">
          <input className="input !w-48" placeholder="Filter by analyst…" value={actor} onChange={(e) => { setActor(e.target.value); setPage(1); }} aria-label="Analyst filter" />
          <select className="input !w-auto" value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }} aria-label="Action filter"><option value="">All actions</option>{ACTIONS.map((a) => <option key={a}>{a}</option>)}</select>
        </div>
        <Async state={s} empty={(d) => d.items.length === 0}>
          {(d) => (<>
            <TableWrap>
              <thead><tr><th className="th">Timestamp</th><th className="th">Analyst</th><th className="th">Case</th><th className="th">Action</th><th className="th">Previous</th><th className="th">New</th><th className="th">Details</th></tr></thead>
              <tbody className="divide-y divide-ink-100">{d.items.map((r) => (
                <tr key={r.id} className="hover:bg-ink-50"><td className="td text-ink-500">{dt(r.created_at)}</td><td className="td font-medium">{r.actor ?? "—"}</td><td className="td">{r.case_id ? `#${r.case_id}` : "—"}</td><td className="td font-mono text-xs">{r.action}</td>
                  <td className="td">{r.previous_status ? <StatusBadge status={r.previous_status} /> : "—"}</td><td className="td">{r.new_status ? <StatusBadge status={r.new_status} /> : "—"}</td>
                  <td className="td max-w-xs truncate text-xs text-ink-500" title={JSON.stringify(r.details)}>{Object.keys(r.details).length ? JSON.stringify(r.details) : "—"}</td></tr>))}</tbody>
            </TableWrap>
            <Pagination page={d.page} pageSize={d.page_size} total={d.total} onChange={setPage} />
          </>)}
        </Async>
      </Card>
    </>
  );
}
