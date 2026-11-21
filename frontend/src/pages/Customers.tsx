import { useState } from "react";
import { Link } from "react-router-dom";
import { Async, Card, PageHeader, Pagination, TableWrap } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { pkr } from "../utils/format";

export default function Customers() {
  const [page, setPage] = useState(1);
  const s = useAsync(() => api.customers(page, 20), [page]);
  return (
    <>
      <PageHeader title="Customers" subtitle="Synthetic customers and their behavioural baselines" />
      <Card pad={false}>
        <Async state={s} empty={(d) => d.items.length === 0}>
          {(d) => (<>
            <TableWrap>
              <thead><tr><th className="th">Customer ID</th><th className="th">Name</th><th className="th">Home city</th><th className="th">Avg. transaction</th><th className="th" /></tr></thead>
              <tbody className="divide-y divide-ink-100">{d.items.map((c) => (
                <tr key={c.id} className="hover:bg-ink-50"><td className="td font-mono text-xs">{c.customer_code}</td><td className="td font-medium">{c.full_name}</td><td className="td">{c.home_city}</td><td className="td tabular-nums">{pkr(c.avg_transaction_amount)}</td>
                  <td className="td text-right"><Link className="font-medium text-brand-600 hover:underline" to={`/customers/${c.id}`}>View</Link></td></tr>))}</tbody>
            </TableWrap>
            <Pagination page={d.page} pageSize={d.page_size} total={d.total} onChange={setPage} />
          </>)}
        </Async>
      </Card>
    </>
  );
}
