from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.redis import get_redis


router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck() -> JSONResponse:
    database_status = "ok"
    redis_status = "ok"
    status_code = 200

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"
        status_code = 503

    if settings.redis_enabled:
        try:
            await get_redis().ping()
        except Exception:
            redis_status = "error"
            status_code = 503
    else:
        redis_status = "disabled"

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if status_code == 200 else "degraded",
            "database": database_status,
            "redis": redis_status,
        },
    )
