import pytest
from fastapi import HTTPException, status
from unittest.mock import AsyncMock, patch
from api.utils.security import role_checker, get_current_user
from api.db.user import get_user_role_in_org
from api.utils.db import get_new_db_connection

# Mock for get_current_user_id, assuming it returns a user ID
@pytest.fixture
def mock_get_current_user_id():
    return lambda: 1 # Always return user ID 1 for tests

# Mock for get_new_db_connection
@pytest.fixture
async def mock_db_connection():
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.cursor.return_value = mock_cursor
    with patch('api.utils.db.get_new_db_connection', return_value=AsyncMock(aenter=AsyncMock(return_value=mock_conn), aexit=AsyncMock(return_value=None))):
        yield mock_conn, mock_cursor

@pytest.mark.asyncio
async def test_role_checker_authorized_role(mock_db_connection, mock_get_current_user_id):
    _, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = ("ADMIN",)

    checker = role_checker(["ADMIN"])
    user_id, org_id = await checker(user=await get_current_user(mock_get_current_user_id()), org_id=123)

    assert user_id == 1
    assert org_id == 123
    mock_cursor.fetchone.assert_called_once_with()
    mock_cursor.execute.assert_called_once_with(
        "SELECT role FROM user_organizations WHERE user_id = ? AND org_id = ?",
        (1, 123)
    )

@pytest.mark.asyncio
async def test_role_checker_unauthorized_role(mock_db_connection, mock_get_current_user_id):
    _, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = ("MEMBER",)

    checker = role_checker(["ADMIN"])

    with pytest.raises(HTTPException) as exc_info:
        await checker(user=await get_current_user(mock_get_current_user_id()), org_id=123)
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "You do not have permission to perform this action."

@pytest.mark.asyncio
async def test_role_checker_no_org_id(mock_get_current_user_id):
    checker = role_checker(["ADMIN"])
    with pytest.raises(HTTPException) as exc_info:
        await checker(user=await get_current_user(mock_get_current_user_id()))
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Organization ID is required for role-based access control."

@pytest.mark.asyncio
async def test_role_checker_no_role_found(mock_db_connection, mock_get_current_user_id):
    _, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = None # No role found

    checker = role_checker(["ADMIN"])

    with pytest.raises(HTTPException) as exc_info:
        await checker(user=await get_current_user(mock_get_current_user_id()), org_id=123)
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "You do not have permission to perform this action."