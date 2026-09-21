from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.logging import logger


async def get_current_user(request: Request) -> dict:
    cookies = request.cookies

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.backend_api_url}/api/v1/user/me", cookies=cookies)
            logger.info("response: %s", response)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized"
                )

            user_data = response.json()
            logger.info("user_data: %s", user_data)
            return {
                "user_id": int(user_data.get("id")),
                "role": user_data.get("role")
            }

        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to connect to the Auth service"
            )


CurrentUser = Annotated[dict, Depends(get_current_user)]