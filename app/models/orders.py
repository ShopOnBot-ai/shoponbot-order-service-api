import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.schemas.order import OrderStatus, PaymentStatus

if TYPE_CHECKING:
    from app.models.order_item import OrderItem


class CancelledBy(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    order_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    tax: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    shipping_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    discount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    total_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )

    shipping_address: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    cancelled_by: Mapped[str | None] = mapped_column(
        Enum(CancelledBy),
        nullable=True,
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
