import { FormEvent, useEffect, useRef, useState } from "react";
import { Card, PageHeader, Spinner } from "../components/ui";
import { api, errorMessage } from "../services/api";
import type { ChatTurn } from "../types";

type Msg = ChatTurn & { sources?: string[]; mode?: "llm" | "deterministic" };
const FALLBACK = ["How does a payment move through the system?", "How is the risk score calculated?", "What does a held (FLAGGED) transaction mean?", "How does the double-entry ledger work?", "What do the six AI agents do?", "What can each role do?"];

// Minimal, safe renderer: **bold** only, no HTML injection (React escapes everything else).
const Rich = ({ text }: { text: string }) => (
  <>{text.split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.startsWith("**") && p.endsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>))}</>
);

export default function Assistant() {
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "assistant", content: "Hi! I can explain how AegisBank AI works: payments and the ledger, risk scoring, the AI agents, policies, roles and deployment. English, Urdu or Roman Urdu all work when an LLM key is configured." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(FALLBACK);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { api.chatSuggestions().then((r) => setSuggestions(r.suggestions)).catch(() => undefined); }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    const history: ChatTurn[] = msgs.slice(1).map(({ role, content }) => ({ role, content })).slice(-10);
    setMsgs((m) => [...m, { role: "user", content: q }]);
    setInput(""); setBusy(true);
    try {
      const r = await api.chat(q, history);
      setMsgs((m) => [...m, { role: "assistant", content: r.answer, sources: r.sources, mode: r.mode }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "assistant", content: `Sorry — ${errorMessage(e)}` }]);
    } finally { setBusy(false); }
  };
  const onSubmit = (e: FormEvent) => { e.preventDefault(); void send(input); };

  return (
    <>
      <PageHeader title="Assistant" subtitle="Ask how the system works. Read-only: it can explain, never move money or change data." />
      <Card pad={false}>
        <div className="flex h-[60vh] flex-col">
          <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user" ? "bg-brand-500 text-white" : "bg-ink-100 text-ink-900"}`}>
                  <Rich text={m.content} />
                  {m.sources && m.sources.length > 0 && <p className="mt-2 text-[11px] text-ink-500">Sources: {m.sources.join(" · ")} · {m.mode === "llm" ? "AI-written" : "from documentation"}</p>}
                </div>
              </div>
            ))}
            {busy && <div className="flex items-center gap-2 text-sm text-ink-500"><Spinner className="h-4 w-4" /> Thinking…</div>}
            <div ref={end} />
          </div>
          <div className="flex flex-wrap gap-2 border-t border-ink-100 px-4 py-2">
            {suggestions.map((s) => <button key={s} type="button" className="rounded-full border border-ink-200 px-3 py-1 text-xs text-ink-700 hover:bg-ink-50" onClick={() => send(s)} disabled={busy}>{s}</button>)}
          </div>
          <form onSubmit={onSubmit} className="flex gap-2 border-t border-ink-100 p-3">
            <input className="input flex-1" value={input} maxLength={1000} onChange={(e) => setInput(e.target.value)} placeholder="Ask anything about the system…" aria-label="Your question" />
            <button className="btn-primary" disabled={busy || !input.trim()}>Send</button>
          </form>
        </div>
      </Card>
    </>
  );
}
