from pydantic import BaseModel

from app.schemas.order import OrderResponse


class AdminOrdersResponse(BaseModel):
    message: str
    orders: list[OrderResponse]
    page: int
    limit: int
    total_count: int
