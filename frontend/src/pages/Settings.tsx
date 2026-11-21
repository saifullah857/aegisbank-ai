import { Card, KV, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";
import { Async } from "../components/ui";

const PERMS: Record<string, string[]> = {
  ADMIN: ["Full access", "Run investigations", "Record decisions", "View audit logs"],
  FRAUD_ANALYST: ["Investigate cases", "Record decisions (approve / escalate / reject)", "Use the simulator and demo", "No audit-log access"],
  AUDITOR: ["Read cases and investigations", "View audit logs", "Cannot record decisions"],
  VIEWER: ["Read-only access", "Cannot run investigations or record decisions"],
};

export default function Settings() {
  const { user } = useAuth();
  const h = useAsync(() => api.appHealth(), []);
  return (
    <>
      <PageHeader title="Settings" subtitle="Your profile, permissions and platform configuration" />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Profile"><dl className="divide-y divide-ink-50"><KV k="Username" v={user?.username} /><KV k="Role" v={user?.role} /></dl></Card>
        <Card title="Your permissions"><ul className="list-disc space-y-1 pl-5 text-sm text-ink-700">{(PERMS[user?.role ?? ""] ?? []).map((p) => <li key={p}>{p}</li>)}</ul></Card>
        <Card title="AI provider">
          <Async state={h}>{(d) => (<dl className="divide-y divide-ink-50"><KV k="Provider" v={d.llm_provider} /><KV k="API key configured" v={d.llm_configured ? "Yes" : "No"} /><KV k="Mode" v={d.llm_configured ? "LLM-assisted" : "Deterministic fallback"} /></dl>)}</Async>
          <p className="mt-3 text-xs text-ink-500">The provider key is a server-side environment variable and is never sent to the browser.</p>
        </Card>
      </div>
    </>
  );
}
