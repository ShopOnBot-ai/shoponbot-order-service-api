import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import api_router
from app.core.config import settings
from app.core.logging import logger
from app.messaging.producer import kafka_producer_client
from app.utils.telemetry import setup_telemetry
from app.workers.outbox_processor import processOutboxEvents


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Start up
    await kafka_producer_client.start()
    logger.info("Kafka producer client setup completed")
    yield
    # shut down
    await kafka_producer_client.stop()

app = FastAPI(
    title="ShopOnBot Order Service", 
    version="1.0.0",
    lifespan=lifespan
)

setup_telemetry(service_name="order-service", app=app)

@app.middleware("http")
async def dynamic_root_path_middleware(request: Request, call_next):
    if request.url.path.startswith("/admin"):
        request.scope["root_path"] = "/api/v1/admin/orders"
    else:
        request.scope["root_path"] = "/api/v1/orders"
        
    response = await call_next(request)
    return response

app.include_router(api_router, prefix="")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_url,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "Order service is healthy"}


@app.get("/boom", include_in_schema=False)
async def boom():
    logger.error("order-service about to fail")
    raise RuntimeError("test crash in order-service")