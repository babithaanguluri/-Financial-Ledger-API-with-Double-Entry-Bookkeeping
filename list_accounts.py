import asyncio
from app.db.session import AsyncSessionLocal
from app.models import Account
from sqlalchemy import select

async def list_accounts():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account))
        accounts = result.scalars().all()
        with open("results.txt", "w") as f:
            f.write("\n--- AVAILABLE ACCOUNTS ---\n")
            for a in accounts:
                f.write(f"Name: {a.name:20} ID: {a.id}\n")
            f.write("--------------------------\n")

if __name__ == "__main__":
    asyncio.run(list_accounts())
