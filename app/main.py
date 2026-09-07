from fastapi import FastAPI

from app.api.v1.routers import api_router

app = FastAPI(
    root_path="/api/v1/orders"
)

app.include_router(api_router, prefix="")


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "Order service is healthy"}


@app.get("/")
def get_orders():
    return {"message": "Orders"}