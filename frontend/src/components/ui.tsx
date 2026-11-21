import { ReactNode, useEffect } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import type { CaseStatus, RiskLevel } from "../types";
import { INDICATOR_LABEL, LEVEL_STYLE, STATUS_STYLE } from "../utils/format";

export const Spinner = ({ className = "h-5 w-5" }: { className?: string }) => (
  <svg className={`animate-spin text-brand-500 ${className}`} viewBox="0 0 24 24" fill="none" aria-label="Loading">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity=".2" /><path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
  </svg>
);
export const Loading = ({ label = "Loading…" }: { label?: string }) => (
  <div className="flex items-center justify-center gap-3 py-16 text-sm text-ink-500" role="status"><Spinner />{label}</div>
);
export const ErrorState = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <div className="card border-red-200 bg-red-50/50 p-6 text-center" role="alert">
    <div className="mx-auto mb-2 flex h-9 w-9 items-center justify-center rounded-full bg-red-100 text-red-600 font-bold">!</div>
    <p className="text-sm font-medium text-red-800">Something went wrong</p>
    <p className="mt-1 text-sm text-red-700">{message}</p>
    {onRetry && <button className="btn-secondary mt-4" onClick={onRetry}>Try again</button>}
  </div>
);
export const EmptyState = ({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) => (
  <div className="py-14 text-center">
    <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-ink-100 text-ink-400">∅</div>
    <p className="text-sm font-medium text-ink-800">{title}</p>
    {hint && <p className="mt-1 text-sm text-ink-500">{hint}</p>}
    {action && <div className="mt-4">{action}</div>}
  </div>
);

export function Async<T>({ state, children, empty }: { state: { data: T | null; loading: boolean; error: string | null; reload: () => void }; children: (d: T) => ReactNode; empty?: (d: T) => boolean }) {
  if (state.loading && !state.data) return <Loading />;
  if (state.error) return <ErrorState message={state.error} onRetry={state.reload} />;
  if (!state.data) return null;
  if (empty?.(state.data)) return <EmptyState title="Nothing to show yet" />;
  return <>{children(state.data)}</>;
}

export const RiskBadge = ({ level }: { level: RiskLevel | null | undefined }) =>
  level ? <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${LEVEL_STYLE[level]}`}>{level}</span> : <span className="text-ink-400">—</span>;
export const StatusBadge = ({ status }: { status: CaseStatus | string }) => (
  <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${STATUS_STYLE[status] ?? STATUS_STYLE.PENDING}`}>{status}</span>
);
export const IndicatorChip = ({ code }: { code: string }) => (
  <span className="inline-flex items-center rounded-md bg-red-50 px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-red-700 ring-1 ring-inset ring-red-200">{INDICATOR_LABEL[code] ?? code}</span>
);

export function ScoreBar({ score, level }: { score: number; level: RiskLevel }) {
  const color = { LOW: "bg-emerald-500", MEDIUM: "bg-amber-500", HIGH: "bg-brand-500", CRITICAL: "bg-red-600" }[level];
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-ink-100"><div className={`h-full ${color}`} style={{ width: `${score}%` }} /></div>
      <span className="text-sm font-semibold tabular-nums">{score}</span>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions, crumbs }: { title: string; subtitle?: string; actions?: ReactNode; crumbs?: { label: string; to?: string }[] }) {
  return (
    <div className="mb-5">
      {crumbs && (
        <nav aria-label="Breadcrumb" className="mb-1 flex items-center gap-1.5 text-xs text-ink-500">
          {crumbs.map((c, i) => (<span key={i} className="flex items-center gap-1.5">{i > 0 && <span>/</span>}{c.to ? <Link className="hover:text-brand-600" to={c.to}>{c.label}</Link> : <span className="text-ink-800">{c.label}</span>}</span>))}
        </nav>
      )}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-xl font-semibold text-ink-900">{title}</h1>{subtitle && <p className="mt-0.5 text-sm text-ink-500">{subtitle}</p>}</div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}

export const Card = ({ title, right, children, className = "", pad = true }: { title?: string; right?: ReactNode; children: ReactNode; className?: string; pad?: boolean }) => (
  <section className={`card ${className}`}>
    {title && <header className="flex items-center justify-between border-b border-ink-100 px-4 py-3"><h2 className="text-sm font-semibold text-ink-900">{title}</h2>{right}</header>}
    <div className={pad ? "p-4" : ""}>{children}</div>
  </section>
);

export const StatCard = ({ label, value, hint, tone = "ink" }: { label: string; value: string | number; hint?: string; tone?: "ink" | "orange" | "red" | "violet" }) => {
  const bar = { ink: "bg-ink-800", orange: "bg-brand-500", red: "bg-red-600", violet: "bg-violet-500" }[tone];
  return (
    <div className="card relative overflow-hidden p-4">
      <div className={`absolute inset-y-0 left-0 w-1 ${bar}`} />
      <p className="text-xs font-medium text-ink-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-ink-900">{typeof value === "number" ? value.toLocaleString() : value}</p>
      {hint && <p className="mt-0.5 text-xs text-ink-400">{hint}</p>}
    </div>
  );
};

export const TableWrap = ({ children }: { children: ReactNode }) => <div className="overflow-x-auto"><table className="min-w-full divide-y divide-ink-100">{children}</table></div>;

export function Pagination({ page, pageSize, total, onChange }: { page: number; pageSize: number; total: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between border-t border-ink-100 px-4 py-2.5 text-sm text-ink-500">
      <span>{total === 0 ? "0 results" : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total.toLocaleString()}`}</span>
      <div className="flex items-center gap-2">
        <button className="btn-secondary !py-1" disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
        <span className="tabular-nums">Page {page} / {pages}</span>
        <button className="btn-secondary !py-1" disabled={page >= pages} onClick={() => onChange(page + 1)}>Next</button>
      </div>
    </div>
  );
}

export function Modal({ open, onClose, title, children, footer }: { open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);
  if (!open) return null;
  // Rendered into <body> via a portal so no parent (overflow, transform, animation, stacking context) can hide or block the dialog.
  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-ink-900/40" onClick={onClose} />
      <div className="relative w-full max-w-md animate-fadeUp rounded-xl bg-white shadow-pop">
        <div className="border-b border-ink-100 px-5 py-3.5 text-base font-semibold">{title}</div>
        <div className="px-5 py-4 text-sm text-ink-700">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-ink-100 px-5 py-3">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}

export const Tabs = <T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string }[]; value: T; onChange: (v: T) => void }) => (
  <div className="flex gap-1 rounded-lg bg-ink-100 p-1">
    {tabs.map((t) => (<button key={t.id} onClick={() => onChange(t.id)} className={`rounded-md px-3 py-1 text-sm font-medium transition ${value === t.id ? "bg-white text-ink-900 shadow-card" : "text-ink-500 hover:text-ink-800"}`}>{t.label}</button>))}
  </div>
);

export const Field = ({ label, children }: { label: string; children: ReactNode }) => (<div><label className="label">{label}</label>{children}</div>);
export const KV = ({ k, v }: { k: string; v: ReactNode }) => (<div className="flex items-start justify-between gap-4 py-1.5 text-sm"><dt className="text-ink-500">{k}</dt><dd className="text-right font-medium text-ink-900">{v}</dd></div>);
