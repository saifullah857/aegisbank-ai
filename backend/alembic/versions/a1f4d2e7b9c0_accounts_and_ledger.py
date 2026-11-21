"""accounts, double-entry ledger, and transaction ledger links

Revision ID: a1f4d2e7b9c0
Revises: c8b36ab539db
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1f4d2e7b9c0"
down_revision: Union[str, Sequence[str], None] = "c8b36ab539db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_number", sa.String(length=34), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("account_type", sa.String(length=16), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("opening_balance", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("balance", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounts_account_number"), "accounts", ["account_number"], unique=True)
    op.create_index(op.f("ix_accounts_customer_id"), "accounts", ["customer_id"], unique=False)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(length=6), nullable=False),
        sa.Column("amount", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_entries_transaction_id"), "ledger_entries", ["transaction_id"], unique=False)
    op.create_index("ix_ledger_account_id_id", "ledger_entries", ["account_id", "id"], unique=False)

    with op.batch_alter_table("transactions") as batch:  # batch mode so SQLite can add the FK too
        batch.add_column(sa.Column("account_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("idempotency_key", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("failure_reason", sa.String(length=255), nullable=True))
        batch.create_foreign_key("fk_transactions_account_id", "accounts", ["account_id"], ["id"])
        batch.create_index("ix_transactions_account_id", ["account_id"], unique=False)
        batch.create_unique_constraint("uq_transactions_idempotency_key", ["idempotency_key"])


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_constraint("uq_transactions_idempotency_key", type_="unique")
        batch.drop_index("ix_transactions_account_id")
        batch.drop_constraint("fk_transactions_account_id", type_="foreignkey")
        batch.drop_column("failure_reason")
        batch.drop_column("idempotency_key")
        batch.drop_column("account_id")
    op.drop_index("ix_ledger_account_id_id", table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_transaction_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index(op.f("ix_accounts_customer_id"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_account_number"), table_name="accounts")
    op.drop_table("accounts")
