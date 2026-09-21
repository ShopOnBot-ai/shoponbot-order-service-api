from fastapi import HTTPException, status

from app.integrations.user_client import CurrentUser


async def require_admin(current_user: CurrentUser):
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to this administrative role"
        )

    return current_user