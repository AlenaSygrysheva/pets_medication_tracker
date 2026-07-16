# Pet Medication Tracker

Мобильно-дружественное веб-приложение для отслеживания расписания приёма препаратов у домашних животных.

Владелец регистрирует питомца, добавляет курс лечения с частотой приёма и датами — система автоматически генерирует расписание доз. Каждую дозу можно отметить как «принято» или «пропущено». Просроченные дозы помечаются планировщиком автоматически. Дневной календарь кэшируется в Redis.

## Возможности

- Регистрация и авторизация через JWT (access + refresh токены)
- Управление несколькими питомцами с фото
- Курс лечения → автогенерация расписания доз с учётом частоты приёма
- Дневной календарь с кнопками «Принял» / «Пропустил»
- Отмена курса: все незакрытые дозы переходят в статус `cancelled`
- Фоновый планировщик помечает просроченные дозы как `missed`
- Redis-кэш дневного календаря (TTL 5 мин) с инвалидацией при изменениях
- Мобильный UI (TailwindCSS, SPA на Vanilla JS)
- Swagger UI и ReDoc из коробки

## Стек

| Слой | Технология |
|---|---|
| API | FastAPI 0.104 |
| ORM | SQLAlchemy 2.0 async |
| Миграции | Alembic |
| Аутентификация | JWT (python-jose) + bcrypt |
| База данных | PostgreSQL 15 |
| Кэш | Redis 7 |
| Планировщик | APScheduler (AsyncIOScheduler) |
| Infra | Docker Compose |
| Зависимости | Poetry |
| Линтер | Ruff |
| Типизация | Mypy (strict) |
| Тесты | pytest + unittest |

## Быстрый старт (Docker)

```bash
git clone <repo-url>
cd pets_medication_tracker

cp .env.example .env
# Обязательно смените SECRET_KEY в .env

docker compose up -d
```

Сервисы:

| URL | Описание |
|---|---|
| http://localhost:8000 | Веб-интерфейс |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health | Health check |

## Локальная разработка

### Требования

- Python 3.12+
- [Poetry](https://python-poetry.org/docs/#installation) 1.8+
- PostgreSQL 15 и Redis 7 (или запустить только инфраструктуру через Docker)

### Установка

```bash
# Установить зависимости
poetry install

# Запустить только БД и Redis через Docker
docker compose up -d db redis

# Применить миграции
poetry run alembic upgrade head

# Запустить сервер
poetry run uvicorn app.main:app --reload
```

### Зависимости разработки

```bash
# Запустить тесты
poetry run pytest tests/ -v

# Тесты с покрытием
poetry run pytest tests/ --cov=app --cov-report=term-missing

# Линтер
poetry run ruff check app/ tests/

# Автоисправление
poetry run ruff check app/ tests/ --fix

# Проверка типов
poetry run mypy app/
```

## Переменные окружения

Файл `.env` (скопировать из `.env.example`):

| Переменная | Описание | Пример |
|---|---|---|
| `SECRET_KEY` | Секрет для JWT подписи | `openssl rand -hex 32` |
| `DATABASE_URL` | URL подключения к PostgreSQL | `postgresql+asyncpg://user:pass@db:5432/dbname` |
| `POSTGRES_USER` | Пользователь PostgreSQL | `pet_app` |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | — |
| `POSTGRES_DB` | Имя базы данных | `pet_medication_db` |
| `REDIS_URL` | URL подключения к Redis | `redis://redis:6379/0` |
| `ALLOWED_ORIGINS` | CORS origins через запятую | `http://localhost:3000` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | TTL access-токена | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | TTL refresh-токена | `7` |
| `DEBUG` | Логирование SQL | `false` |

## API

Все эндпоинты защищены JWT, кроме `/auth/register`, `/auth/login`, `/health`.

### Аутентификация

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Регистрация, возвращает токены |
| `POST` | `/api/v1/auth/login` | Вход, возвращает токены |
| `POST` | `/api/v1/auth/refresh` | Обновление access-токена |
| `GET` | `/api/v1/auth/me` | Данные текущего пользователя |

### Питомцы

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/api/v1/pets` | Список питомцев пользователя |
| `POST` | `/api/v1/pets` | Добавить питомца |
| `GET` | `/api/v1/pets/{id}` | Карточка питомца |
| `PATCH` | `/api/v1/pets/{id}` | Редактировать питомца |
| `DELETE` | `/api/v1/pets/{id}` | Удалить питомца |
| `POST` | `/api/v1/pets/{id}/avatar` | Загрузить фото |

### Препараты

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/api/v1/medications/pet/{pet_id}` | Курсы лечения питомца |
| `POST` | `/api/v1/medications` | Создать курс (генерирует дозы) |
| `GET` | `/api/v1/medications/{id}` | Карточка курса |
| `PATCH` | `/api/v1/medications/{id}` | Редактировать курс |
| `POST` | `/api/v1/medications/{id}/cancel` | Отменить курс |
| `DELETE` | `/api/v1/medications/{id}` | Удалить курс |

### Календарь и дозы

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/api/v1/calendar/pet/{pet_id}/{date}` | Расписание дня (YYYY-MM-DD) |
| `PATCH` | `/api/v1/doses/{id}` | Отметить дозу (taken / skipped) |

### Статусы дозы

| Статус | Описание |
|---|---|
| `pending` | Запланирована, ещё не принята |
| `taken` | Принята |
| `skipped` | Пропущена вручную |
| `missed` | Просрочена (проставлена планировщиком) |
| `cancelled` | Отменена вместе с курсом |

## Структура проекта

```
pets_medication_tracker/
├── app/
│   ├── api/
│   │   ├── dependencies.py      # get_current_user
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── calendar.py
│   │       ├── doses.py
│   │       ├── medications.py
│   │       └── pets.py
│   ├── core/
│   │   ├── cache.py             # Redis helpers
│   │   ├── exceptions.py        # HTTP-исключения
│   │   └── security.py          # JWT + bcrypt
│   ├── models/                  # SQLAlchemy ORM-модели
│   ├── repositories/            # DAO (Data Access Objects)
│   ├── schemas/                 # Pydantic схемы запросов/ответов
│   ├── services/                # Бизнес-логика
│   │   ├── auth_service.py
│   │   ├── calendar_service.py
│   │   ├── medication_service.py
│   │   ├── pet_service.py
│   │   └── scheduler_service.py
│   ├── static/                  # SPA (HTML + JS + CSS)
│   ├── config.py
│   ├── database.py
│   └── main.py
├── migrations/                  # Alembic миграции (raw SQL)
├── tests/
│   ├── unit/                    # unittest + AsyncMock, без БД
│   │   ├── test_auth_service.py
│   │   ├── test_calendar_service.py
│   │   ├── test_medication_service.py
│   │   ├── test_pet_service.py
│   │   ├── test_schemas.py
│   │   └── test_security.py
│   ├── conftest.py              # SQLite in-memory, мок Redis
│   ├── test_auth.py             # Интеграционные тесты
│   ├── test_calendar.py
│   ├── test_doses.py
│   ├── test_medications.py
│   └── test_pets.py
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh                # Миграции + запуск uvicorn
├── pyproject.toml               # Poetry + конфиги ruff/mypy/pytest
└── .env.example
```

## Тесты

Тесты не требуют запущенного PostgreSQL или Redis — используется SQLite in-memory и моки.

```bash
# Все тесты
poetry run pytest tests/ -v

# Только юнит-тесты
poetry run pytest tests/unit/ -v

# Только интеграционные тесты
poetry run pytest tests/test_*.py -v

# С отчётом покрытия
poetry run pytest tests/ --cov=app --cov-report=html
# Отчёт: htmlcov/index.html
```

Покрытие: **126 тестов** (96 unit + 30 integration), все проходят.

## Качество кода

Проект настроен под **mypy strict** и **ruff** с нулём ошибок:

```bash
poetry run ruff check app/ tests/   # 0 ошибок
poetry run mypy app/                # 0 ошибок в 37 файлах
```

Конфигурации находятся в `pyproject.toml` в секциях `[tool.ruff]` и `[tool.mypy]`.

## Миграции

```bash
# Применить все миграции
poetry run alembic upgrade head

# Откатить одну миграцию
poetry run alembic downgrade -1

# Создать новую миграцию
poetry run alembic revision -m "описание изменения"

# Текущая ревизия
poetry run alembic current
```

Миграции написаны на raw SQL (`op.execute(sa.text(...))`) для совместимости с PostgreSQL enum-типами.
