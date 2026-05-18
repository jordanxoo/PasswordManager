import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app
from app.database import Base, get_db
from app.redis_client import get_redis

TEST_DB_URL = "postgresql+asyncpg://pm_admin:pm_admin@localhost:5433/pm_db_test"

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    #db.delete = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    db.execute.return_value = result
    return db

@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.get.return_value = None
    r.setex.return_value = True
    r.incr.return_value = 1
    r.expire.return_value = True
    r.ttl.return_value = 60
    r.publish.return_value = 1
    return r

@pytest.fixture
async def db():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def client(db, mock_redis):
    async def override_get_db():
        yield db

    async def override_get_redis():
        yield mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    with patch("app.main.connect_rabbitmq", new_callable=AsyncMock), \
        patch("app.main.setup_rabbitmq", new_callable=AsyncMock), \
        patch("app.main.disconnect_rabbitmq", new_callable=AsyncMock), \
        patch("app.main.redis_pubsub_listener", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()

@pytest.fixture
async def auth_headers(client):
    await client.post("/auth/register", json={
        "email": "testuser@test.com",
        "password": "TestPass123!",
        "salt": "testsalt123"
    })
    resp = await client.post("/auth/login", json={
        "email": "testuser@test.com",
        "password": "TestPass123!"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
