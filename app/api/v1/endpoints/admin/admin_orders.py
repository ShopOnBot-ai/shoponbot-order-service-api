import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.redis import generate_admin_orders_cache_key, redis_client
from app.db.base import EventOutbox, Order
from app.db.database import get_db
from app.models.event_outbox import EventStatus
from app.models.orders import CancelledBy
from app.schemas.admin.admin_orders import (
    AdminOrderRejectRequest,
    AdminOrdersResponse,
)
from app.schemas.order import OrderResponse, OrderStatus

router = APIRouter()


@router.get("/", response_model=AdminOrdersResponse)
async def get_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 10,
    page: int = 1,
    search: str | None = None,
):
    try:
        offset = (page - 1) * limit

        cached_key = generate_admin_orders_cache_key(
            limit=limit, page=page, search=search
        )
        logger.info("cached key: %s", cached_key)
        cached_data = await redis_client.get(cached_key)
        logger.info("cached_data: %s", cached_data)
        if cached_data is not None:
            data = json.loads(cached_data)
            logger.info("data: %s", data)
            return AdminOrdersResponse(
                message="Orders fetched successfully",
                orders=data.get("orders", []),
                page=int(data.get("page", 0)),
                limit=int(data.get("limit", 0)),
                total_count=int(data.get("total_count", 0)),
            )

        query = select(Order).options(selectinload(Order.items))
        if search:
            query = query.where(Order.order_number.ilike(f"%{search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar_one()

        query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        total_orders = result.scalars().all()

        response = AdminOrdersResponse(
            message="Orders fetched successfully",
            orders=total_orders,
            page=page,
            limit=limit,
            total_count=total_count,
        )
        response_json = response.model_dump_json()
        await redis_client.set(cached_key, response_json, ex=300)
        return response
    except Exception as e:
        logger.exception(
            "Global admin orders listing execution collapsed mapping: %s", str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch orders data.",
        )


@router.patch(
    "/{order_id}/accept", response_model=OrderResponse, status_code=status.HTTP_200_OK
)
async def accept_order(db: Annotated[AsyncSession, Depends(get_db)], order_id: int):
    try:
        query = (
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
            )

        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending orders can be accepted.",
            )

        order.status = OrderStatus.PROCESSING

        new_event = EventOutbox(
            aggregate_type="Order",
            aggregate_id=str(order.id),
            event_type="OrderAccepted",
            publish_status=EventStatus.PENDING,
            payload={
                "order_id": order.id,
                "order_number": order.order_number,
                "user_id": order.user_id,
                "total_amount": str(order.total_amount),
            },
        )
        db.add(new_event)
        await db.flush()

        await redis_client.delete(f"orders:user:{order.user_id}:*")
        await redis_client.delete("orders:admin:*")

        await db.refresh(order)
        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Administrative order processing framework collapsed acceptance transaction execution path: %s",
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete administrative state transitions due to runtime database synchronization constraints failures.",
        )


@router.patch(
    "/{order_id}/ship", response_model=OrderResponse, status_code=status.HTTP_200_OK
)
async def ship_order(order_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        query = (
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order record not found."
            )

        if order.status != OrderStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only accepted processing orders can be pushed to shipment status.",
            )

        order.status = OrderStatus.SHIPPED

        new_event = EventOutbox(
            aggregate_type="Order",
            aggregate_id=str(order.id),
            event_type="OrderShipped",
            publish_status=EventStatus.PENDING,
            payload={
                "order_id": order.id,
                "order_number": order.order_number,
                "user_id": order.user_id,
                "status": "shipped",
            },
        )
        db.add(new_event)

        await db.flush()

        await redis_client.delete(f"orders:user:{order.user_id}:*")
        await redis_client.delete("orders:admin:*")

        await db.refresh(order)
        return order

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Shipment configuration transaction pathway collapsed: %s", str(e)
        )
        raise HTTPException(
            status_code=500, detail="Database transactional synchronization failures."
        )


@router.patch(
    "/{order_id}/deliver", response_model=OrderResponse, status_code=status.HTTP_200_OK
)
async def deliver_order(order_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        query = (
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order record not found."
            )

        if order.status != OrderStatus.SHIPPED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only accepted processing orders can be pushed to shipment status.",
            )

        order.status = OrderStatus.DELIVERED

        new_event = EventOutbox(
            aggregate_type="Order",
            aggregate_id=str(order.id),
            event_type="OrderDelivered",
            publish_status=EventStatus.PENDING,
            payload={
                "order_id": order.id,
                "order_number": order.order_number,
                "user_id": order.user_id,
                "status": "delivered",
            },
        )
        db.add(new_event)

        await db.flush()

        await redis_client.delete(f"orders:user:{order.user_id}:*")
        await redis_client.delete("orders:admin:*")

        await db.refresh(order)
        return order

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Delivered configuration transaction pathway collapsed: %s", str(e)
        )
        raise HTTPException(
            status_code=500, detail="Database transactional synchronization failures."
        )


@router.post("/{order_id}/reject", response_model=OrderResponse, status_code=status.HTTP_200_OK)
async def reject_order(
    db: Annotated[AsyncSession, Depends(get_db)], payload: AdminOrderRejectRequest
):
    try:
        order_id = payload.order_id
        reason = payload.cancellation_reason

        query = (
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        order.status = OrderStatus.CANCELLED
        order.cancelled_by = CancelledBy.ADMIN
        order.cancellation_reason = reason

        new_event = EventOutbox(
            aggregate_type="Order",
            aggregate_id=str(order.id),
            event_type="OrderCancelled",
            publish_status=EventStatus.PENDING,
            payload={
                "order_id": order.id,
                "order_number": order.order_number,
                "user_id": order.user_id,
                "status": "Cancelled",
            },
        )
        db.add(new_event)
        await db.flush()

        await redis_client.delete(f"orders:user:{order.user_id}:*")
        await redis_client.delete("orders:admin:*")

        await db.refresh()
        return order

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Cancel configuration transaction pathway collapsed: %s", str(e)
        )
        raise HTTPException(
            status_code=500, detail="Database transactional synchronization failures."
        )
