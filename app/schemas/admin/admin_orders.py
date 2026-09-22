from pydantic import BaseModel, Field

from app.schemas.order import OrderResponse


class AdminOrdersResponse(BaseModel):
    message: str
    orders: list[OrderResponse]
    page: int
    limit: int
    total_count: int


class AdminOrderRejectRequest(BaseModel):
    order_id: int
    cancellation_reason: str = Field(min_length=5, max_length=255)
