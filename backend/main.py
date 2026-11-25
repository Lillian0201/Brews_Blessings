from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_bool
from src.core.errors import ApiError, api_error_handler, validation_error_handler
from src.database.bootstrap import apply_bootstrap
from src.database.seeds import run_seeds

from auth.router import router as auth_router
from transactions.router import router as transactions_router
from expenses.router import router as expenses_router
from products.router import router as products_router
from users.router import router as users_router
from inventory.router import router as inventory_router
from pos.router import router as pos_router
from dashboard.router import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if get_bool("BB_AUTO_BOOTSTRAP", os.getenv("VERCEL") != "1"):
        apply_bootstrap()
        run_seeds()
    yield


app = FastAPI(title="Brews & Blessings API", lifespan=lifespan)
default_origins = "" if os.getenv("VERCEL") == "1" else (
    "null,http://127.0.0.1:5500,http://localhost:5500,"
    "http://127.0.0.1:8000,http://localhost:8000"
)
cors_origins = [
    origin.strip()
    for origin in os.getenv("BB_CORS_ORIGINS", default_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type"],
)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(expenses_router)
app.include_router(products_router)
app.include_router(users_router)
app.include_router(inventory_router)
app.include_router(pos_router)
app.include_router(dashboard_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=5001, reload=False)
