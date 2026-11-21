import type { CaseStatus, RiskLevel } from "../types";

const hasTz = (s: string) => /[zZ]$|[+-]\d\d:\d\d$/.test(s);
const toDate = (s: string) => new Date(hasTz(s) ? s : s + "Z");
export const pkr = (n: number | null | undefined) => (n == null ? "—" : `PKR ${Math.round(n).toLocaleString("en-PK")}`);
export const dt = (s: string | null | undefined) => (s ? toDate(s).toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—");
export const clock = (s: string) => toDate(s).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
export const day = (s: string) => toDate(s).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
export const pct = (n: number) => `${Math.round(n * 100)}%`;
export const title = (s: string) => s.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

export const LEVEL_STYLE: Record<RiskLevel, string> = {
  LOW: "bg-emerald-50 text-emerald-700 ring-emerald-200", MEDIUM: "bg-amber-50 text-amber-700 ring-amber-200",
  HIGH: "bg-orange-50 text-orange-700 ring-orange-200", CRITICAL: "bg-red-50 text-red-700 ring-red-200",
};
export const LEVEL_COLOR: Record<string, string> = { LOW: "#10B981", MEDIUM: "#F59E0B", HIGH: "#F36F21", CRITICAL: "#DC2626" };
export const STATUS_STYLE: Record<CaseStatus | string, string> = {
  OPEN: "bg-blue-50 text-blue-700 ring-blue-200", INVESTIGATING: "bg-violet-50 text-violet-700 ring-violet-200", ESCALATED: "bg-orange-50 text-orange-700 ring-orange-200",
  APPROVED: "bg-emerald-50 text-emerald-700 ring-emerald-200", REJECTED: "bg-ink-100 text-ink-700 ring-ink-200", PENDING: "bg-ink-100 text-ink-700 ring-ink-200",
  COMPLETED: "bg-emerald-50 text-emerald-700 ring-emerald-200", FLAGGED: "bg-orange-50 text-orange-700 ring-orange-200 font-bold", FAILED: "bg-red-50 text-red-700 ring-red-200", DECLINED: "bg-ink-100 text-ink-700 ring-ink-200",
};
export const RECOMMENDATION_LABEL: Record<string, string> = {
  APPROVE_TRANSACTION: "Approve transaction", ESCALATE_FOR_REVIEW: "Escalate for human review", BLOCK_AND_INVESTIGATE: "Recommend block & investigate",
};
export const AGENT_LABEL: Record<string, string> = {
  fraud_detection: "Fraud Detection Agent", transaction_analysis: "Transaction Analysis Agent", customer_risk: "Customer Risk Agent",
  investigation: "Investigation Agent", rag_policy: "RAG Policy Agent", decision: "Decision Agent",
};
export const INDICATOR_LABEL: Record<string, string> = {
  NEW_DEVICE: "NEW DEVICE", NEW_LOCATION: "UNUSUAL LOCATION", UNUSUAL_AMOUNT: "HIGH AMOUNT", HIGH_VELOCITY: "HIGH VELOCITY",
  NEW_BENEFICIARY: "NEW BENEFICIARY", UNUSUAL_MERCHANT: "UNUSUAL MERCHANT", FAILED_ATTEMPTS: "FAILED ATTEMPTS",
};
export const CAN_INVESTIGATE = (role?: string) => role === "ADMIN" || role === "FRAUD_ANALYST";
export const CAN_AUDIT = (role?: string) => role === "ADMIN" || role === "AUDITOR";
