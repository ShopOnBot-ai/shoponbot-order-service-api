from fastapi import APIRouter, Depends

from app.api.v1.endpoints import checkout, orders, payments
from app.api.v1.endpoints.admin import admin_orders
from app.utils.deps import require_admin

api_router = APIRouter()

api_router.include_router(checkout.router, prefix="/checkout", tags=["Checkout"])
api_router.include_router(orders.router, prefix="", tags=["Orders"])
api_router.include_router(payments.router, prefix="/payments/webhook", tags=["Payments"])
api_router.include_router(admin_orders.router, prefix="/admin", tags=["Admin-Orders"], dependencies=[Depends(require_admin)])