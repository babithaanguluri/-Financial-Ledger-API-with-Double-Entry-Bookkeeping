
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api"

async def main():
    async with httpx.AsyncClient() as client:
        print("Creating Account A...")
        resp = await client.post(f"{BASE_URL}/accounts", json={"name": "Alice"})
        print(resp.json())
        account_a = resp.json()
        assert resp.status_code == 201

        print("\nCreating Account B...")
        resp = await client.post(f"{BASE_URL}/accounts", json={"name": "Bob"})
        print(resp.json())
        account_b = resp.json()
        assert resp.status_code == 201

        print(f"\nDepositing $100 to Alice ({account_a['id']})...")
        deposit_data = {
            "type": "DEPOSIT",
            "amount": 100.00,
            "description": "Initial Deposit",
            "destination_account_id": account_a['id'],
            "idempotency_key": "v-dep-alice-1"
        }
        resp = await client.post(f"{BASE_URL}/deposits", json=deposit_data)
        print(resp.json())
        assert resp.status_code == 200

        print("\nChecking Alice's Balance...")
        resp = await client.get(f"{BASE_URL}/accounts/{account_a['id']}")
        print(resp.json())
        assert float(resp.json()['balance']) == 100.0

        print(f"\nTransferring $30 from Alice to Bob...")
        transfer_data = {
            "type": "TRANSFER",
            "amount": 30.00,
            "description": "Lunch money",
            "source_account_id": account_a['id'],
            "destination_account_id": account_b['id'],
            "idempotency_key": "v-trans-alice-bob-1"
        }
        resp = await client.post(f"{BASE_URL}/transfers", json=transfer_data)
        print(resp.json())
        assert resp.status_code == 200

        print("\nChecking Alice's Balance (Expected 70)...")
        resp = await client.get(f"{BASE_URL}/accounts/{account_a['id']}")
        print(resp.json())
        assert float(resp.json()['balance']) == 70.0

        print("\nChecking Bob's Balance (Expected 30)...")
        resp = await client.get(f"{BASE_URL}/accounts/{account_b['id']}")
        print(resp.json())
        assert float(resp.json()['balance']) == 30.0

        print("\nAttempting Overdraft Transfer ($100 from Alice)...")
        transfer_data['amount'] = 100.00
        transfer_data['idempotency_key'] = "v-failed-trans-1"
        resp = await client.post(f"{BASE_URL}/transfers", json=transfer_data)

        print(resp.json())
        assert resp.status_code == 400

        print("\nVerifying Ledger Entries for Alice...")
        resp = await client.get(f"{BASE_URL}/accounts/{account_a['id']}/ledger")
        entries = resp.json()
        print(f"Found {len(entries)} entries")
        for entry in entries:
            print(f" - {entry['type']} {entry['amount']}")
        
        assert len(entries) >= 2 # Deposit + Transfer

if __name__ == "__main__":
    asyncio.run(main())
