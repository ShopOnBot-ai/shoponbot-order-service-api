import secrets
import string
from datetime import datetime


def generate_order_number(user_id: int) -> str:
    """
    Generate a unique, high-secure auditable order number format
    Format Example: SOB-20260918-A7X92 (SOB - DATE - RANDOM_STRING)
    """
    date_str = datetime.utcnow().strftime("%Y%m%d")
    
    allowed_chars = string.ascii_uppercase + string.digits
    random_str = "".join(secrets.choice(allowed_chars) for _ in range(5))
    order_number = f"SOB-{date_str}-{user_id}-{random_str}"
    
    return order_number
