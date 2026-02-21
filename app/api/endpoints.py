
from typing import List, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas import (
    AccountCreate,
    AccountResponse,
    TransactionCreate,
    TransactionResponse,
    LedgerEntryResponse
)
from app.services.ledger import LedgerService

router = APIRouter()

@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(account: AccountCreate, db: AsyncSession = Depends(get_db)):
    service = LedgerService(db)
    new_account = await service.create_account(account)
    # Balance is 0 for new account
    return AccountResponse(
        id=new_account.id,
        name=new_account.name,
        currency=new_account.currency,
        status=new_account.status,
        created_at=new_account.created_at,
        balance=0
    )

@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: UUID, db: AsyncSession = Depends(get_db)):
    service = LedgerService(db)
    account = await service.get_account(account_id)
    
    balance = await service.get_account_balance(account_id)
    
    return AccountResponse(
        id=account.id,
        name=account.name,
        currency=account.currency,
        status=account.status,
        created_at=account.created_at,
        balance=balance
    )

@router.get("/accounts/{account_id}/ledger", response_model=List[LedgerEntryResponse])
async def get_account_ledger(account_id: UUID, db: AsyncSession = Depends(get_db)):
    service = LedgerService(db)
    await service.get_account(account_id)
        
    entries = await service.get_ledger_entries(account_id)
    return entries

@router.post("/transfers", response_model=TransactionResponse)
async def create_transfer(transaction: TransactionCreate, db: AsyncSession = Depends(get_db)):
    service = LedgerService(db)
    return await service.process_transfer(transaction)

@router.post("/deposits", response_model=TransactionResponse)
async def create_deposit(transaction: TransactionCreate, db: AsyncSession = Depends(get_db)):
    service = LedgerService(db)
    return await service.process_deposit(transaction)

@router.post("/withdrawals", response_model=TransactionResponse)
async def create_withdrawal(transaction: TransactionCreate, db: AsyncSession = Depends(get_db)):
    service = LedgerService(db)
    return await service.process_withdrawal(transaction)
