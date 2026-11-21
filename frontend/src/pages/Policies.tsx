import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Citations } from "../components/Citations";
import { Async, Card, ErrorState, Loading, Modal, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api, errorMessage } from "../services/api";
import type { Citation, PolicyDetail } from "../types";

export default function Policies() {
  const [sp, setSp] = useSearchParams();
  const list = useAsync(() => api.policies(), []);
  const [q, setQ] = useState(sp.get("q") ?? "");
  const [hits, setHits] = useState<{ available: boolean; items: Citation[] } | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchErr, setSearchErr] = useState<string | null>(null);
  const [open, setOpen] = useState<PolicyDetail | null>(null);
  const [opening, setOpening] = useState(false);
  const [openErr, setOpenErr] = useState<string | null>(null);

  async function search(term: string) {
    if (term.trim().length < 2) { setHits(null); return; }
    setSearching(true); setSearchErr(null);
    try { const r = await api.searchPolicies(term.trim()); setHits({ available: r.rag_available, items: r.results }); } catch (e) { setSearchErr(errorMessage(e)); } finally { setSearching(false); }
  }
  async function openPolicy(id: string) {
    setOpening(true); setOpenErr(null);
    try { setOpen(await api.policy(id)); } catch (e) { setOpenErr(errorMessage(e)); } finally { setOpening(false); }
  }
  useEffect(() => { const initial = sp.get("q"); if (initial) search(initial); const o = sp.get("open"); if (o) openPolicy(o); /* eslint-disable-next-line */ }, []);
  const submit = (e: FormEvent) => { e.preventDefault(); search(q); const n = new URLSearchParams(); if (q) n.set("q", q); setSp(n); };

  return (
    <>
      <PageHeader title="Policies & RAG" subtitle="Fictional banking policies, chunked by section and indexed in ChromaDB for retrieval with source citations" />
      <form onSubmit={submit} className="mb-4 flex gap-2" role="search">
        <input className="input" placeholder="Search fraud policies…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search fraud policies" />
        <button className="btn-primary" disabled={searching}>{searching ? "Searching…" : "Search"}</button>
      </form>
      {searchErr && <ErrorState message={searchErr} />}
      {hits && (
        <Card title={`Retrieved sources for “${q}”`} className="mb-4">
          {!hits.available ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">The policy index is unavailable (not built). Browse the documents below instead.</p> : hits.items.length === 0 ? <p className="text-sm text-ink-500">No relevant sections found.</p> : <Citations items={hits.items} />}
        </Card>
      )}
      {openErr && <ErrorState message={openErr} />}
      <Async state={list} empty={(d) => d.length === 0}>
        {(docs) => (
          <div className="grid gap-3 md:grid-cols-2">
            {docs.map((p) => (
              <button key={p.id} onClick={() => openPolicy(p.id)} className="card p-4 text-left transition hover:border-brand-300 hover:shadow-pop">
                <div className="flex items-start justify-between gap-2"><h3 className="font-semibold text-ink-900">{p.title}</h3><span className="shrink-0 rounded bg-ink-100 px-1.5 py-0.5 text-[11px] font-medium text-ink-600">{p.policy_id}</span></div>
                <p className="mt-1 text-xs text-brand-700">{p.category} · v{p.version}</p>
                <p className="mt-2 line-clamp-3 text-sm text-ink-600">{p.description}</p>
                <div className="mt-3 flex items-center justify-between text-xs text-ink-500"><span>{p.sections.length} sections</span><span className="font-medium text-ink-700">{p.relevant_cases} cited in cases</span></div>
              </button>
            ))}
          </div>
        )}
      </Async>
      <Modal open={opening || !!open} onClose={() => { setOpen(null); setOpening(false); }} title={open ? open.title : "Loading policy…"} footer={<button className="btn-secondary" onClick={() => setOpen(null)}>Close</button>}>
        {opening && !open ? <Loading /> : open && (
          <div className="max-h-[60vh] space-y-4 overflow-y-auto">
            <p className="text-xs text-ink-500">{open.policy_id} · {open.category} · version {open.version}</p>
            {open.full_sections.map((s) => (<div key={s.section}><h4 className="text-sm font-semibold text-ink-900">{s.section}</h4><p className="mt-1 text-sm text-ink-700">{s.content}</p></div>))}
          </div>
        )}
      </Modal>
    </>
  );
}
