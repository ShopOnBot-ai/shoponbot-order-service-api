from fastapi import APIRouter

from app.api.v1.endpoints import checkout

api_router = APIRouter()

api_router.include_router(checkout.router, prefix="/checkout", tags=["Orders"])