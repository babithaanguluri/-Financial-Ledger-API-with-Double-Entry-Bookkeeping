from fastapi import HTTPException

class LedgerError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class AccountNotFoundError(LedgerError):
    def __init__(self):
        super().__init__(status_code=404, detail="Account not found")

class CurrencyMismatchError(LedgerError):
    def __init__(self):
        super().__init__(status_code=400, detail="Currency mismatch between accounts")

class InsufficientFundsError(LedgerError):
    def __init__(self):
        super().__init__(status_code=400, detail="Insufficient funds for transaction")

class InvalidAmountError(LedgerError):
    def __init__(self):
        super().__init__(status_code=400, detail="Transaction amount must be positive")

class DuplicateTransactionError(LedgerError):
    def __init__(self):
        super().__init__(status_code=400, detail="Duplicate transaction detected (idempotency)")
