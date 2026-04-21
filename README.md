![HabbitTrackerBot banner](./app/bot/assets/readme_banner.png)

# HabbitTrackerBot

Telegram-бот для системного ведения привычек: с гибкими расписаниями, напоминаниями, целями, историей, прогрессом и административными инструментами. Проект собран как аккуратное многослойное приложение на `aiogram`, `FastAPI`, `SQLAlchemy`, `PostgreSQL`, `Redis` и `Celery`.

## Возможности

- Создание привычек с разными сценариями расписания: каждый день, через день, по выбранным дням недели
- Отметка выполнения на текущий день и работа с экраном "Сегодня"
- Цели по количеству выполнений и по длине серии
- История привычки, текущая и лучшая серии, прогресс за последние 7, 14 и 30 дней
- Напоминания и автоматические сводки в локальном времени пользователя
- Пауза и мягкое удаление привычек с возможностью восстановления
- Обратная связь от пользователей
- Админ-панель: поиск пользователей, блокировка, выдача прав, ответы на обращения, action log, рассылка

## Стек

- Python 3.10
- aiogram 3
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Redis
- Celery
- pytest + pytest-asyncio
- Docker Compose

## Архитектура

Проект собран по простой прикладной схеме: `handlers -> services -> repositories`.

- `handlers` принимают команды и callback-и Telegram, валидируют пользовательский сценарий и передают управление дальше
- `services` содержат бизнес-логику: привычки, цели, прогресс, напоминания, админские действия, feedback и рассылка
- `repositories` изолируют работу с базой данных и не смешивают SQL-доступ с логикой сценариев
- `workers` выполняют фоновые задачи для напоминаний и сводок
- `api` держит служебный HTTP-слой, в том числе `GET /health`

Ключевые директории:

```text
app/
  api/           FastAPI-приложение и healthcheck
  bot/           Telegram-бот: handlers, keyboards, middlewares
  core/          конфигурация, подключение к БД, Redis, логирование
  models/        SQLAlchemy-модели
  repositories/  слой доступа к данным
  services/      бизнес-логика
  workers/       Celery worker и периодические задачи
migrations/      Alembic-миграции
tests/           тесты сервисов, handlers и middleware
```

## Запуск локально

Шаблон переменных окружения лежит в [`.env.example`](./.env.example).

### Вариант 1. Через Docker Compose

1. Скопируйте `.env.example` в `.env`
2. Заполните `BOT_TOKEN`
3. Запустите проект:

```bash
docker compose up --build
```

Будут подняты `postgres`, `redis`, `migrator`, `api`, `bot`, `worker` и `beat`.

После запуска:

- API healthcheck доступен по `http://localhost:8000/health`
- бот запускается в polling-режиме
- Celery worker и beat обрабатывают напоминания и сводки

### Вариант 2. Без Docker

Подготовка окружения в PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

В `.env` нужно как минимум:

- указать `BOT_TOKEN`
- заменить `POSTGRES_HOST=postgres` на `POSTGRES_HOST=localhost`
- заменить `REDIS_HOST=redis` на `REDIS_HOST=localhost`

Поднять инфраструктуру можно отдельно:

```bash
docker compose up -d postgres redis
```

Применить миграции:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Запустить API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Запустить бота:

```powershell
.\.venv\Scripts\python.exe -m app.bot.main
```

Запустить Celery worker:

```powershell
.\.venv\Scripts\celery.exe -A app.workers.celery_app:celery_app worker --loglevel=INFO
```

Запустить Celery beat:

```powershell
.\.venv\Scripts\celery.exe -A app.workers.celery_app:celery_app beat --loglevel=INFO
```

Для упрощённой локальной разработки можно отключить Redis и Celery:

```env
REDIS_ENABLED=false
```

В этом режиме бот сам запускает внутренний цикл проверки напоминаний и сводок, поэтому достаточно PostgreSQL, миграций и процесса `.\.venv\Scripts\python.exe -m app.bot.main`.

## Тесты

Запуск тестов:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Тесты лежат в каталоге [`tests`](./tests) и покрывают сервисы, обработчики и middleware.

## Первый администратор

Первый администратор назначается напрямую через базу данных. Перед этим пользователь должен хотя бы один раз открыть бота через `/start`, чтобы появилась запись в таблице `users`.

SQL:

```sql
UPDATE users
SET is_admin = true
WHERE telegram_id = 123456789;
```

Пример для Docker Compose:

```bash
docker compose exec postgres psql -U habit_user -d habit_tracker -c "UPDATE users SET is_admin = true WHERE telegram_id = 123456789;"
```

После этого у пользователя станет доступен раздел администрирования.

## Статус проекта

`HabbitTrackerBot` — зрелый pet-project с уже собранным базовым продуктовым контуром: пользовательский сценарий, фоновые задачи, административный слой, миграции и тесты. Репозиторий подходит как для дальнейшего развития функционала, так и как showcase проекта с внятной архитектурой и рабочей инфраструктурой.
