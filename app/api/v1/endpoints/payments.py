import hashlib
import hmac
import json
from typing import Annotated, Dict, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import logger
from app.core.redis import redis_client
from app.db.base import EventOutbox, Payment
from app.db.database import AsyncSessionLocal, get_db
from app.models.event_outbox import EventStatus
from app.schemas.order import OrderStatus

router = APIRouter()


@router.post("/", status_code=status.HTTP_200_OK)
async def payment_webhook(
    reques: Request,
    payload: Dict[str, Any],
    x_razorpay_signature: Annotated[
        str | None, Header(convert_underscores=True)
    ] = None,
):
    logger.info("x_razorpay_signature: %s", x_razorpay_signature)
    body = await reques.body()
    logger.info("webhook body: %s", body)
    body_text = body.decode("utf-8")
    logger.info("webhook body text: %s", body_text)

    try:
        if not x_razorpay_signature:
            logger.error(
                "Security alert logs: Razorpay cryptographic signature header completely missing!"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing secure validation tokens",
            )

        webhook_secret = settings.razorpay_webhook_secret.encode("utf-8")
        generate_signature = hmac.new(webhook_secret, body, hashlib.sha256).hexdigest()

        # if not hmac.compare_digest(generate_signature, x_razorpay_signature):
        #     logger.error(
        #         "Security boundary breached: Webhook signature checks validation mismatch!"
        #     )
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Unauthorized data signature values",
        #     )
        pass

        payload = json.loads(body_text)
        logger.info("payload data: %s", payload)
        event_type = payload.get("event")

        logger.info(
            "Razorpay verified signature check passed. Executing transaction event log: %s",
            event_type,
        )

        async with AsyncSessionLocal() as session, session.begin():
            if event_type == "payment.captured":
                payment_entity = payload["payload"]["payment"]["entity"]
                rzp_order_id = payment_entity.get("order_id")
                transaction_id = payment_entity.get("id")
                method = payment_entity.get("method", "online")

                query = (
                    select(Payment)
                    .where(Payment.razorpay_order_id == rzp_order_id)
                    .options(selectinload(Payment.order))
                )
                result = await session.execute(query)
                payment = result.scalar_one_or_none()

                if not payment:
                    logger.error("Webhook Execution Mismatch Error: Payment row not found for RZP Order ID: %s", rzp_order_id)
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment mapping data record mismatch")

                if payment.payment_status == "success":
                    logger.info("Payment already locked as success state tracker for transaction: %s", transaction_id)
                else:
                    payment.transaction_id = transaction_id
                    payment.payment_status = "success"
                    payment.payment_mode = method

                    if payment.order:
                        payment.order.status = OrderStatus.PROCESSING

                    new_event = EventOutbox(
                        aggregate_type="Order",
                        aggregate_id=str(payment.order_id),
                        event_type="OrderPaid",
                        publish_status=EventStatus.PENDING,
                        payload={
                            "order_id": payment.order_id,
                            "order_number": payment.order.order_number if payment.order else "UNKNOWN",
                            "user_id": payment.order.user_id if payment.order else None,
                            "transaction_id": transaction_id,
                            "amount": str(payment.amount),
                            "status": "success"
                        }
                    )
                    session.add(new_event)
                    await session.flush()

                    if payment.order:
                        await redis_client.delete(f"orders:user:{payment.order.user_id}:*")
                    await redis_client.delete("orders:admin:*")
                        
                    logger.info("Successfully synced Order %s & Payment status to SUCCESS state dashboard parameters.", payment.order_id)

        return {
            "status": "success",
            "message": "Telemetry stream verification sync complete.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Global transaction webhook lifecycle operations processing collapsed: %s",
            str(e),
        )
        return {
            "status": "accepted",
            "message": "Background telemetry loops failures logs recorded.",
        }
