import json

from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.core.logging import logger


class KafkaProducerMangaer:
    def __init__(self):
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Initialized connection instance on application startup."""
        if not self._producer:
            logger.info(
                "Connecting to Apache Kafka Cluster Broker at %s...",
                settings.kafka_bootstrap_servers,
            )
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            await self._producer.start()
            logger.info("Apache Kafka Producer client stream securely initialized and active!")

    async def stop(self) -> None:
        """Successfully close the connection instance on application shutdown block for db saftey."""
        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("Apache Kafka Producer connection terminated safely.")

    async def publish_event(self, topic: str, payload: dict) -> None:
        """Centralized event dispatcher block configuration parameters inputs string mappings."""
        if not self._producer:
            raise RuntimeError("Kafka Event streaming engine context missing configuration setup initialization hooks.")
        try:
            await self._producer.send_and_wait(topic, payload)
            logger.info("Successfully published transaction streaming event metadata payload to Topic: %s", topic)
        except Exception as e:
            logger.error("Failed to safely dispatch streaming parameters block to Kafka network clusters: %s", str(e))
            raise

kafka_producer_client = KafkaProducerMangaer()
