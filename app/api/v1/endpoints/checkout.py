from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.database import get_db
from app.integrations.address_client import get_user_address
from app.integrations.cart_client import get_user_cart
from app.integrations.user_client import CurrentUserId
from app.schemas.chekout import (
    CheckoutRequest,
    CheckoutResponse,
    CheckoutSummaryRequest,
    CheckoutSummaryResponse,
)
from app.services.checkout_service import CheckoutService
from app.utils.idempotency import generate_idempotency_key

router = APIRouter()


@router.post("/summary", response_model=CheckoutSummaryResponse)
async def checkout_summary(
    request: Request,
    payload: CheckoutSummaryRequest,
):
    try:
        cart_data = await get_user_cart(request.cookies)
        address_data = None
        if payload.address_id is not None:
            address_data = await get_user_address(payload.address_id, request.cookies)

        bill_summary = CheckoutService.calculate_bill(cart_data, address_data)
        idempotency_key = generate_idempotency_key()
        return CheckoutSummaryResponse(
            subtotal=bill_summary["subtotal"],
            tax=bill_summary["tax"],
            shipping_fee=bill_summary["shipping_fee"],
            discount=bill_summary["discount"],
            total_amount=bill_summary["total_amount"],
            idempotency_key=idempotency_key
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to load checkout summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load checkout summary",
        )


@router.post("/", response_model=CheckoutResponse)
async def create_order(payload: CheckoutRequest, user_id: CurrentUserId, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        pass
    except HTTPException:
        raise
    except Exception as e:
        raise
