
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_account(client: AsyncClient):
    response = await client.post("/api/accounts", json={"name": "Test User", "currency": "USD"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"
    assert float(data["balance"]) == 0.0

@pytest.mark.asyncio
async def test_deposit_flow(client: AsyncClient):
    # Create account
    resp = await client.post("/api/accounts", json={"name": "Depositor"})
    account_id = resp.json()["id"]

    deposit_data = {
        "type": "DEPOSIT",
        "amount": 500.00,
        "description": "Salary",
        "destination_account_id": account_id,
        "idempotency_key": "dep-1"
    }
    resp = await client.post("/api/deposits", json=deposit_data)
    assert resp.status_code == 200
    
    # Check Balance
    resp = await client.get(f"/api/accounts/{account_id}")
    assert resp.status_code == 200
    assert float(resp.json()["balance"]) == 500.00

@pytest.mark.asyncio
async def test_transfer_flow(client: AsyncClient):
    # Setup Accounts
    resp_a = await client.post("/api/accounts", json={"name": "Alice"})
    id_a = resp_a.json()["id"]
    
    resp_b = await client.post("/api/accounts", json={"name": "Bob"})
    id_b = resp_b.json()["id"]

    # Deposit to A
    await client.post("/api/deposits", json={
        "type": "DEPOSIT",
        "amount": 200.00,
        "destination_account_id": id_a,
        "idempotency_key": "dep-alice"
    })

    transfer_data = {
        "type": "TRANSFER",
        "amount": 50.00,
        "description": "Payment",
        "source_account_id": id_a,
        "destination_account_id": id_b,
        "idempotency_key": "trans-1"
    }
    resp = await client.post("/api/transfers", json=transfer_data)
    assert resp.status_code == 200

    # Verify Balances
    resp_a = await client.get(f"/api/accounts/{id_a}")
    assert float(resp_a.json()["balance"]) == 150.00

    resp_b = await client.get(f"/api/accounts/{id_b}")
    assert float(resp_b.json()["balance"]) == 50.00

@pytest.mark.asyncio
async def test_insufficient_funds(client: AsyncClient):
    resp = await client.post("/api/accounts", json={"name": "Broke User"})
    account_id = resp.json()["id"]
    
    # Deposit small amount
    await client.post("/api/deposits", json={
        "type": "DEPOSIT",
        "amount": 10.00,
        "destination_account_id": account_id,
        "idempotency_key": "dep-broke"
    })

    # Try large transfer
    resp = await client.post("/api/accounts", json={"name": "Rich User"})
    dest_id = resp.json()["id"]

    transfer_data = {
        "type": "TRANSFER",
        "amount": 100.00,
        "source_account_id": account_id,
        "destination_account_id": dest_id,
        "idempotency_key": "trans-broke"
    }
    resp = await client.post("/api/transfers", json=transfer_data)
    assert resp.status_code == 400
    assert "Insufficient funds" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_ledger_integrity(client: AsyncClient):
    resp = await client.post("/api/accounts", json={"name": "Ledger User"})
    account_id = resp.json()["id"]
    
    # Perform various ops
    await client.post("/api/deposits", json={"type": "DEPOSIT", "amount": 100, "destination_account_id": account_id, "idempotency_key": "dep-integrity"})
    await client.post("/api/withdrawals", json={"type": "WITHDRAWAL", "amount": 20, "source_account_id": account_id, "idempotency_key": "with-integrity"})
    
    resp = await client.get(f"/api/accounts/{account_id}/ledger")
    entries = resp.json()
    
    # Should have 2 entries
    assert len(entries) == 2
    
    # Calculate balance from entries manually
    balance = 0.0
    for entry in entries:
        if entry["type"] == "CREDIT":
            balance += float(entry["amount"])
        elif entry["type"] == "DEBIT":
            balance -= float(entry["amount"])
    
    assert balance == 80.0

@pytest.mark.asyncio
async def test_idempotency(client: AsyncClient):
    # Setup Account
    resp = await client.post("/api/accounts", json={"name": "Idempotent User"})
    account_id = resp.json()["id"]
    
    idempotency_key = "test-key-123"
    deposit_data = {
        "type": "DEPOSIT",
        "amount": 100.00,
        "destination_account_id": account_id,
        "idempotency_key": idempotency_key
    }
    
    # First request
    resp1 = await client.post("/api/deposits", json=deposit_data)
    assert resp1.status_code == 200
    tx1_id = resp1.json()["id"]
    
    # Second request with same key
    resp2 = await client.post("/api/deposits", json=deposit_data)
    assert resp2.status_code == 200
    tx2_id = resp2.json()["id"]
    
    # IDs should be identical
    assert tx1_id == tx2_id
    
    # Verify balance is only 100, not 200
    resp_balance = await client.get(f"/api/accounts/{account_id}")
    assert float(resp_balance.json()["balance"]) == 100.00

@pytest.mark.asyncio
async def test_transaction_atomicity(client: AsyncClient):
    # Setup Accounts
    resp_a = await client.post("/api/accounts", json={"name": "Alice Atom"})
    id_a = resp_a.json()["id"]
    resp_b = await client.post("/api/accounts", json={"name": "Bob Atom"})
    id_b = resp_b.json()["id"]

    # Deposit to A
    await client.post("/api/deposits", json={
        "type": "DEPOSIT",
        "amount": 100.00,
        "destination_account_id": id_a,
        "idempotency_key": "initial-deposit-atom"
    })

    # Intentional failure: source account doesn't exist for a real transaction?
    # Or mock something?
    # Actually, we can just test that a failed transfer doesn't change balances.
    transfer_data = {
        "type": "TRANSFER",
        "amount": 500.00, # More than balance
        "source_account_id": id_a,
        "destination_account_id": id_b,
        "idempotency_key": "failed-transfer-atom"
    }
    
    resp = await client.post("/api/transfers", json=transfer_data)
    assert resp.status_code == 400
    assert "Insufficient funds" in resp.json()["detail"]
    
    # Verify balances haven't changed
    resp_a = await client.get(f"/api/accounts/{id_a}")
    assert float(resp_a.json()["balance"]) == 100.00
    resp_b = await client.get(f"/api/accounts/{id_b}")
    assert float(resp_b.json()["balance"]) == 0.00

async def test_account_not_found(client: AsyncClient):
    # Test deposit to non-existent account
    random_id = uuid.uuid4()
    resp = await client.post("/api/deposits", json={
        "type": "DEPOSIT",
        "amount": 100.00,
        "destination_account_id": str(random_id),
        "idempotency_key": f"not-found-{random_id}"
    })
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Account not found"

async def test_currency_mismatch(client: AsyncClient):
    # Setup USD and EUR accounts
    resp_usd = await client.post("/api/accounts", json={"name": "USD Account", "currency": "USD"})
    id_usd = resp_usd.json()["id"]
    resp_eur = await client.post("/api/accounts", json={"name": "EUR Account", "currency": "EUR"})
    id_eur = resp_eur.json()["id"]

    # Fund USD account
    await client.post("/api/deposits", json={
        "type": "DEPOSIT",
        "amount": 100.00,
        "destination_account_id": id_usd,
        "idempotency_key": "fund-usd"
    })

    # Try transfer to EUR account
    resp = await client.post("/api/transfers", json={
        "type": "TRANSFER",
        "amount": 50.00,
        "source_account_id": id_usd,
        "destination_account_id": id_eur,
        "idempotency_key": "mismatch-transfer"
    })
    assert resp.status_code == 400
    assert "Currency mismatch" in resp.json()["detail"]

