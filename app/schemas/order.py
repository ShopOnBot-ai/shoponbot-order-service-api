from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.payment import PaymentResponse


class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    PAYMENT_PENDING = "payment-pending"
    PAYMENT_FAILED = "payment-failed"


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    product_price: Decimal
    quantity: int
    subtotal: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    order_number: str

    status: OrderStatus

    subtotal: Decimal
    tax: Decimal | None = None
    shipping_fee: Decimal | None = None
    discount: Decimal | None = None
    total_amount: Decimal

    shipping_address: dict

    items: list[OrderItemResponse]
    payment: PaymentResponse | None = None

    created_at: datetime
    updated_at: datetime


class PaginatedOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    orders: list[OrderResponse]
    next_cursor: str | None = None
    has_more: bool = False


class OrderCancelRequest(BaseModel):
    cancellation_reason: str = Field(min_length=5, max_length=100)