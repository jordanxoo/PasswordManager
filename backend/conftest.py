import pytest
from httpx import AsyncClient,ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine,AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base,get_db
from unittest.mock import AsyncMock,MagicMock


engine = create_async_engine("sqlite+aiosqlite:///:memory:")

TestingSessionLocal = sessionmaker(engine,class_=AsyncSession,expire_on_commit=False)

@pytest.fixture
async def async_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


    async with TestingSessionLocal() as session:
        yield session

    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(async_session):
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    return db



