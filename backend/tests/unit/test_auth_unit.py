import pytest
from unittest.mock import AsyncMock,MagicMock,patch
from fastapi import HTTPException
from app.services.auth_service import register_user,login_user
from argon2.exceptions import VerifyMismatchError

async def test_register_existing_email(mock_db):
    
    mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await register_user(mock_db,"test@test.com","password","salt")

    assert exc.value.status_code == 400

async def test_register_new_user(mock_db):

    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    await register_user(mock_db,"new@test.com","password123","salt123")

    mock_db.add.assert_called()
    mock_db.commit.assert_called()


async def test_login_not_existing_user(mock_db,mock_redis):
    
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(HTTPException) as exc:
        await login_user(mock_db,mock_redis,"test@test.com","password123")

    assert exc.value.status_code == 401



async def test_login_wrong_password(mock_db,mock_redis):
    
    mock_user = MagicMock()
    mock_user.password = "hashed_password"
    mock_user.is_blocked = False
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user

    with patch("argon2.PasswordHasher.verify",side_effect = VerifyMismatchError):
        with pytest.raises(HTTPException) as exc:
            await login_user(mock_db,mock_redis,"test@test.com","wrong_password")

    assert exc.value.status_code == 401

