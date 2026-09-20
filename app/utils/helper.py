import base64
import secrets
import string
from datetime import datetime

from app.core.logging import logger


def generate_order_number(user_id: int) -> str:
    """
    Generate a unique, high-secure auditable order number format
    Format Example: SOB-20260918-A7X92 (SOB - DATE - RANDOM_STRING)
    """
    date_str = datetime.utcnow().strftime("%Y%m%d")
    
    allowed_chars = string.ascii_uppercase + string.digits
    random_str = "".join(secrets.choice(allowed_chars) for _ in range(5))
    order_number = f"SOB-{date_str}-{user_id}-{random_str}"
    logger.info("order number: %s", order_number)
    
    return order_number



def encode_cursor(order_id: int) -> str:
    """convert Integer ID to safe Base64 string cursor."""
    return base64.b64encode(str(order_id).encode("utf-8")).decode("utf-8")

def decode_cursor(cursor_str: str) -> int | None:
    """convert/decode back Base64 string cursor into Integer ID."""
    if not cursor_str:
        return None
    try:
        return int(base64.b64decode(cursor_str.encode("utf-8")).decode("utf-8"))
    except Exception:
        return None

