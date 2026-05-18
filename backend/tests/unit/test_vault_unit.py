import pytest
from unittest.mock import AsyncMock,MagicMock
from fastapi import HTTPException
from app.services.vault_service import get_vaults,create_vault,update_vault,delete_vault
from app.models.enums import Category


async def test_get_vaults_returns_list(mock_db):
    mock_vaults = [MagicMock(),MagicMock()]
    mock_db.execute.return_value.scalars.return_value.all.return_value = mock_vaults
  
    result = await get_vaults(mock_db,"user-123")

    assert result == mock_vaults
    mock_db.execute.assert_called_once()

async def test_get_vaults_with_category(mock_db):
    mock_db.return_value.scalars.return_value.all.return_value = []

    result = await get_vaults(mock_db,"user-123",category=Category.WORK)

    mock_db.execute.assert_called_once()

    assert result == []

async def test_create_vault_adds_and_commits(mock_db):
    data = MagicMock()
    data.name = "testG"
    data.url = "testG.com"
    data.encrypted = "enc123"
    data.iv = "iv123"
    data.expires_at = None
    data.category = None

    await create_vault(mock_db,"user-123",data)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh_assert_called_once()


async def test_update_vault_not_found(mock_db):

    mock_db.execute.return_value.scalar_one_or_none.return_value= None

    with pytest.raises(HTTPException) as exc:
        await update_vault(mock_db,"user-123","vault-456",MagicMock())

    assert exc.value.status_code == 404


async def test_update_vault_forbidden(mock_db):
    mock_vault = MagicMock()
    mock_vault.user_id = "other-user"

    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_vault

    with pytest.raises(HTTPException) as exc:
        await update_vault(mock_db,"user-123","vault-456",MagicMock())


    assert exc.value.status_code == 403


async def test_update_vault_success(mock_db):
    mock_vault = MagicMock()
    mock_vault.user_id = "user-123"
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_vault

    data = MagicMock()
    data.name = "update ok"
    data.url = "update.com"
    data.encrypted = "new_enc"
    data.iv = "new_iv"
    data.expires_at = None
    data.category = None

    await update_vault(mock_db,"user-123","vault-456",data)

    assert mock_vault.name == "update ok"
    mock_db.commit.assert_called_once()



async def test_delete_vault_not_found(mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(HTTPException) as exc:
        await delete_vault(mock_db,"user-123","vault-456")


    assert exc.value.status_code == 404


async def test_delete_vault_forbidden(mock_db):

    mock_vault = MagicMock()
    mock_vault.user_id = "other-user"
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_vault

    with pytest.raises(HTTPException) as exc:
        await delete_vault(mock_db,"user-123","vault-456")

    assert exc.value.status_code == 403

async def test_delete_vault_success(mock_db):
    mock_vault = MagicMock()
    mock_vault.user_id = "user-123"
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_vault

    result = await delete_vault(mock_db,"user-123","vault-456")

    mock_db.delete.assert_called_once()
    mock_db.commit.assert_called_once()
    assert result == {"message":"deleted"}