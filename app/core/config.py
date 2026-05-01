"""Настройки приложения и производные URL для подключений."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Централизованные настройки, загружаемые из окружения и `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Habit Tracker Bot"
    environment: str = "development"
    log_level: str = "INFO"

    bot_token: str
    feedback_contact_username: str | None = None

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "habit_tracker"
    postgres_user: str = "habit_user"
    postgres_password: str = "habit_password"
    database_echo: bool = False

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_enabled: bool = True

    celery_broker_db: int = 1
    celery_result_db: int = 2

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def database_url(self) -> str:
        """Асинхронный URL SQLAlchemy для работающего приложения."""

        # This URL includes a password because SQLAlchemy needs it to connect.
        # Do not log or expose the rendered value.
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

    @property
    def alembic_database_url(self) -> str:
        """URL для Alembic-миграций, совместимый с синхронным драйвером."""

        # This URL includes a password because Alembic needs it to connect.
        # Do not log or expose the rendered value.
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

    @property
    def redis_url(self) -> str:
        """База Redis по умолчанию, которую использует само приложение."""

        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_broker_url(self) -> str:
        """Отдельная база Redis, используемая как брокер Celery."""

        return f"redis://{self.redis_host}:{self.redis_port}/{self.celery_broker_db}"

    @property
    def celery_result_backend(self) -> str:
        """Отдельная база Redis для результатов задач Celery."""

        return f"redis://{self.redis_host}:{self.redis_port}/{self.celery_result_db}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
