import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger


async def get_user_cart(cookies: dict) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.backend_api_url}/api/v1/cart/",
                cookies=cookies,
                follow_redirects=True,
                timeout=5.0,
            )
            logger.info(
                "Cart service dynamic redirect check - Status: %s", response.status_code
            )
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
                )
            elif response.status_code != 200:
                logger.error("Cart API failed with raw response: %s", response.text)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized or Session Expired",
                )

            cart = response.json()
            logger.info("cart: %s", cart)
            return cart
        except Exception as e:
            logger.exception("Failed to connect to the service: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to connect to the Cart domain service",
            )
