import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Logo } from "../components/Logo";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";
import type { CaseSummary } from "../types";
import { CAN_AUDIT, CAN_INVESTIGATE } from "../utils/format";
import { RiskBadge } from "../components/ui";

const I = ({ d }: { d: string }) => (<svg className="h-[18px] w-[18px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>);
const NAV: { to: string; label: string; icon: string; group: string; show?: (r?: string) => boolean }[] = [
  { to: "/", label: "Dashboard", icon: "M3 12 12 3l9 9M5 10v10h5v-6h4v6h5V10", group: "Overview" },
  { to: "/cases", label: "Fraud Cases", icon: "M12 3 4 6v6c0 5 3.400 8 8 9 4.600-1 8-4 8-9V6z", group: "Overview" },
  { to: "/investigations", label: "Investigations", icon: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm9 16-4-4", group: "Overview" },
  { to: "/customers", label: "Customers", icon: "M16 11a4 4 0 1 0-8 0 4 4 0 0 0 8 0zM4 21a8 8 0 0 1 16 0", group: "Data" },
  { to: "/transactions", label: "Transactions", icon: "M7 8h13M7 8l3-3M7 8l3 3M17 16H4m13 0-3-3m3 3-3 3", group: "Data" },
  { to: "/analytics", label: "Fraud Analytics", icon: "M4 20V10m6 10V4m6 16v-7m4 7H2", group: "Intelligence" },
  { to: "/agents", label: "AI Agents", icon: "M12 8V4m-6 8a6 6 0 0 1 12 0v6H6zM9 13h.01M15 13h.01", group: "Intelligence" },
  { to: "/policies", label: "Policies & RAG", icon: "M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h7", group: "Intelligence" },
  { to: "/simulator", label: "Transaction Simulator", icon: "M5 3l14 9-14 9z", group: "Tools", show: CAN_INVESTIGATE },
  { to: "/assistant", label: "Assistant", icon: "M21 12a8 8 0 0 1-11.600 7.100L4 20l1-4.600A8 8 0 1 1 21 12zM8.500 11h.01M12 11h.01M15.500 11h.01", group: "Tools" },
  { to: "/audit", label: "Audit Logs", icon: "M9 5h10M9 12h10M9 19h10M4 5h.01M4 12h.01M4 19h.01", group: "Governance", show: CAN_AUDIT },
  { to: "/health", label: "System Health", icon: "M3 12h4l3-8 4 16 3-8h4", group: "Governance" },
  { to: "/settings", label: "Settings", icon: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm7.400-3a7.400 7.400 0 0 0-.1-1.200l2-1.600-2-3.400-2.400 1a7.600 7.600 0 0 0-2-1.200L14.500 3h-4l-.4 2.600a7.600 7.600 0 0 0-2 1.200l-2.400-1-2 3.400 2 1.600a7.400 7.400 0 0 0 0 2.400l-2 1.600 2 3.400 2.400-1a7.600 7.600 0 0 0 2 1.200l.4 2.600h4l.4-2.600a7.600 7.600 0 0 0 2-1.200l2.400 1 2-3.400-2-1.600c.1-.4.100-.8.100-1.200z", group: "Governance" },
];

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  const items = NAV.filter((n) => !n.show || n.show(user?.role));
  const groups = [...new Set(items.map((n) => n.group))];
  return (
    <div className="flex h-full flex-col bg-ink-900 text-ink-300">
      <div className="px-5 py-5"><Logo light /></div>
      {CAN_INVESTIGATE(user?.role) && (
        <div className="px-3 pb-3">
          <Link to="/demo" onClick={onNavigate} className="btn-primary w-full !py-2.5 text-[13px] font-semibold tracking-wide">▶ RUN FRAUD DEMO</Link>
        </div>
      )}
      <nav className="flex-1 space-y-4 overflow-y-auto px-3 pb-4" aria-label="Main">
        {groups.map((g) => (
          <div key={g}>
            <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-ink-500">{g}</p>
            {items.filter((n) => n.group === g).map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === "/"} onClick={onNavigate}
                className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${isActive ? "bg-brand-500/15 text-white" : "hover:bg-white/5 hover:text-white"}`}>
                {({ isActive }) => (<><span className={isActive ? "text-brand-400" : ""}><I d={n.icon} /></span>{n.label}</>)}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <p className="border-t border-white/10 px-5 py-3 text-[10px] leading-snug text-ink-500">Synthetic data only. AI output is advisory — a human analyst decides.</p>
    </div>
  );
}

function useOutside(onOutside: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && onOutside();
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [onOutside]);
  return ref;
}

function Notifications() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<CaseSummary[]>([]);
  const [total, setTotal] = useState(0);
  const ref = useOutside(() => setOpen(false));
  useEffect(() => {
    const load = () => api.cases({ status: "OPEN", page_size: 5 }).then((r) => { setItems(r.items); setTotal(r.total); }).catch(() => undefined);
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="relative" ref={ref}>
      <button className="relative rounded-lg p-2 text-ink-500 hover:bg-ink-100" onClick={() => setOpen(!open)} aria-label={`Notifications, ${total} open cases`}>
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8zM13.700 21a2 2 0 0 1-3.400 0" strokeLinecap="round" /></svg>
        {total > 0 && <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-500 px-1 text-[10px] font-bold text-white">{total > 99 ? "99+" : total}</span>}
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 animate-fadeUp rounded-xl border border-ink-100 bg-white shadow-pop">
          <p className="border-b border-ink-100 px-4 py-2.5 text-sm font-semibold">Open cases awaiting review ({total})</p>
          {items.length === 0 ? <p className="px-4 py-6 text-center text-sm text-ink-500">No open cases.</p> : items.map((c) => (
            <Link key={c.id} to={`/cases/${c.case_number}`} onClick={() => setOpen(false)} className="flex items-center justify-between gap-2 border-b border-ink-50 px-4 py-2.5 text-sm last:border-0 hover:bg-ink-50">
              <span><span className="block font-medium">{c.case_number}</span><span className="text-xs text-ink-500">{c.customer.name} · {c.transaction.location}</span></span><RiskBadge level={c.risk_level} />
            </Link>
          ))}
          <Link to="/cases?status=OPEN" onClick={() => setOpen(false)} className="block px-4 py-2.5 text-center text-sm font-medium text-brand-600 hover:bg-ink-50">View all open cases</Link>
        </div>
      )}
    </div>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useOutside(() => setOpen(false));
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-ink-100" aria-label="User menu">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink-900 text-xs font-bold uppercase text-white">{user?.username.slice(0, 2)}</span>
        <span className="hidden text-left leading-tight sm:block"><span className="block text-sm font-medium">{user?.username}</span><span className="block text-[10px] text-ink-500">{user?.role}</span></span>
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-48 animate-fadeUp rounded-xl border border-ink-100 bg-white py-1 shadow-pop">
          <Link to="/settings" onClick={() => setOpen(false)} className="block px-4 py-2 text-sm hover:bg-ink-50">Profile & settings</Link>
          <button onClick={logout} className="block w-full px-4 py-2 text-left text-sm text-red-700 hover:bg-red-50">Sign out</button>
        </div>
      )}
    </div>
  );
}

function Search() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  function submit(e: FormEvent) {
    e.preventDefault();
    const v = q.trim();
    if (!v) return;
    nav(/^frd-/i.test(v) ? `/cases/${v.toUpperCase()}` : `/policies?q=${encodeURIComponent(v)}`);
    setQ("");
  }
  return (
    <form onSubmit={submit} className="hidden w-full max-w-sm md:block" role="search">
      <input className="input !bg-ink-50" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Open case (FRD-2026-00012) or search policies…" aria-label="Search" />
    </form>
  );
}

export default function AppLayout(): ReactNode {
  const [drawer, setDrawer] = useState(false);
  const loc = useLocation();
  useEffect(() => { setDrawer(false); window.scrollTo(0, 0); }, [loc.pathname]);
  return (
    <div className="flex h-full">
      <aside className="hidden w-64 shrink-0 lg:block"><Sidebar /></aside>
      {drawer && (<div className="fixed inset-0 z-50 lg:hidden"><div className="absolute inset-0 bg-ink-900/50" onClick={() => setDrawer(false)} /><div className="relative h-full w-72 animate-fadeUp"><Sidebar onNavigate={() => setDrawer(false)} /></div></div>)}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-ink-100 bg-white px-4">
          <button className="rounded-lg p-2 text-ink-600 hover:bg-ink-100 lg:hidden" onClick={() => setDrawer(true)} aria-label="Open menu">
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" /></svg>
          </button>
          <Search />
          <div className="ml-auto flex items-center gap-1"><Notifications /><UserMenu /></div>
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-5 md:px-6" id="main">
          <div className="mx-auto max-w-7xl animate-fadeUp" key={loc.pathname}><Outlet /></div>
        </main>
      </div>
    </div>
  );
}
