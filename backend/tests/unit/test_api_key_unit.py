import pytest
from unittest.mock import AsyncMock,MagicMock
from uuid import uuid4
from datetime import datetime, timedelta
from app.services.api_key_service import _hash_key,create_api_key,verify_api_key,revoke_api_key
from fastapi import HTTPException


async def test_hash_key_is_deterministic():
    key = "pm_keytest123"
    assert _hash_key(key) == _hash_key(key)
    assert _hash_key(key) != key
    assert len(_hash_key(key)) == 64

async def test_create_api_key_format(mock_db):
    _,raw = await create_api_key(mock_db,uuid4(),"Test Key", "read")

    assert raw.startswith("pm_")
    assert len(raw) == 67

async def test_create_api_key_stores_hash(mock_db):
    record,raw = await create_api_key(mock_db,uuid4(),"Test Key","read")

    assert record.key_hash != raw
    assert record.key_hash  == _hash_key(raw)
    assert len(record.key_hash) == 64


async def test_verify_valid_key(mock_db):
    mock_record = MagicMock()
    mock_record.expires_at = None
    mock_record.user_id = uuid4()
    mock_record.scope = "read"

    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_record
    mock_db.execute.return_value = result

    outcome = await verify_api_key(mock_db,"pm_somevalidkey")
    assert outcome is not None
    user_id, scope = outcome
    assert isinstance(user_id,str)
    assert scope == "read"

async def test_verify_nonexistent_key(mock_db):
    result = await verify_api_key(mock_db,"pm_nonexistent")
    assert result is None

async def test_verify_expired_key(mock_db):
    mock_record = MagicMock()
    mock_record.expires_at = datetime.now() - timedelta(days=1)
    mock_record.user_id = uuid4()
    mock_record.scope = "read"

    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_record
    mock_db.execute.return_value = result

    outcome = await verify_api_key(mock_db,"pm_expiredkey")

    assert outcome is None


async def test_revoke_nonexistent_key(mock_db):
    with pytest.raises(HTTPException) as exc_info:
        await revoke_api_key(mock_db,str(uuid4()),uuid4())
        
    assert exc_info.value.status_code == 404