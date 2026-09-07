from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.address import Address
from app.schemas.address import AddressRequest, AddressResponse, AddressesResponse
from app.utils.helper import CurrentUser, logger

router = APIRouter()


@router.post("/", response_model=AddressResponse)
async def create_addresses(
    payload: AddressRequest,
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await db.execute(select(Address).where(Address.user_id == user_id, Address.address_line1 == payload.address_line1))
        address = result.scalar_one_or_none()
        logger.info("address: %s", address)

        if address is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Address already exist"
            )

        new_address = Address(
            user_id= user_id,
            name=payload.name,
            phone=payload.phone,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            postal_code=payload.postal_code,
            country=payload.country,
            latitude=payload.latitude,
            longitude=payload.longitude
        )

        db.add(new_address)
        await db.flush()
        await db.refresh(new_address)
        response = AddressResponse(
            message="Address created successfully",
            id=new_address.id,
            user_id=new_address.user_id,
            address=payload,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Database Runtime Error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add new address",
        )



@router.get("/", response_model=AddressesResponse)
async def get_all_addresses(user_id: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        results = await db.execute(select(Address).where(Address.user_id == user_id))
        addresses = results.scalars().all()
        logger.info("addresses: %s", addresses)

        if addresses is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Addresses found for this user, please create atleast one address first"
            )

        response = AddressesResponse(
            message="Addresses fetched successfully",
            user_id=user_id,
            addresses=addresses
        )
        return response
    except Exception as e:
        logger.exception("Failed to fetch addresses: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch addresses"
        )
