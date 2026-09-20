from uuid import uuid4


def generate_idempotency_key() -> str:
    """
    Generate a unique random 32-character hexadecimal string 
    """

    return uuid4().hex

async def update_idempotency_state(client, key: str, user_id: int, order_id: int) -> None:
    """
    It will execute to update the status once the order has been safely saved in the database.
    It will change the status from 'PROCESSING' and save the actual `order_id` (with a 24-hour expiry).
    """
    redis_key = f"idempotency:{user_id}:{key}"
    await client.set(redis_key, str(order_id), ex=86400)