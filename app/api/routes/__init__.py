"""Экспорт маршрутов для сборки API-приложения."""

from app.api.routes.health import router as health_router

__all__ = ["health_router"]
