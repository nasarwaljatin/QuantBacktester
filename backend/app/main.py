# backend/app/main.py
"""FastAPI application entry point with CORS, routers, and database initialization."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import health, data, backtest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — creates database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="QuantBacktester API",
    description="Algorithmic trading strategy backtesting platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(data.router)
app.include_router(backtest.router)
