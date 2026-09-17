from uuid import uuid4


def generate_idempotency_key() -> str:
    """
    Generate a unique random 32-character hexadecimal string 
    """

    return uuid4().hex