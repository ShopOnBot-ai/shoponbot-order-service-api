import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.redis import generate_order_cache_key, redis_client
from app.db.base import EventOutbox, Order
from app.db.database import get_db
from app.integrations.user_client import CurrentUser
from app.models.event_outbox import EventStatus
from app.models.orders import CancelledBy
from app.schemas.order import (
    OrderCancelRequest,
    OrderResponse,
    OrderStatus,
    PaginatedOrderResponse,
)
from app.utils.helper import decode_cursor, encode_cursor

router = APIRouter()


@router.get("/", response_model=PaginatedOrderResponse, status_code=status.HTTP_200_OK)
async def get_user_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    limit=10,
    cursor: str | None = None,
):
    try:
        user_id = current_user.get("user_id")

        cursor_id = decode_cursor(cursor)
        logger.info("Decode cursor value: %s", cursor_id)
        cached_key = generate_order_cache_key(
            user_id=user_id, limit=limit, cursor=cursor
        )
        logger.info("cached key: %s", cached_key)
        cached_data = await redis_client.get(cached_key)
        logger.info("cached data: %s", cached_data)
        if cached_data is not None:
            data = json.loads(cached_data)
            logger.info("data: %s", data)
            return PaginatedOrderResponse(
                orders=data.get("orders", []),
                next_cursor=data.get("next_cursor"),
                has_more=data.get("has_more", False),
            )
        query = (
            select(Order)
            .where(Order.user_id == user_id)
            .options(selectinload(Order.items))
        )
        if cursor_id is not None:
            query = query.where(Order.id < cursor_id)
            
        query = query.order_by(Order.id.desc()).limit(int(limit) + 1)
        result = await db.execute(query)
        orders = list(result.scalars().all())
        logger.info("Orders: %s", orders)
        has_more = len(orders) > int(limit)
        if has_more:
            orders.pop()
            logger.info("popped Orders: %s", len(orders))
            last_order_id = orders[-1].id
            logger.info("last order_id: %s", last_order_id)
            next_cursor = encode_cursor(last_order_id)
            logger.info("next cursor: %s", next_cursor)
        else:
            next_cursor = None

        response = PaginatedOrderResponse(
            orders=orders, next_cursor=next_cursor, has_more=has_more
        )
        response_json = response.model_dump_json()
        await redis_client.set(cached_key, response_json, ex=300)
        return response
    except Exception as e:
        raise


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order_by_user(
    db: Annotated[AsyncSession, Depends(get_db)], payload: OrderCancelRequest, order_id: int, current_user: CurrentUser
):
    try:
        user_id = current_user.get("user_id")

        query = (
            select(Order)
            .where(Order.id == order_id, Order.user_id == user_id)
            .options(selectinload(Order.items))
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can't cancel the order after shipped/delivered"
            )

        order.status = OrderStatus.CANCELLED
        order.cancelled_by = CancelledBy.USER
        order.cancellation_reason = payload.cancellation_reason

        publish_event = EventOutbox(
            aggregate_type= "Order",
            aggregate_id=str(order.id),
            event_type="OrderCancelled",
            publish_status=EventStatus.PENDING,
            payload= {
                "order_id": order.id,
                "order_number": order.order_number,
                "user_id": user_id,
                "cancellation_reason": payload.cancellation_reason,
                "items": [
                    {
                        "product_id": item.product_id,
                        "quantity": item.quantity
                    } for item in order.items
                ]
            }
        )
        db.add(publish_event)
        await db.flush()
        await redis_client.delete(f"orders:user:{user_id}:*")
        await db.refresh(order)
        return order

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel Order due to runtime transaction constraint",
        )
