from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="VIEWER")  # ADMIN | FRAUD_ANALYST | AUDITOR | VIEWER
    is_active: Mapped[bool] = mapped_column(default=True)


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    home_city: Mapped[str] = mapped_column(String(64))
    # Behavioral baseline the risk engine compares each transaction against.
    avg_transaction_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    typical_locations: Mapped[list] = mapped_column(JSON, default=list)
    known_devices: Mapped[list] = mapped_column(JSON, default=list)
    known_beneficiaries: Mapped[list] = mapped_column(JSON, default=list)
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="customer")


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_ref: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="PKR")
    transaction_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="COMPLETED")  # COMPLETED | FAILED | FLAGGED (= funds on hold) | DECLINED
    merchant: Mapped[str] = mapped_column(String(255))
    merchant_category: Mapped[str] = mapped_column(String(64))
    location: Mapped[str] = mapped_column(String(64))
    device_id: Mapped[str] = mapped_column(String(64))
    beneficiary_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rule_risk_score: Mapped[int | None] = mapped_column(nullable=True)
    ml_anomaly_score: Mapped[float | None] = mapped_column(nullable=True)
    risk_score: Mapped[int | None] = mapped_column(nullable=True)  # combined rule+ML
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_indicators: Mapped[list] = mapped_column(JSON, default=list)
    # Ledger linkage. Seeded historical rows predate the ledger, so these stay NULL for them.
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer: Mapped[Customer] = relationship(back_populates="transactions")


class Account(Base):
    """A bank account. CUSTOMER accounts belong to a customer; the single SYSTEM account (CLEARING) is the counterparty
    for money entering/leaving the bank (cash, merchants, other banks), which keeps every posting double-entry balanced."""
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_number: Mapped[str] = mapped_column(String(34), unique=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    account_type: Mapped[str] = mapped_column(String(16), default="CUSTOMER")  # CUSTOMER | SYSTEM
    currency: Mapped[str] = mapped_column(String(3), default="PKR")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")  # ACTIVE | FROZEN | CLOSED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LedgerEntry(Base):
    """Append-only. One transaction = one DEBIT entry + one CREDIT entry of the same amount (double-entry)."""
    __tablename__ = "ledger_entries"
    __table_args__ = (Index("ix_ledger_account_id_id", "account_id", "id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    direction: Mapped[str] = mapped_column(String(6))  # DEBIT | CREDIT
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FraudCase(Base):
    __tablename__ = "fraud_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    risk_score: Mapped[int]
    risk_level: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="OPEN")  # OPEN|INVESTIGATING|ESCALATED|APPROVED|REJECTED
    risk_indicators: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    transaction: Mapped[Transaction] = relationship()
    customer: Mapped[Customer] = relationship()
    investigation: Mapped["Investigation | None"] = relationship(back_populates="case", uselist=False)


class Investigation(Base):
    """The AI recommendation for a case, plus the human analyst's decision on it."""
    __tablename__ = "investigations"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("fraud_cases.id"), unique=True)
    summary: Mapped[str] = mapped_column(String(2000))
    ai_recommendation: Mapped[str] = mapped_column(String(32))  # APPROVE_TRANSACTION|ESCALATE_FOR_REVIEW|BLOCK_AND_INVESTIGATE
    recommendation_reason: Mapped[str] = mapped_column(String(1000))
    confidence: Mapped[float]
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    policy_citations: Mapped[list] = mapped_column(JSON, default=list)
    decision_status: Mapped[str] = mapped_column(String(16), default="PENDING")  # PENDING|APPROVED|ESCALATED|REJECTED
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    case: Mapped[FraudCase] = relationship(back_populates="investigation")


class AgentExecution(Base):
    __tablename__ = "agent_executions"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("fraud_cases.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))  # completed | unavailable | failed
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    risk_findings: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    execution_time_ms: Mapped[int | None] = mapped_column(nullable=True)
    used_llm: Mapped[bool] = mapped_column(default=False)


class AuditLog(Base):
    """Append-only record of every analyst action and access denial."""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("fraud_cases.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    previous_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
