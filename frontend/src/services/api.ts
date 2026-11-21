import axios, { AxiosError } from "axios";
import type {
  AgentInfo, AnalyzeResponse, Analytics, AuditEntry, CaseSummary, Customer, CustomerDetail, DashboardStats, DemoTxn, Health, Investigation, Page,
  Citation, ChatReply, ChatTurn, DecisionResult, ReviewResult, PolicyDetail, PolicySummary, TimelineTxn, Txn, TxnDraft,
} from "../types";

const TOKEN_KEY = "aegis.token";
export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (t: string) => sessionStorage.setItem(TOKEN_KEY, t),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

export const http = axios.create({ baseURL: import.meta.env.VITE_API_URL || "/api/v1", timeout: 60000 });
http.interceptors.request.use((cfg) => {
  const t = tokenStore.get();
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});
http.interceptors.response.use((r) => r, (err: AxiosError) => {
  if (err.response?.status === 401 && !err.config?.url?.includes("/auth/login")) {
    tokenStore.clear();
    window.dispatchEvent(new Event("aegis:unauthorized"));
  }
  return Promise.reject(err);
});

export function errorMessage(e: unknown): string {
  const err = e as AxiosError<{ detail?: unknown }>;
  if (err?.response) {
    const d = err.response.data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x: { msg?: string }) => x.msg).filter(Boolean).join("; ") || "Invalid request";
    return `Request failed (${err.response.status})`;
  }
  if (err?.code === "ECONNABORTED") return "The request timed out.";
  if (err?.request) return "Cannot reach the AegisBank API. Check that the backend is running.";
  return (e as Error)?.message || "Unexpected error";
}
export const statusOf = (e: unknown) => (e as AxiosError)?.response?.status;

const get = <T,>(url: string, params?: object) => http.get<T>(url, { params }).then((r) => r.data);
const post = <T,>(url: string, body?: object) => http.post<T>(url, body).then((r) => r.data);

export const api = {
  login: (username: string, password: string) => post<{ access_token: string; role: string }>("/auth/login", { username, password }),
  dashboard: (days = 30) => get<DashboardStats>("/dashboard/stats", { days }),
  analytics: () => get<Analytics>("/dashboard/analytics"),
  customers: (page = 1, page_size = 20) => get<Page<Customer>>("/customers", { page, page_size }),
  customer: (id: number | string) => get<CustomerDetail>(`/customers/${id}`),
  transactions: (p: { page?: number; page_size?: number; risk_level?: string; customer_id?: number }) => get<Page<Txn>>("/transactions", p),
  // A fresh Idempotency-Key per submit: if the network retries the request the server returns the first result instead of paying twice.
  createTransaction: (d: TxnDraft) => http.post<Txn>("/transactions", d, { headers: { "Idempotency-Key": crypto.randomUUID() } }).then((r) => r.data),
  releaseTransaction: (id: number, notes?: string) => post<ReviewResult>(`/transactions/${id}/release`, { notes }),
  declineTransaction: (id: number, notes?: string) => post<ReviewResult>(`/transactions/${id}/decline`, { notes }),
  chat: (message: string, history: ChatTurn[]) => post<ChatReply>("/assistant/chat", { message, history }),
  chatSuggestions: () => get<{ suggestions: string[] }>("/assistant/suggestions"),
  cases: (p: { page?: number; page_size?: number; status?: string; risk_level?: string }) => get<Page<CaseSummary>>("/fraud/cases", p),
  case: (ref: string) => get<CaseSummary>(`/fraud/cases/${ref}`),
  caseTimeline: (ref: string) => get<{ timeline: TimelineTxn[] }>(`/fraud/cases/${ref}/timeline`),
  investigation: (ref: string) => get<Investigation>(`/investigations/${ref}`),
  analyze: (transaction_id: number) => post<AnalyzeResponse>("/fraud/analyze", { transaction_id }),
  decide: (ref: string, decision: "approve" | "escalate" | "reject", notes?: string) =>
    post<DecisionResult>(`/investigations/${ref}/${decision}`, { notes }),
  agents: () => get<{ mode: string; llm_configured: boolean; llm_provider: string; agents: AgentInfo[] }>("/agents"),
  policies: () => get<PolicySummary[]>("/policies"),
  policy: (id: string) => get<PolicyDetail>(`/policies/${id}`),
  searchPolicies: (q: string) => get<{ rag_available: boolean; results: Citation[] }>("/policies/search", { q }),
  audit: (p: { page?: number; page_size?: number; actor?: string; action?: string }) => get<Page<AuditEntry>>("/audit", p),
  health: () => get<Health>("/system/health"),
  appHealth: () => get<{ status: string; llm_provider: string; llm_configured: boolean }>("/health"),
  simulate: (customer_id: number, kind: "normal" | "suspicious" | "anomalous") => post<TxnDraft>("/simulator/generate", { customer_id, kind }),
  demoTransaction: () => post<DemoTxn>("/demo/transaction"),
};
