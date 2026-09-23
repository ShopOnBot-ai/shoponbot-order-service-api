import enum
from decimal import Decimal

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Order


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentMode(str, enum.Enum):
    CASH = "cash"
    ONLINE = "online"
    UPI = "upi"
    CARD = "card"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    payment_status: Mapped[PaymentStatus | None] = mapped_column(
        SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    payment_gateway: Mapped[str] = mapped_column(String(50), default="razorpay")
    payment_mode: Mapped[PaymentMode | None] = mapped_column(
        SQLEnum(PaymentMode), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(10), default="INR")

    order: Mapped["Order"] = relationship(back_populates="payment")
