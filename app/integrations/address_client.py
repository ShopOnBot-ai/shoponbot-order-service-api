import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger


async def get_user_address(address_id: int, cookies: dict) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.backend_api_url}/api/v1/address/{address_id}",
                cookies=cookies,
            )
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
                )
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized or Session Expired",
                )

            address = response.json()
            logger.info("address: %s", address)
            return address
        except Exception as e:
            logger.exception("Failed to connect to the service: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to connect to the Address domain service",
            )
