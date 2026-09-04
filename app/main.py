from fastapi import FastAPI

app = FastAPI(
    root_path="/api/v1/orders"
)


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "Order service is healthy"}


@app.get("/")
def get_orders():
    return {"message": "Orders"}