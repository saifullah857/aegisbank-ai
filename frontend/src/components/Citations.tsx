import { useState } from "react";
import { Link } from "react-router-dom";
import type { Citation } from "../types";

/** Retrieved policy sources with relevance score; the analyst can expand each to inspect the cited text. */
export function Citations({ items, unavailable }: { items: Citation[]; unavailable?: boolean }) {
  const [open, setOpen] = useState<number | null>(0);
  if (!items.length) return (
    <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{unavailable ? "Policy retrieval was unavailable for this investigation — no policies were cited. The decision rests on rule-based evidence only." : "No policy sources were retrieved."}</p>
  );
  return (
    <ul className="space-y-2">
      {items.map((c, i) => (
        <li key={i} className="rounded-lg border border-ink-100 bg-white">
          <button className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
            <span><span className="block text-sm font-medium text-ink-900">{c.document}</span><span className="block text-xs text-ink-500">{c.policy_id} · {c.section}</span></span>
            <span className="shrink-0 rounded-full bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700">{Math.round(c.score * 100)}% match</span>
          </button>
          {open === i && (
            <div className="border-t border-ink-100 px-3 py-2.5 text-sm text-ink-700">
              <p>{c.content}</p>
              <Link className="mt-2 inline-block text-xs font-medium text-brand-600 hover:underline" to={`/policies?open=${c.slug}`}>Open full policy →</Link>
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
