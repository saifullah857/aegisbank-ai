import { FormEvent, useState } from "react";
import { LogoMark } from "../components/Logo";
import { Spinner } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { errorMessage } from "../services/api";

const DEMO = [["analyst01", "Fraud Analyst"], ["auditor01", "Auditor"], ["viewer01", "Viewer"], ["admin", "Admin"]];

export default function Login() {
  const { login } = useAuth();
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError(null);
    try { await login(username.trim(), password); } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }
  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between bg-ink-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-3"><LogoMark size={40} /><span className="text-xl font-bold">Aegis<span className="text-brand-500">Bank</span> AI</span></div>
        <div>
          <h1 className="text-3xl font-semibold leading-tight">Intelligent Fraud Investigation<br />for Modern Banking</h1>
          <p className="mt-4 max-w-md text-ink-300">Rules, machine-learning anomaly detection, a six-agent investigation pipeline and cited banking policy — with a human analyst always making the final call.</p>
          <div className="mt-8 flex gap-6 text-sm text-ink-300"><span>● Explainable risk</span><span>● Human-in-the-loop</span><span>● Full audit trail</span></div>
        </div>
        <p className="text-xs text-ink-500">Hackathon demo · all data is synthetic · not affiliated with any real bank</p>
      </div>
      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm" aria-label="Sign in">
          <div className="mb-6 lg:hidden"><div className="flex items-center gap-2"><LogoMark /><span className="text-lg font-bold">Aegis<span className="text-brand-500">Bank</span> AI</span></div></div>
          <h2 className="text-2xl font-semibold">Sign in</h2>
          <p className="mb-6 mt-1 text-sm text-ink-500">Use your analyst credentials to continue.</p>
          <div className="space-y-4">
            <div><label className="label" htmlFor="u">Username</label><input id="u" className="input" autoComplete="username" value={username} onChange={(e) => setU(e.target.value)} required autoFocus /></div>
            <div><label className="label" htmlFor="p">Password</label><input id="p" type="password" className="input" autoComplete="current-password" value={password} onChange={(e) => setP(e.target.value)} required /></div>
            {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</p>}
            <button className="btn-primary w-full" disabled={busy}>{busy ? <><Spinner className="h-4 w-4" /> Signing in…</> : "Sign in"}</button>
          </div>
          <div className="mt-6 rounded-lg border border-ink-100 bg-ink-50 p-3 text-xs text-ink-600">
            <p className="mb-1.5 font-medium text-ink-800">Synthetic demo accounts <span className="font-normal text-ink-500">(password: AegisDemo123!)</span></p>
            <div className="flex flex-wrap gap-1.5">{DEMO.map(([u, r]) => (<button type="button" key={u} className="rounded-md bg-white px-2 py-1 ring-1 ring-ink-200 hover:ring-brand-500" onClick={() => { setU(u); setP("AegisDemo123!"); }}>{u} <span className="text-ink-400">· {r}</span></button>))}</div>
          </div>
        </form>
      </div>
    </div>
  );
}
