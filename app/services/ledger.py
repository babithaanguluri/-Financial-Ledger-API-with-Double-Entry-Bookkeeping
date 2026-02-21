from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

# Setup Logger
logger = logging.getLogger(__name__)

from app.models import Account, Transaction, LedgerEntry, AccountStatus, TransactionStatus, EntryType, TransactionType
from app.schemas import AccountCreate, TransactionCreate

class LedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_account(self, account_in: AccountCreate) -> Account:
        """
        Creates a new financial account and persists it to the database.
        """
        account = Account(
            name=account_in.name,
            currency=account_in.currency,
            status=AccountStatus.ACTIVE
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        logger.info(f"Created account: {account.name} (ID: {account.id})")
        return account

    async def get_account_balance(self, account_id: UUID) -> Decimal:
        """
        Calculates the aggregate balance for an account by summing all ledger entries.
        Credits increase balance, debits decrease balance.
        """
        # Sum of credits - Sum of debits? Or simple sum if debits are negative?
        # Typically in double entry: 
        # Assets = Debits (positive)
        # Liabilities/Equity = Credits (positive)
        # But for a simple bank account view: Balance = Credits - Debits
        # Let's assume:
        # Credit = Increase balance (Deposit)
        # Debit = Decrease balance (Withdrawal)
        
        # Calculate total credits
        query_credits = select(func.sum(LedgerEntry.amount)).where(
            LedgerEntry.account_id == account_id,
            LedgerEntry.type == EntryType.CREDIT
        )
        result_credits = await self.db.execute(query_credits)
        total_credits = result_credits.scalar() or Decimal(0)

        # Calculate total debits
        query_debits = select(func.sum(LedgerEntry.amount)).where(
            LedgerEntry.account_id == account_id,
            LedgerEntry.type == EntryType.DEBIT
        )
        result_debits = await self.db.execute(query_debits)
        total_debits = result_debits.scalar() or Decimal(0)
        
        balance = total_credits - total_debits
        logger.debug(f"Retrieved balance for {account_id}: {balance}")
        return balance

    async def get_account(self, account_id: UUID) -> Account:
        """
        Retrieves account metadata by its unique UUID.
        Raises HTTPException 404 if the account does not exist.
        """
        query = select(Account).where(Account.id == account_id)
        result = await self.db.execute(query)
        account = result.scalar_one_or_none()
        if not account:
            logger.warning(f"Account lookup failed: {account_id}")
            raise HTTPException(status_code=404, detail="Account not found")
        return account

    async def process_transfer(self, transaction_in: TransactionCreate):
        """
        Processes an atomic transfer between two accounts with currency validation 
        and sufficient funds checking. Support for idempotency is included.
        """
        # Validation
        if transaction_in.type != TransactionType.TRANSFER:
             raise HTTPException(status_code=400, detail="Invalid transaction type for transfer")
        if transaction_in.amount <= 0:
            raise HTTPException(status_code=400, detail="Transaction amount must be positive")
        if not transaction_in.source_account_id or not transaction_in.destination_account_id:
            raise HTTPException(status_code=400, detail="Source and destination accounts required")
        
        # Idempotency check before starting transaction
        existing_tx_query = select(Transaction).where(Transaction.idempotency_key == transaction_in.idempotency_key)
        existing_tx_result = await self.db.execute(existing_tx_query)
        existing_tx = existing_tx_result.scalar_one_or_none()
        if existing_tx:
            query = select(Transaction).options(selectinload(Transaction.entries)).where(Transaction.id == existing_tx.id)
            result = await self.db.execute(query)
            return result.scalar_one()

        try:
            source_account = await self.get_account(transaction_in.source_account_id)
            dest_account = await self.get_account(transaction_in.destination_account_id)

            if not source_account or not dest_account:
                raise HTTPException(status_code=404, detail="Account not found")

            if source_account.currency != dest_account.currency:
                 raise HTTPException(status_code=400, detail="Currency mismatch")

            # Check sufficient funds
            current_balance = await self.get_account_balance(source_account.id)
            if current_balance < transaction_in.amount:
                raise HTTPException(status_code=400, detail="Insufficient funds")

            # Create Transaction
            transaction = Transaction(
                type=TransactionType.TRANSFER,
                status=TransactionStatus.PENDING,
                description=transaction_in.description,
                idempotency_key=transaction_in.idempotency_key,
                metadata_json=transaction_in.metadata
            )
            self.db.add(transaction)
            await self.db.flush() # Get ID

            # Create Ledger Entries
            # Debit Source (Decrease)
            debit_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=source_account.id,
                type=EntryType.DEBIT,
                amount=transaction_in.amount
            )
            # Credit Destination (Increase)
            credit_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=dest_account.id,
                type=EntryType.CREDIT,
                amount=transaction_in.amount
            )
            self.db.add(debit_entry)
            self.db.add(credit_entry)

            transaction.status = TransactionStatus.COMPLETED
            await self.db.commit()
            logger.info(f"Transfer successful: {transaction_in.amount} {source_account.currency} from {source_account.id} to {dest_account.id} (TX: {transaction.id})")
            
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

        # Load entries for response after commit
        query = select(Transaction).options(selectinload(Transaction.entries)).where(Transaction.id == transaction.id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def process_deposit(self, transaction_in: TransactionCreate):
        """
        Processes a deposit into an account by creating a credit entry and 
        a balancing debit entry for the SYSTEM_VAULT.
        """
        if transaction_in.type != TransactionType.DEPOSIT:
            raise HTTPException(status_code=400, detail="Invalid transaction type")
        if transaction_in.amount <= 0:
            raise HTTPException(status_code=400, detail="Transaction amount must be positive")
        if not transaction_in.destination_account_id:
            raise HTTPException(status_code=400, detail="Destination account required")
        
        # Idempotency check
        existing_tx_query = select(Transaction).where(Transaction.idempotency_key == transaction_in.idempotency_key)
        existing_tx_result = await self.db.execute(existing_tx_query)
        existing_tx = existing_tx_result.scalar_one_or_none()
        if existing_tx:
            query = select(Transaction).options(selectinload(Transaction.entries)).where(Transaction.id == existing_tx.id)
            result = await self.db.execute(query)
            return result.scalar_one()

        try:
            dest_account = await self.get_account(transaction_in.destination_account_id)
            if not dest_account:
                raise HTTPException(status_code=404, detail="Account not found")

            transaction = Transaction(
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.PENDING,
                description=transaction_in.description,
                idempotency_key=transaction_in.idempotency_key,
                metadata_json=transaction_in.metadata
            )
            self.db.add(transaction)
            await self.db.flush()

            # Credit Destination (Increase)
            credit_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=dest_account.id,
                type=EntryType.CREDIT,
                amount=transaction_in.amount
            )
            
            # Create a SYSTEM account for balancing.
            system_account_query = select(Account).where(Account.name == "SYSTEM_VAULT")
            result = await self.db.execute(system_account_query)
            system_account = result.scalar_one_or_none()
            
            if not system_account:
                 system_account = Account(name="SYSTEM_VAULT", currency="USD", status=AccountStatus.ACTIVE)
                 self.db.add(system_account)
                 await self.db.flush()
            
            debit_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=system_account.id,
                type=EntryType.DEBIT,
                amount=transaction_in.amount
            )
            
            self.db.add(credit_entry)
            self.db.add(debit_entry)

            transaction.status = TransactionStatus.COMPLETED
            await self.db.commit()
            logger.info(f"Deposit successful: {transaction_in.amount} to {dest_account.id} (TX: {transaction.id})")

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

        query = select(Transaction).options(selectinload(Transaction.entries)).where(Transaction.id == transaction.id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def process_withdrawal(self, transaction_in: TransactionCreate):
        """
        Processes a withdrawal from an account by creating a debit entry and 
        a balancing credit entry for the SYSTEM_VAULT.
        """
        if transaction_in.type != TransactionType.WITHDRAWAL:
            raise HTTPException(status_code=400, detail="Invalid transaction type")
        if transaction_in.amount <= 0:
            raise HTTPException(status_code=400, detail="Transaction amount must be positive")
        if not transaction_in.source_account_id:
             raise HTTPException(status_code=400, detail="Source account required")
        
        # Idempotency check
        existing_tx_query = select(Transaction).where(Transaction.idempotency_key == transaction_in.idempotency_key)
        existing_tx_result = await self.db.execute(existing_tx_query)
        existing_tx = existing_tx_result.scalar_one_or_none()
        if existing_tx:
            query = select(Transaction).options(selectinload(Transaction.entries)).where(Transaction.id == existing_tx.id)
            result = await self.db.execute(query)
            return result.scalar_one()

        try:
            source_account = await self.get_account(transaction_in.source_account_id)
            if not source_account:
                raise HTTPException(status_code=404, detail="Account not found")
            
            current_balance = await self.get_account_balance(source_account.id)
            if current_balance < transaction_in.amount:
                 raise HTTPException(status_code=400, detail="Insufficient funds")

            transaction = Transaction(
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.PENDING,
                description=transaction_in.description,
                idempotency_key=transaction_in.idempotency_key,
                metadata_json=transaction_in.metadata
            )
            self.db.add(transaction)
            await self.db.flush()

            # Debit Source (Decrease)
            debit_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=source_account.id,
                type=EntryType.DEBIT,
                amount=transaction_in.amount
            )
            
            # Credit System (Increase vault)
            system_account_query = select(Account).where(Account.name == "SYSTEM_VAULT")
            result = await self.db.execute(system_account_query)
            system_account = result.scalar_one_or_none()
            
            if not system_account:
                 system_account = Account(name="SYSTEM_VAULT", currency="USD", status=AccountStatus.ACTIVE)
                 self.db.add(system_account)
                 await self.db.flush()

            credit_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=system_account.id,
                type=EntryType.CREDIT,
                amount=transaction_in.amount
            )

            self.db.add(debit_entry)
            self.db.add(credit_entry)
            
            transaction.status = TransactionStatus.COMPLETED
            await self.db.commit()
            logger.info(f"Withdrawal successful: {transaction_in.amount} from {source_account.id} (TX: {transaction.id})")

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

        query = select(Transaction).options(selectinload(Transaction.entries)).where(Transaction.id == transaction.id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_ledger_entries(self, account_id: UUID):
        """
        Returns all ledger entries associated with a specific account ID.
        """
        query = select(LedgerEntry).where(LedgerEntry.account_id == account_id).order_by(LedgerEntry.created_at)
        result = await self.db.execute(query)
        entries = result.scalars().all()
        logger.debug(f"Retrieved {len(entries)} ledger entries for {account_id}")
        return entries
