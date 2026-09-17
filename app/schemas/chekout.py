from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.order import PaymentStatus


class CheckoutSummaryRequest(BaseModel):
    address_id: int | None = None


class CheckoutSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subtotal: Decimal
    tax: Decimal
    shipping_fee: Decimal
    discount: Decimal
    total_amount: Decimal
    idempotency_key: str


class CheckoutRequest(BaseModel):
    address_id: int | None = None
    idempotency_key: str = Field(
        min_length=16,
        max_length=100,
    )


class CheckoutResponse(BaseModel):
    message: str
    order_id: int
    order_number: str
    payment_status: PaymentStatus
    payment_url: str | None = None
