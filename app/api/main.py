from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health_router
from app.core.config import settings
from app.core.database import check_database_connection, dispose_engine
from app.core.logging import configure_logging
from app.core.redis import close_redis, get_redis


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    await check_database_connection()
    if settings.redis_enabled:
        await get_redis().ping()
    yield
    if settings.redis_enabled:
        await close_redis()
    await dispose_engine()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
