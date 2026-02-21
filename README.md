
# Financial Ledger API

A robust financial ledger API implementing double-entry bookkeeping principles, ACID transactions, and immutability. Built with FastAPI, PostgreSQL, and SQLAlchemy.

## Features

- **Double-Entry Bookkeeping**: Every transaction creates balanced debit and credit entries.
- **ACID Transactions**: Operations are atomic; any failure rolls back the entire transaction.
- **Immutability**: Ledger entries are append-only.
- **Balance Integrity**: Prevents overdrafts with pre-commit checks.
- **Comprehensive API**: REST endpoints for accounts, transfers, deposits, and withdrawals.
- **Automated Testing**: Pytest suite ensuring correctness and concurrency handling.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (via Docker)
- **ORM**: SQLAlchemy (Async)
- **Testing**: Pytest, Httpx, Pytest-Asyncio

## Setup

### 1. Prerequisites

- Python 3.9+
- Docker & Docker Compose

### 2. Installation

1. Clone the repository (if applicable) or navigate to the project directory.
2. Install dependencies:

```bash
pip install -r requirements.txt
pip install pytest-asyncio  # For running tests
```

### 3. Database Setup

Start the PostgreSQL database using Docker Compose:

```bash
docker-compose up -d
```
The database will be available at `localhost:5435`.

## Running the Application

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The API will be available at [http://localhost:8000](http://localhost:8000).
Interactive API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).

## Verification and Testing

### Automated Tests

Run the comprehensive test suite:

```bash
python -m pytest app/tests/test_ledger.py -v
```

### Manual Verification Script

Run the included verification script to simulate a user flow:

```bash
python verify_api.py
```

## API Endpoints

All transaction endpoints (`/transfers`, `/deposits`, `/withdrawals`) require a mandatory `idempotency_key` to prevent duplicate processing.

### 1. Accounts

#### **POST /api/accounts**
Create a new account.
- **Request Body**:
  ```json
  {
    "name": "John Doe",
    "currency": "USD"
  }
  ```
- **Response**: `AccountResponse` object.

#### **GET /api/accounts/{id}**
Get account details and current balance.
- **Response**: `AccountResponse` object including `balance`.

#### **GET /api/accounts/{id}/ledger**
Get the complete transaction history for an account.
- **Response**: List of `LedgerEntryResponse` objects.

### 2. Transactions

#### **POST /api/deposits**
Deposit funds into an account.
- **Request Body**:
  ```json
  {
    "type": "DEPOSIT",
    "amount": 1000.00,
    "destination_account_id": "uuid-here",
    "idempotency_key": "unique-client-generated-key",
    "description": "Salary deposit"
  }
  ```

#### **POST /api/withdrawals**
Withdraw funds from an account.
- **Request Body**:
  ```json
  {
    "type": "WITHDRAWAL",
    "amount": 200.00,
    "source_account_id": "uuid-here",
    "idempotency_key": "unique-client-generated-key",
    "description": "ATM Withdrawal"
  }
  ```

#### **POST /api/transfers**
Transfer funds between two accounts.
- **Request Body**:
  ```json
  {
    "type": "TRANSFER",
    "amount": 50.00,
    "source_account_id": "8a7b6c5d-4e3f-2b1a-0d9c-8b7a6f5e4d3c",
    "destination_account_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "idempotency_key": "unique-client-generated-key",
    "description": "Lunch split"
  }
  ```
## Live Demo Example

Follow these steps for a complete end-to-end demonstration:

### Step 1: Create Two Accounts
**POST** `/api/accounts`
```json
{ "name": "Alice Demo", "currency": "USD" }
```
*(Note the returned ID, e.g., `ID_A`)*

**POST** `/api/accounts`
```json
{ "name": "Bob Demo", "currency": "USD" }
```
*(Note the returned ID, e.g., `ID_B`)*

### Step 2: Deposit Funds to Alice
**POST** `/api/deposits`
```json
{
  "type": "DEPOSIT",
  "amount": 500.00,
  "destination_account_id": "ID_A",
  "idempotency_key": "demo-deposit-001",
  "description": "Initial Capital"
}
```

### Step 3: Transfer to Bob
**POST** `/api/transfers`
```json
{
  "type": "TRANSFER",
  "amount": 150.00,
  "source_account_id": "ID_A",
  "destination_account_id": "ID_B",
  "idempotency_key": "demo-transfer-001",
  "description": "Payment for services"
}
```

### Step 4: Verify Balances
**GET** `/api/accounts/ID_A` → Should show **350.00**
**GET** `/api/accounts/ID_B` → Should show **150.00**

### Step 5: Test Idempotency
Resend the **Step 3** request. 
- **Expected**: You get the *same* transaction ID back, and balances **do not change**.
