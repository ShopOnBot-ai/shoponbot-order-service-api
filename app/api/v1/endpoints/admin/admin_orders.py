import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.redis import generate_admin_orders_cache_key, redis_client
from app.db.base import Order
from app.db.database import get_db
from app.schemas.admin.admin_orders import AdminOrdersResponse

router = APIRouter()


@router.get("/", response_model=AdminOrdersResponse)
async def get_orders(
    db: Annotated[AsyncSession, Depends(get_db)], 
    limit: int = 10, 
    page: int = 1,
    search: str | None = None
):
    try:
        offset = (page - 1) * limit

        cached_key = generate_admin_orders_cache_key(limit=limit, page=page, search=search)
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
                total_count=int(data.get("total_count", 0))
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
            total_count=total_count
        )
        response_json = response.model_dump_json()
        await redis_client.set(cached_key, response_json , ex=300)
        return response
    except Exception as e:
        logger.exception("Global admin orders listing execution collapsed mapping: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch orders data."
        )
