from fastapi import APIRouter

from app.api.v1.endpoints import checkout, orders

api_router = APIRouter()

api_router.include_router(checkout.router, prefix="/checkout", tags=["Checkout"])
api_router.include_router(orders.router, prefix="", tags=["Orders"])