# AegisBank AI — Suspicious Activity Escalation Policy
Policy ID: SAE-2026-02
Category: Escalation
Version: 1.0

## 1. Purpose
This policy sets out when and how a suspicious transaction is escalated from the automated system to a human fraud analyst and onward to senior review.

## 2. Case Opening Criteria
A fraud case is opened automatically when the combined risk level is HIGH or CRITICAL. Cases may also be opened manually by a fraud analyst when a customer reports unauthorised activity.

## 3. Analyst Decisions
The AI recommendation is advisory only. A human analyst must approve the recommendation, escalate the case for senior review, or reject the recommendation. No account is frozen and no transaction is reversed automatically; any such action is taken by the analyst through bank procedures.

## 4. Escalation Timelines
CRITICAL cases must be reviewed within one hour. HIGH cases must be reviewed within four hours. Escalated cases must be resolved by a senior analyst within one business day.

## 5. Recommendation Outcomes
APPROVE_TRANSACTION applies when no material indicators are present. ESCALATE_FOR_REVIEW applies to MEDIUM and HIGH risk. BLOCK_AND_INVESTIGATE applies to CRITICAL risk, where multiple independent indicators such as a new device, a new location and an unusually large amount occur together.

## 6. Audit Trail
Every analyst action, including approvals, escalations, rejections and access denials, is written to the immutable audit log with the previous and new case status.
