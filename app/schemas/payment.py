from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    payment_status: str
    payment_gateway: str
    payment_mode: str | None = None
    transaction_id: str | None = None
    currency: str