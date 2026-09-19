from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.integrations.user_client import CurrentUserId
from app.schemas.chekout import CheckoutRequest, CheckoutResponse

router = APIRouter()

