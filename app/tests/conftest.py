
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.db.session import get_db
from app.core.config import settings

@pytest_asyncio.fixture(loop_scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Create engine within the fixture/loop to avoid sharing across different loops
    engine = create_async_engine(settings.DATABASE_URL)
    TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with TestingSessionLocal() as session:
        yield session
    
    await engine.dispose()

@pytest_asyncio.fixture(loop_scope="function")
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    # Override get_db dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Create transport with the app
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    
    app.dependency_overrides.clear()
