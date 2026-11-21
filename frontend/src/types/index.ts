export type Role = "ADMIN" | "FRAUD_ANALYST" | "AUDITOR" | "VIEWER";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type CaseStatus = "OPEN" | "INVESTIGATING" | "ESCALATED" | "APPROVED" | "REJECTED";

export interface Page<T> { total: number; page: number; page_size: number; items: T[] }
export interface Indicator { code: string; label: string; points: number; detail: string }

export interface CaseSummary {
  id: number; case_number: string; status: CaseStatus; risk_score: number; risk_level: RiskLevel; risk_indicators: Indicator[];
  created_at: string; has_investigation: boolean;
  customer: { id: number; code: string; name: string; home_city: string };
  transaction: { id: number; ref: string; amount: number; type: string; merchant: string; location: string; device_id: string; beneficiary_account: string | null; occurred_at: string };
}
export interface Customer { id: number; customer_code: string; full_name: string; home_city: string; avg_transaction_amount: number }
export interface TimelineTxn {
  id: number; ref: string; amount: number; type: string; merchant: string; merchant_category: string; location: string; device_id: string;
  beneficiary_account: string | null; occurred_at: string; risk_score: number | null; risk_level: RiskLevel | null; status: string;
  indicator_codes: string[]; known_device: boolean; usual_location: boolean; is_anomaly: boolean; is_focus: boolean;
}
export interface CustomerDetail extends Customer {
  typical_locations: string[]; known_devices: string[]; known_beneficiaries_count: number; total_transactions: number; flagged_transactions: number;
  cases: { id: number; case_number: string; status: CaseStatus; risk_level: RiskLevel; risk_score: number }[]; timeline: TimelineTxn[];
  accounts: { id: number; account_number: string; balance: number; currency: string; status: string }[];
}
export interface Txn {
  id: number; transaction_ref: string; customer_id: number; amount: number; currency: string; transaction_type: string; status: string; merchant: string;
  merchant_category: string; location: string; device_id: string; beneficiary_account: string | null; occurred_at: string; risk_score: number | null;
  rule_score: number | null; ml_anomaly_score: number | null; risk_level: RiskLevel | null; risk_indicators: Indicator[]; case_number?: string | null; account_id?: number | null; failure_reason?: string | null; replayed?: boolean;
}
export interface AgentResult {
  agent: string; status: "completed" | "unavailable" | "failed"; confidence: number; risk_findings: string[]; evidence: string[]; execution_time_ms: number; used_llm: boolean;
}
export interface Citation { document: string; policy_id: string; slug: string; section: string; content: string; score: number }
export interface Investigation {
  case_number: string; case_status: CaseStatus; summary: string; policy_citations: Citation[]; ai_recommendation: string; recommendation_reason: string;
  confidence: number; evidence: string[]; decision_status: "PENDING" | "APPROVED" | "ESCALATED" | "REJECTED"; decided_by: string | null; decided_at: string | null;
  agents: AgentResult[]; llm_used: boolean; fallback_notice: string | null;
}
export interface DecisionResult { case_number?: string; case_status: string; decision_status: Investigation["decision_status"]; decided_by: string; decided_at?: string | null }
export interface AnalyzeResponse {
  transaction_ref: string; risk_score: number; risk_level: RiskLevel; rule_score?: number; ml_anomaly_score?: number | null; case_number: string | null;
  investigation: Investigation | null; agents?: AgentResult[]; fallback_notice?: string | null;
}
export interface DashboardStats {
  totals: { total_transactions: number; suspicious_transactions: number; high_risk_cases: number; cases_under_investigation: number; open_cases: number; resolved_cases: number; total_cases: number };
  cases_over_time: { date: string; count: number }[]; risk_distribution: { label: string; count: number }[];
  fraud_by_transaction_type: { label: string; count: number }[]; fraud_by_location: { label: string; count: number }[];
  anomaly_trend: { date: string; transactions: number; flagged: number }[]; recent_high_risk_cases: CaseSummary[];
}
export interface Analytics {
  fraud_rate_percent: number; total_transactions: number; flagged_transactions: number; risk_score_histogram: { bucket: string; count: number }[];
  high_risk_trend: { date: string; count: number }[]; fraud_by_merchant_category: { label: string; count: number }[];
  fraud_by_device_novelty: { label: string; count: number }[]; fraud_by_hour: { hour: number; count: number }[]; case_resolution_status: { label: string; count: number }[];
}
export interface AgentInfo { name: string; display_name: string; description: string; order: number; total_runs: number; avg_confidence: number | null; avg_execution_time_ms: number | null; llm_runs: number; deterministic_runs: number }
export interface PolicySummary { id: string; title: string; policy_id: string; category: string; version: string; sections: string[]; description: string; chunk_count: number; relevant_cases: number }
export interface PolicyDetail extends PolicySummary { full_sections: { section: string; content: string }[] }
export interface AuditEntry { id: number; created_at: string; actor: string | null; case_id: number | null; action: string; previous_status: string | null; new_status: string | null; details: Record<string, unknown> }
export interface Health {
  overall_status: "ONLINE" | "DEGRADED" | "OFFLINE"; services: { name: string; status: "ONLINE" | "DEGRADED" | "OFFLINE"; detail: string }[];
  metrics: { cpu_percent: number; memory_percent: number; memory_used_mb: number; memory_total_mb: number; api_latency_ms_avg: number | null; api_latency_ms_p95: number | null; request_count: number; error_rate_percent: number; agent_avg_execution_time_ms: number | null; agent_execution_count: number; uptime_seconds: number };
}
export interface DemoTxn { transaction_id: number; transaction_ref: string; customer_id: number; customer_name: string; amount: number; location: string; risk_score: number; rule_score: number; ml_anomaly_score: number | null; risk_level: RiskLevel; risk_indicators: Indicator[]; case_number: string | null }
export interface TxnDraft { customer_id: number; amount: number; transaction_type: string; merchant: string; merchant_category: string; location: string; device_id: string; beneficiary_account: string | null; occurred_at: string }
export interface ChatTurn { role: "user" | "assistant"; content: string }
export interface ChatReply { answer: string; sources: string[]; mode: "llm" | "deterministic"; suggestions?: string[] }
export interface ReviewResult { transaction_ref: string; status: string; failure_reason: string | null }
export interface Reconciliation { balanced: boolean; total_debits: number; total_credits: number; accounts_checked: number; mismatches: { account_number: string; expected: number; actual: number }[] }
