from fastapi import APIRouter, HTTPException, Request, status

from app.core.logging import logger
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

router = APIRouter()


@router.post("/summary", response_model=CheckoutSummaryResponse)
async def checkout_summary(
    request: Request,
    payload: CheckoutSummaryRequest,
    user_id: CurrentUserId,
):
    try:
        cart_data = await get_user_cart(request.cookies)
        address_data = None
        if payload.address_id is not None:
            address_data = await get_user_address(payload.address_id, request.cookies)

        bill_summary = CheckoutService.calculate_bill(cart_data, address_data)
        return CheckoutSummaryResponse(
            subtotal= bill_summary["subtotal"],
            tax= bill_summary["tax"],
            shipping_fee= bill_summary["shipping_fee"],
            discount= bill_summary["discount"],
            total_amount= bill_summary["total_amount"]
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to load checkout summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load checkout summary",
        )
