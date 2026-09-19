import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class EventStatus(enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class EventOutbox(Base):
    __tablename__ = "event_outbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(String(20), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    publish_status: Mapped[str | None] = mapped_column(Enum(EventStatus), default=EventStatus.PENDING, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)