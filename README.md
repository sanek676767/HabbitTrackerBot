# Habit Tracker Bot

Telegram-бот для ведения привычек с расписанием, напоминаниями, прогрессом, целями и административной панелью. Проект построен на `aiogram`, `FastAPI`, `SQLAlchemy`, `PostgreSQL`, `Redis` и `Celery`.

## Возможности

- создание привычек с разным расписанием:
  - ежедневно
  - через N дней
  - по выбранным дням недели
- отметка выполнения привычки на текущий день
- статистика по привычке:
  - текущее и лучшее серии
  - общее число выполнений
  - прогресс за последние 7 дней
- цели по привычке:
  - по числу выполнений
  - по длине серии
- напоминания в локальном времени пользователя
- экран "Сегодня" только с актуальными привычками
- экран общего прогресса с метриками за 7 и 30 дней
- автоматические сводки:
  - ежедневная в `21:00` по локальному времени
  - еженедельная в воскресенье в `20:00` по локальному времени
- обратная связь от пользователей
- админ-панель:
  - поиск и просмотр пользователей
  - блокировка и разблокировка
  - выдача и снятие админ-прав
  - просмотр и восстановление удалённых привычек
  - ответы на обращения
  - журнал админ-действий

## Стек

- Python 3.10
- aiogram 3
- FastAPI
- SQLAlchemy 2 + Alembic
- PostgreSQL
- Redis
- Celery
- pytest

## Структура проекта

```text
app/
  api/           FastAPI-приложение и healthcheck
  bot/           Telegram-бот: handlers, callbacks, keyboards, middlewares
  core/          конфигурация, БД, Redis, логирование
  models/        SQLAlchemy-модели
  repositories/  слой доступа к данным
  services/      бизнес-логика
  workers/       Celery worker и периодические задачи
migrations/      Alembic-миграции
tests/           тесты сервисов, диспетчеров и middleware
```

## Переменные окружения

Шаблон находится в [.env.example](.env.example).

Основные переменные:

- `BOT_TOKEN` - токен Telegram-бота
- `FEEDBACK_CONTACT_USERNAME` - опциональный контакт для поддержки
- `POSTGRES_*` - параметры подключения к PostgreSQL
- `REDIS_*` - параметры Redis
- `CELERY_BROKER_DB` и `CELERY_RESULT_DB` - базы Redis для Celery
- `REDIS_ENABLED` - если `false`, бот запускает цикл напоминаний и сводок внутри процесса без Celery
- `API_HOST` и `API_PORT` - параметры FastAPI

Важно: в шаблоне `.env.example` для Docker указаны хосты `postgres` и `redis`. Если запускать приложение локально вне контейнеров, замените их на `localhost`.

## Быстрый старт через Docker Compose

1. Скопируйте `.env.example` в `.env`.
2. Заполните `BOT_TOKEN`.
3. Запустите проект:

```bash
docker compose up --build
```

Будут подняты сервисы:

- `postgres`
- `redis`
- `migrator`
- `api`
- `bot`
- `worker`
- `beat`

После запуска:

- API healthcheck доступен по `http://localhost:8000/health`
- бот начинает polling в Telegram
- Celery Beat раз в минуту проверяет напоминания и сводки

## Локальный запуск без Docker

### 1. Подготовка окружения

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

После этого:

- укажите `BOT_TOKEN`
- поменяйте `POSTGRES_HOST=localhost`
- поменяйте `REDIS_HOST=localhost`

### 2. Поднимите инфраструктуру

Проще всего оставить PostgreSQL и Redis в Docker:

```bash
docker compose up -d postgres redis
```

### 3. Примените миграции

```powershell
python -m alembic upgrade head
```

### 4. Запуск сервисов

API:

```powershell
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Бот:

```powershell
python -m app.bot.main
```

Celery worker:

```powershell
celery -A app.workers.celery_app:celery_app worker --loglevel=INFO
```

Celery beat:

```powershell
celery -A app.workers.celery_app:celery_app beat --loglevel=INFO
```

## Упрощённый локальный режим без Redis и Celery

Для разработки можно отключить Redis:

```env
REDIS_ENABLED=false
```

В этом режиме бот сам запускает внутренний цикл проверки напоминаний и сводок. Тогда достаточно:

- PostgreSQL
- миграций
- процесса `python -m app.bot.main`

API при этом продолжит работать, а `/health` будет возвращать `redis: "disabled"`.

## Тесты

```powershell
pytest -q
```

## Первый администратор

Права администратора выдаются через базу данных. Сначала пользователь должен хотя бы один раз открыть бота через `/start`, чтобы появилась запись в таблице `users`.

SQL:

```sql
UPDATE users
SET is_admin = true
WHERE telegram_id = 123456789;
```

Пример для Docker:

```bash
docker compose exec postgres psql -U habit_user -d habit_tracker -c "UPDATE users SET is_admin = true WHERE telegram_id = 123456789;"
```

После этого у пользователя появится раздел админки.

## API

Сейчас FastAPI используется как служебный HTTP-интерфейс. Доступный маршрут:

- `GET /health` - проверка состояния API, PostgreSQL и Redis

Пример ответа:

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok"
}
```

## Полезные команды

Из файла [TERMINAL_COMMANDS.txt](TERMINAL_COMMANDS.txt):

```powershell
python -m app.bot.main
python -m pytest -q
python -m alembic upgrade head
```

## Что стоит помнить

- напоминания и сводки завязаны на локальное время пользователя, которое бот определяет по введённому времени
- архивные привычки нельзя отмечать и для них нельзя включать напоминания
- удаление привычек мягкое: администратор может восстановить их из админки
- в проекте уже есть слой API, воркеры, миграции и тесты, поэтому его удобно развивать дальше без смены архитектуры
