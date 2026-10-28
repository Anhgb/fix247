"""
Fix 24/7 FastAPI Application Entry Point.
NFR-10: structured logging, X-Trace-ID header on every request.
FR-PAY-04, BR-08: Scheduled auto-confirm job every 10 minutes.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import generate_trace_id, get_logger, setup_logging
from app.core.redis import close_redis, get_redis
from app.routers import (
    admin,
    assets,
    auth,
    categories,
    diagnosis,
    orders,
    payments,
    qr,
    reviews,
    technician,
    warranty,
    ws_orders,
)
from app.services.auto_confirm import auto_confirm_expired_orders
from app.services.maintenance_reminders import check_and_send_maintenance_reminders
from app.services.technician_service import auto_offline_inactive_technicians
from app.services.storage import MEDIA_DIR

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)


async def _background_maintenance_loop():
    """
    Background tasks:
    1. Auto-offline inactive technicians without location ping > 5 mins (FR-TECH-03, A-14)
    2. Auto-confirm orders awaiting confirmation > 24h (FR-PAY-04, BR-08, AT-05)
    3. Maintenance reminders delivery for vehicles & appliances (FR-HEALTH-03)
    """
    counter = 0
    while True:
        try:
            await asyncio.sleep(60)  # check heartbeat every 60s
            counter += 1
            async with AsyncSessionLocal() as session:
                # Every 60s: auto-offline inactive technicians (FR-TECH-03)
                offline_count = await auto_offline_inactive_technicians(session)
                if offline_count > 0:
                    logger.info("auto_offlined_inactive_technicians", count=offline_count)

                # Every 10 min (counter % 10 == 0): auto-confirm orders & check reminders
                if counter % 10 == 0:
                    confirmed = await auto_confirm_expired_orders(session, cutoff_hours=24)
                    if confirmed:
                        logger.info("auto_confirmed_orders", count=len(confirmed), ids=confirmed)

                    reminders_sent = await check_and_send_maintenance_reminders(session)
                    if reminders_sent > 0:
                        logger.info("maintenance_reminders_sent", count=reminders_sent)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("background_loop_error", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("fix247_api_starting", env=settings.app_env)
    # Warm up Redis connection
    redis = await get_redis()
    await redis.ping()
    logger.info("redis_connected")

    # Start background worker loop
    loop_task = asyncio.create_task(_background_maintenance_loop())

    yield

    # Shutdown
    loop_task.cancel()
    await close_redis()
    logger.info("fix247_api_stopped")


app = FastAPI(
    title="Fix 24/7 API",
    description="Nền tảng chẩn đoán AI và kết nối thợ sửa chữa",
    version="0.5.0",
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
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(qr.router, prefix=API_PREFIX)
app.include_router(assets.router, prefix=API_PREFIX)
app.include_router(diagnosis.router, prefix=API_PREFIX)
app.include_router(categories.router, prefix=API_PREFIX)
app.include_router(orders.router, prefix=API_PREFIX)
app.include_router(technician.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)
app.include_router(reviews.router, prefix=API_PREFIX)
app.include_router(warranty.router, prefix=API_PREFIX)
app.include_router(ws_orders.router, prefix=API_PREFIX)

# Also mount ws directly at /orders/{order_id}/stream and qr directly at /qr/{code} for spec compliance
app.include_router(ws_orders.router)
app.include_router(qr.router)

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
            "database": "ok",
        },
    }


@app.get("/", include_in_schema=False)
async def root():
    return {"name": "Fix 24/7 API", "version": "0.4.0", "docs": "/api/docs"}
