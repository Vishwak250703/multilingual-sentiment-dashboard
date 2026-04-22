from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.redis import get_redis, close_redis
from app.api.routes import auth, ingest, dashboard, reviews, chat, alerts, insights, admin
from app.api import websocket as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_redis()
    print("Redis connected")
    yield
    # Shutdown
    await close_redis()
    print("Redis disconnected")


app = FastAPI(
    title="Multilingual Sentiment Dashboard API",
    description="Production-grade multilingual sentiment analysis platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes ────────────────────────────────────────────────
prefix = settings.API_V1_PREFIX

app.include_router(auth.router,       prefix=f"{prefix}/auth",      tags=["Auth"])
app.include_router(ingest.router,     prefix=f"{prefix}/ingest",    tags=["Ingestion"])
app.include_router(dashboard.router,  prefix=f"{prefix}/dashboard", tags=["Dashboard"])
app.include_router(reviews.router,    prefix=f"{prefix}/reviews",   tags=["Reviews"])
app.include_router(chat.router,       prefix=f"{prefix}/chat",      tags=["Chat Q&A"])
app.include_router(alerts.router,     prefix=f"{prefix}/alerts",    tags=["Alerts"])
app.include_router(insights.router,   prefix=f"{prefix}/insights",  tags=["Insights"])
app.include_router(admin.router,      prefix=f"{prefix}/admin",     tags=["Admin"])

# ─── WebSocket ─────────────────────────────────────────────────
app.include_router(ws_router.router, tags=["WebSocket"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME, "version": "1.0.0"}
