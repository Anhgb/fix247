"""
Fix 24/7 FastAPI Application Entry Point.
NFR-10: structured logging, X-Trace-ID header on every request.
"""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import generate_trace_id, setup_logging, get_logger
from app.core.redis import close_redis, get_redis
from app.routers import auth, categories, diagnosis
from app.services.storage import MEDIA_DIR

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("fix247_api_starting", env=settings.app_env)
    # Warm up Redis connection
    redis = await get_redis()
    await redis.ping()
    logger.info("redis_connected")
    yield
    # Shutdown
    await close_redis()
    logger.info("fix247_api_stopped")


app = FastAPI(
    title="Fix 24/7 API",
    description="Nền tảng chẩn đoán AI và kết nối thợ sửa chữa",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Trace ID middleware ───────────────────────────────────────────────────────
@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """NFR-10: inject X-Trace-ID on every request/response."""
    trace_id = request.headers.get("X-Trace-ID") or generate_trace_id()
    import structlog
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id, path=str(request.url.path))
    response: Response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(diagnosis.router, prefix=API_PREFIX)
app.include_router(categories.router, prefix=API_PREFIX)

# Mount local media storage
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get(f"{API_PREFIX}/health", tags=["system"])
async def health_check():
    """NFR-10: Health check endpoint."""
    redis = await get_redis()
    redis_ok = await redis.ping()
    return {
        "status": "ok",
        "env": settings.app_env,
        "services": {
            "redis": "ok" if redis_ok else "error",
            "database": "ok",  # TODO: add DB ping in P1
        },
    }


@app.get("/", include_in_schema=False)
async def root():
    return {"name": "Fix 24/7 API", "version": "0.1.0", "docs": "/api/docs"}
