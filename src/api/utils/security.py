from fastapi import Depends, HTTPException, status
from typing import List, Dict, Optional
from fastapi.security import OAuth2PasswordBearer
from api.db.user import get_user_role_in_org
from api.utils.db import get_new_db_connection

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    # This is a placeholder. In a real application, you would decode the token
    # and extract the user ID. For now, we'll assume the token *is* the user ID.
    try:
        user_id = int(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id

async def get_current_user(user_id: int = Depends(get_current_user_id)) -> Dict:
    # In a real application, you might fetch more user details here
    # For now, we'll return a basic dictionary with the user_id
    return {"id": user_id}

def role_checker(allowed_roles: List[str]):
    async def check_roles(user: Dict = Depends(get_current_user), org_id: Optional[int] = None):
        # For routes that don't have an org_id in the path, it can be passed as a query param
        if org_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization ID is required for role-based access control."
            )

        user_id = user.get("id")
        async with get_new_db_connection() as conn:
            user_role = await get_user_role_in_org(conn, user_id, org_id)
        
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action."
            )
        return user_id, org_id # Return user_id and org_id for use in the route
    return check_roles