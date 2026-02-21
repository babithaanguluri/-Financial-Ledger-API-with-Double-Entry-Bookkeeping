
from uuid import UUID
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.models import AccountStatus, TransactionType, TransactionStatus, EntryType

# Account Schemas
class AccountCreate(BaseModel):
    """
    Schema for creating a new account.
    """
    name: str
    currency: str = "USD"

class AccountResponse(BaseModel):
    """
    Detailed account information including current balance.
    """
    id: UUID
    name: str
    currency: str
    status: AccountStatus
    created_at: datetime
    balance: Decimal

    class Config:
        from_attributes = True

# Ledger Entry Schemas
class LedgerEntryResponse(BaseModel):
    """
    Schema for a single debit or credit entry in the ledger.
    """
    id: UUID
    transaction_id: UUID
    account_id: UUID
    type: EntryType
    amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True

# Transaction Schemas
class TransactionCreate(BaseModel):
    """
    Universal schema for ledger transactions (Transfers, Deposits, Withdrawals).
    Includes mandatory idempotency key.
    """
    type: TransactionType
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    source_account_id: Optional[UUID] = None
    destination_account_id: Optional[UUID] = None
    idempotency_key: str = Field(..., description="Unique key to prevent duplicate transactions")
    metadata: Optional[Dict[str, Any]] = None


    @field_validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

class TransactionResponse(BaseModel):
    """
    Transaction record including the resulting ledger entries.
    """
    id: UUID
    type: TransactionType
    status: TransactionStatus
    description: Optional[str]
    created_at: datetime
    entries: List[LedgerEntryResponse] = []

    class Config:
        from_attributes = True
