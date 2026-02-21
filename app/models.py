
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Enum,
    DateTime,
    ForeignKey,
    Numeric,
    JSON,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"

class TransactionType(str, enum.Enum):
    TRANSFER = "TRANSFER"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"

class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class EntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class Account(Base):
    """
    Represents a financial account in the ledger system.
    Accounts hold currency and are the primary entities for debit/credit operations.
    """
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(Enum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    entries = relationship("LedgerEntry", back_populates="account")

class Transaction(Base):
    """
    Represents an atomic financial event (Transfer, Deposit, Withdrawal).
    A transaction must always have a balanced set of double-entry ledger entries.
    """
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    description = Column(String)
    idempotency_key = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata_json = Column(JSON, nullable=True)


    # Relationships
    entries = relationship("LedgerEntry", back_populates="transaction")

class LedgerEntry(Base):
    """
    The fundamental unit of the double-entry system.
    Every entry is either a DEBIT or CREDIT. The sum of all entries for an account
    represents its current balance.
    """
    __tablename__ = "ledger_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    type = Column(Enum(EntryType), nullable=False)
    amount = Column(Numeric(precision=20, scale=4), nullable=False) # High precision
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    transaction = relationship("Transaction", back_populates="entries")
    account = relationship("Account", back_populates="entries")
