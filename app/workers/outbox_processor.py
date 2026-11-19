import asyncio
import signal

from sqlalchemy import select

from app.core.logging import logger
from app.db.base import EventOutbox
from app.db.database import AsyncSessionLocal
from app.messaging.producer import kafka_producer_client
from app.models.event_outbox import EventStatus


async def processOutboxEvents(stop_event: asyncio.Event):
    """
    Infinite background loop that polls the event_outbox table
    and process pending events to Apache Kafka.
    """
    logger.info("Starting Transactional Outbox Processing Background Worker Daemon...")

    await asyncio.sleep(2)

    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as db, db.begin():
                db.expire_all()
                query = (
                    select(EventOutbox)
                    .where(EventOutbox.publish_status == EventStatus.PENDING)
                    .order_by(EventOutbox.created_at.asc())
                    .limit(10)
                    .with_for_update(skip_locked=True)
                )
                results = await db.execute(query)
                pending_events = results.scalars().all()

                if pending_events:
                    logger.info(
                        "Found %s pending transaction outbox events to process.",
                        len(pending_events),
                    )

                    for event in pending_events:
                        target_topic = f"{event.aggregate_type.lower()}-events"
                        logger.info("target topic: %s", target_topic)
                        await kafka_producer_client.publish_event(
                            topic=target_topic,
                            key= str(event.aggregate_id),
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
                "Outbox processing failed: %s",
                str(e),
                exc_info=True,
            )

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass



async def main():
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await kafka_producer_client.start()
    logger.info("Kafka producer client setup completed in standalone worker")
    try:
        await processOutboxEvents(stop_event)
    finally:
        logger.info("Shutting down Kafka producer gracefully...")
        await kafka_producer_client.stop()


if __name__ == "__main__":
    asyncio.run(main())

