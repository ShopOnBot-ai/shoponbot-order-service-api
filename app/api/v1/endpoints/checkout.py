from typing import Annotated

import razorpay
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.redis import redis_client, verify_and_lock_request
from app.db.base import EventOutbox, Order, OrderItem, Payment
from app.db.database import get_db
from app.integrations.address_client import get_user_address
from app.integrations.cart_client import get_user_cart
from app.integrations.user_client import CurrentUser
from app.models.event_outbox import EventStatus
from app.models.orders import OrderStatus
from app.schemas.chekout import (
    CheckoutRequest,
    CheckoutResponse,
    CheckoutSummaryRequest,
    CheckoutSummaryResponse,
)
from app.services.checkout_service import CheckoutService
from app.utils.helper import generate_order_number
from app.utils.idempotency import generate_idempotency_key, update_idempotency_state

router = APIRouter()

razorpay_client = razorpay.Client(
    auth=(settings.razorpay_api_key.get_secret_value(), settings.razorpay_key_secret.get_secret_value())
)


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
            idempotency_key=idempotency_key,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to load checkout summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load checkout summary",
        )


@router.post("/", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: CheckoutRequest,
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user_id = current_user.get("user_id")
        await verify_and_lock_request(
            client=redis_client, key=payload.idempotency_key, user_id=user_id
        )
        address_data = await get_user_address(payload.address_id, request.cookies)
        logger.info("address data from post checkout: %s", address_data)

        if not address_data or not address_data.get("addresses"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid shiiping address selection",
            )
        target_shipping_address = address_data.get("addresses")[0]
        logger.info("target shiiping address: %s", target_shipping_address)

        cart_data = await get_user_cart(request.cookies)
        logger.info("cart data from post checkout: %s", cart_data)
        
        bill_summary = CheckoutService.calculate_bill(cart_data, address_data)
        order_num = generate_order_number(user_id)

        new_order = Order(
            user_id=user_id,
            order_number=order_num,
            status=OrderStatus.PENDING,
            subtotal=bill_summary["subtotal"],
            tax=bill_summary["tax"],
            shipping_fee=bill_summary["shipping_fee"],
            discount=bill_summary["discount"],
            total_amount=bill_summary["total_amount"],
            shipping_address=target_shipping_address,
        )
        db.add(new_order)
        await db.flush()

        for item in bill_summary.get("items", []):
            new_item = OrderItem(
                order_id=new_order.id,
                product_id=item.get("product_id"),
                product_name=item.get("product", {}).get("title"),
                product_price=item.get("product", {}).get("price"),
                quantity=item.get("quantity"),
                subtotal=item.get("subtotal"),
            )
            db.add(new_item)
        await db.flush()

        try:
            razorpay_amount_paise = int(new_order.total_amount * 100)
            razorpay_order_response = razorpay_client.order.create({
                "amount": razorpay_amount_paise,
                "currency": "INR",
                "receipt": f"receipt_order_{new_order.id}",
                "payment_capture": 1 
            })
            rzp_order_id = razorpay_order_response.get("id")
            logger.info("Successfully generated Razorpay Order ID reference token: %s", rzp_order_id)

        except Exception as razorpay_err:
            logger.error("External payment gateway communication collapse: %s", str(razorpay_err))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to initialize secure transaction sessions token from payment provider cluster."
            )

        new_payment = Payment(
            order_id=new_order.id,
            amount=new_order.total_amount,
            razorpay_order_id=rzp_order_id,
            payment_status="pending",
            payment_gateway="razorpay",
            currency="INR"
        )
        db.add(new_payment)
        await db.flush()


        new_event = EventOutbox(
            aggregate_type="Order",
            aggregate_id=str(new_order.id),
            event_type="OrderCreated",
            payload={
                "order_id": new_order.id,
                "order_number": new_order.order_number,
                "user_id": user_id,
                "total_amount": str(new_order.total_amount),
                "items": [
                    {
                        "product_id": item.get("product_id"),
                        "title": item.get("product", {}).get("title"),
                        "quantity": item.get("quantity"),
                    }
                    for item in bill_summary.get("items", [])
                ],
            },
            publish_status=EventStatus.PENDING,
        )
        db.add(new_event)
        await db.flush()

        await update_idempotency_state(
            client=redis_client,
            key=payload.idempotency_key,
            user_id=user_id,
            order_id=new_order.id,
        )
        await db.refresh(new_order)
        return CheckoutResponse(
            message="Order placed successfully",
            order_id=new_order.id,
            order_number=new_order.order_number,
            payment_status="pending",
            razorpay_order_id=rzp_order_id,
            payment_url=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Order processing pipeline collapsed initialization: %s", str(e)
        )

        redis_key = f"idempotency:{user_id}:{payload.idempotency_key}"
        await redis_client.delete(redis_key)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Order processing failed due to runtime transaction constraint",
        )
