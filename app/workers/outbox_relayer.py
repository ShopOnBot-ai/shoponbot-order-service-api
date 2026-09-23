import asyncio

from sqlalchemy import select

from app.core.logging import logger
from app.db.base import EventOutbox
from app.db.database import AsyncSessionLocal
from app.messaging.producer import kafka_producer_client
from app.models.event_outbox import EventStatus


async def publish_outbox_relayer():
    """
    Infinite background loop that polls the event_outbox table
    and relays pending events to Apache Kafka.
    """
    logger.info("Starting Transactional Outbox Relayer Background Worker Daemon... ⚙️")

    await asyncio.sleep(2)

    while True:
        try:
            async with AsyncSessionLocal() as db, db.begin():
                query = (
                    select(EventOutbox)
                    .where(EventOutbox.publish_status == EventStatus.PENDING)
                    .order_by(EventOutbox.created_at.desc())
                    .limit(10)
                )
                results = await db.execute(query)
                pending_events = results.scalars().all()

                if not pending_events:
                    break
                logger.info(
                    "Found %s pending transaction outbox events to relay.",
                    len(pending_events),
                )

                for event in pending_events:
                    target_topic = f"{event.aggregate_type.lower()}-events"

                    await kafka_producer_client.publish_event(
                        topic=target_topic,
                        payload={
                            "event_id": event.id,
                            "event_type": event.event_type,
                            "aggregate_id": event.aggregate_id,
                            "payload": event.payload,
                        },
                    )

                    event.publish_status = EventStatus.PROCESSED

                await db.flush()
                logger.info(
                    "Successfully processed and committed %s outbox events.",
                    len(pending_events),
                )

        except Exception as e:
            logger.error(
                "Outbox Relayer processing cycle encountered a failure: %s",
                str(e),
                exc_info=True,
            )

    await asyncio.sleep(2)
