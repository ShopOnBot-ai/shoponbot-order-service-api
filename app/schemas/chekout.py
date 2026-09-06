from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.address import AddressBase
from app.schemas.order import OrderItemResponse, OrderStatus, PaymentStatus


class CheckoutRequest(BaseModel):
    address_id: int | None = None

    shipping_address: AddressBase | None = None

    idempotency_key: str = Field(
        min_length=16,
        max_length=100,
    )

    @model_validator(mode="after")
    def validate_address(self):
        if self.address_id is None and self.shipping_address is None:
            raise ValueError("Either address_id or shipping_address is required")

        if self.address_id is not None and self.shipping_address is not None:
            raise ValueError("Provide either address_id or shipping_address, not both")

        return self


class CheckoutResponse(BaseModel):
    order_id: int
    order_number: str

    status: OrderStatus
    payment_status: PaymentStatus

    items: list[OrderItemResponse]

    shipping_address: AddressBase

    subtotal: Decimal
    tax: Decimal | None = None
    shipping_fee: Decimal | None = None
    discount: Decimal | None = None
    total_amount: Decimal

    currency: str
