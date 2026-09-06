from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict


class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    PAYMENT_PENDING = "payment-pending"
    PAYMENT_FAILED = "payment-failed"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


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
    payment_status: PaymentStatus

    subtotal: Decimal
    tax: Decimal | None = None
    shipping_fee: Decimal | None = None
    discount: Decimal | None = None
    total_amount: Decimal
    currency: str

    shipping_address: dict

    items: list[OrderItemResponse]

    created_at: datetime
    updated_at: datetime
