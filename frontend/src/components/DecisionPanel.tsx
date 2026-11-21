import { useState } from "react";
import { api, errorMessage } from "../services/api";
import type { DecisionResult, Investigation } from "../types";
import { CAN_INVESTIGATE, dt, pct, RECOMMENDATION_LABEL } from "../utils/format";
import { useAuth } from "../hooks/useAuth";
import { Modal, StatusBadge } from "./ui";

type D = "approve" | "escalate" | "reject";
const SUCCESS: Record<D, string> = {
  approve: "Recommendation approved.",
  escalate: "Case escalated for senior review.",
  reject: "Recommendation rejected and case closed.",
};
const COPY: Record<D, { title: string; body: string; btn: string; cls: string }> = {
  approve: { title: "Approve AI recommendation?", body: "You are accepting the AI recommendation. This decision is final and cannot be changed. No account is frozen and no money is moved automatically.", btn: "Approve recommendation", cls: "btn-primary" },
  escalate: { title: "Escalate this case?", body: "The case will be marked ESCALATED for senior fraud-team review. It stays open for a final decision. No account action is taken automatically.", btn: "Escalate case", cls: "btn-dark" },
  reject: { title: "Reject AI recommendation?", body: "You are overriding the AI recommendation and closing the case. This decision is final and cannot be changed.", btn: "Reject recommendation", cls: "btn !bg-red-600 text-white hover:!bg-red-700" },
};

/** Human-in-the-loop panel: recommendation + confidence + reason; every action needs explicit confirmation and is audit-logged server-side.
 *  The panel updates itself from the server's response, so the buttons give visible feedback even if the parent's refresh fails. */
export function DecisionPanel({ caseNumber, inv, onDone }: { caseNumber: string; inv: Investigation; onDone: (r?: DecisionResult) => void }) {
  const { user } = useAuth();
  const [pending, setPending] = useState<D | null>(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<{ decision: D; r: DecisionResult } | null>(null);
  // The server's answer wins over the (possibly stale) prop.
  const status = result?.r.decision_status ?? inv.decision_status;
  const decidedBy = result?.r.decided_by ?? inv.decided_by;
  const decidedAt = result?.r.decided_at ?? inv.decided_at;
  const final = status === "APPROVED" || status === "REJECTED";
  const can = CAN_INVESTIGATE(user?.role);

  async function confirm() {
    if (!pending || busy) return;
    const decision = pending;
    setBusy(true); setErr(null);
    try {
      const r = await api.decide(caseNumber, decision, notes.trim() || undefined);
      setResult({ decision, r }); setPending(null); setNotes("");
      try { onDone(r); } catch { /* parent refresh problems must never hide a recorded decision */ }
    } catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
  }

  return (
    <div className="rounded-xl border-2 border-brand-200 bg-brand-50/40 p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-700">AI recommendation — advisory only</p>
      <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-semibold uppercase text-ink-900">{RECOMMENDATION_LABEL[inv.ai_recommendation] ?? inv.ai_recommendation}</h3>
        <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-ink-800 ring-1 ring-ink-200">Confidence {pct(inv.confidence)}</span>
      </div>
      <p className="mt-2 text-sm text-ink-700"><span className="font-medium">Reason: </span>{inv.recommendation_reason}</p>
      <p className="mt-1 text-sm text-ink-600">{inv.summary}</p>
      <div className="mt-4 border-t border-brand-100 pt-3">
        {result && (
          <p className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800 ring-1 ring-emerald-200" role="status">
            ✓ {SUCCESS[result.decision]} Written to the audit log.
          </p>
        )}
        {final ? (
          <p className="text-sm text-ink-700">Decision recorded: <StatusBadge status={status} /> by <b>{decidedBy}</b> on {dt(decidedAt)}. Final — no further action is possible.</p>
        ) : !can ? (
          <p className="text-sm text-ink-500">Your role ({user?.role}) is read-only. A fraud analyst or admin must decide this case.</p>
        ) : (
          <>
            {status === "ESCALATED" && <p className="mb-2 text-sm text-orange-700">Escalated by {decidedBy}. Awaiting a final decision.</p>}
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn-primary" disabled={busy} onClick={() => { setErr(null); setPending("approve"); }}>Approve Recommendation</button>
              <button type="button" className="btn-dark" disabled={busy || status === "ESCALATED"} onClick={() => { setErr(null); setPending("escalate"); }}>Escalate</button>
              <button type="button" className="btn !bg-red-600 text-white hover:!bg-red-700" disabled={busy} onClick={() => { setErr(null); setPending("reject"); }}>Reject</button>
            </div>
            <p className="mt-2 text-xs text-ink-500">Every action requires confirmation and is written to the audit log. Accounts are never frozen automatically.</p>
          </>
        )}
      </div>
      <Modal open={!!pending} onClose={() => !busy && setPending(null)} title={pending ? COPY[pending].title : ""}
        footer={<><button type="button" className="btn-secondary" disabled={busy} onClick={() => setPending(null)}>Cancel</button><button type="button" className={pending ? COPY[pending].cls : "btn-primary"} disabled={busy} onClick={confirm}>{busy ? "Recording…" : pending ? COPY[pending].btn : ""}</button></>}>
        <p>{pending && COPY[pending].body}</p>
        <label className="label mt-3" htmlFor="notes">Analyst notes (optional)</label>
        <textarea id="notes" className="input" rows={3} maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} />
        {err && <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{err}</p>}
      </Modal>
    </div>
  );
}
