import redis.asyncio as redis
from fastapi import HTTPException, status

from app.core.config import settings

redis_client = redis.from_url(
    str(settings.redis_url),
    encoding= "utf-8",
    decode_responses=True
)

async def verify_and_lock_request(client, key: str, user_id: int):
    redis_key = f"idempotency:{user_id}:{key}"
    cached_status = await client.get(redis_key)

    if cached_status is not None:
        if cached_status == "PROCESSING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Your order is already being processed. Please wait."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate request: Order already placed with ID {cached_status}"
            )
    await redis_client.set(redis_key, "PROCESSING", ex=300)