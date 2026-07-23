# Pet Medication Tracker

> Мобильно-дружественное веб-приложение для отслеживания приёма лекарств у домашних животных

---

## 🎯 Описание проекта

Помогает владельцам животных не пропускать приём препаратов. Владелец регистрирует питомца, добавляет курс лечения с частотой приёма, датами и временем напоминаний — система автоматически генерирует расписание доз на весь курс. Каждую дозу можно отметить как «принято», «пропущено» или «не принято» прямо из дневного календаря; просроченные дозы планировщик помечает автоматически. Курс лечения можно в любой момент отменить (дозы после дня отмены стираются из календаря) или удалить (уже отмеченные дозы остаются в календаре, сам курс исчезает из списка препаратов). По каждому завершённому курсу — отменённому или закончившемуся по дате — доступна сводная статистика приёма.

Целевая аудитория — владельцы домашних животных, которым нужно вести регулярный курс лечения (антибиотики, хронические препараты, витамины) без риска забыть дозу.

## 🛠 Технологический стек

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Язык | Python | ^3.12 |
| Веб-фреймворк | FastAPI | ^0.104 |
| ORM | SQLAlchemy (async) | ^2.0 |
| Миграции | Alembic | ^1.12 |
| Валидация | Pydantic / Pydantic Settings | ^2.5 |
| Аутентификация | JWT (python-jose) + bcrypt | — |
| База данных | PostgreSQL | 15 |
| Кэш | Redis | 7 |
| Планировщик задач | APScheduler | ^3.10 |
| Фронтенд | TailwindCSS + Vanilla JS (SPA) | — |
| Зависимости | Poetry | — |
| Тестирование | Pytest + pytest-asyncio + unittest | ^7.4 |
| Линтер | Ruff | latest |
| Типизация | Mypy (strict) | latest |
| CI/CD | — (пока не настроен) | — |
| Infra | Docker Compose | — |

---

## 🚀 Быстрый старт

### Установка (Docker)

```bash
# Клонирование
git clone https://github.com/AlenaSygrysheva/pets_medication_tracker.git
cd pets_medication_tracker

# Конфигурация
cp .env.example .env
# Обязательно смените SECRET_KEY в .env

# Запуск (поднимет app + PostgreSQL + Redis, применит миграции)
docker compose up -d
```

Сервисы после запуска:

| URL | Описание |
|---|---|
| http://localhost:8000 | Веб-интерфейс (SPA) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health | Health check |

### Локальная разработка (без контейнера с приложением)

Требования: Python 3.12+, [Poetry](https://python-poetry.org/docs/#installation) 1.8+, PostgreSQL 15 и Redis 7 (или только их поднять через Docker).

```bash
# Установка зависимостей
poetry install

# Поднять только БД и Redis
docker compose up -d db redis

# Применить миграции
poetry run alembic upgrade head

# Запустить сервер с автоперезагрузкой
poetry run uvicorn app.main:app --reload
```

### Конфигурация

Файл `.env` (скопировать из `.env.example`):

```env
# Обязательные
SECRET_KEY=your-super-secret-key-change-in-production
DATABASE_URL=postgresql+asyncpg://pet_app:pass@db:5432/pet_medication_db
POSTGRES_USER=pet_app
POSTGRES_PASSWORD=pass
POSTGRES_DB=pet_medication_db

# Опциональные
APP_NAME=PetMedicationTracker
APP_VERSION=1.0.0
DEBUG=false
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
REDIS_URL=redis://redis:6379/0
ALLOWED_ORIGINS=http://localhost:8000
```

---

## 📂 Структура проекта

```
pets_medication_tracker/
├── app/
│   ├── api/
│   │   ├── dependencies.py      # get_current_user
│   │   └── v1/                  # auth, pets, medications, calendar, doses
│   ├── core/
│   │   ├── cache.py             # Redis helpers
│   │   ├── exceptions.py        # HTTP-исключения (NotFound/Forbidden/Conflict/...)
│   │   └── security.py          # JWT + bcrypt
│   ├── models/                  # SQLAlchemy ORM-модели
│   ├── repositories/            # DAO — прямой доступ к БД
│   ├── schemas/                 # Pydantic-схемы запросов/ответов
│   ├── services/                # Бизнес-логика (auth, pet, medication, calendar, scheduler)
│   ├── static/                  # SPA: index.html (HTML + TailwindCSS + Vanilla JS)
│   ├── config.py                # Pydantic Settings
│   ├── database.py
│   └── main.py                  # FastAPI app, роуты, lifespan
├── migrations/                  # Alembic-миграции (raw SQL через op.execute)
├── tests/
│   ├── unit/                    # unittest + AsyncMock, без БД
│   ├── conftest.py              # SQLite in-memory, мок Redis
│   └── test_*.py                # Интеграционные тесты (httpx + ASGITransport)
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh                # Миграции + запуск uvicorn
├── pyproject.toml               # Poetry + конфиги ruff/mypy/pytest
└── .env.example
```

Архитектура — 4 слоя: **models → repositories → services → API routers**. Каждый слой знает только о соседнем снизу.

---

## 🧪 Тестирование

```bash
# Все тесты
poetry run pytest tests/ -v

# Только юнит-тесты (без БД)
poetry run pytest tests/unit/ -v

# Только интеграционные тесты
poetry run pytest tests/test_*.py -v

# С отчётом покрытия
poetry run pytest tests/ --cov=app --cov-report=html
# Отчёт: htmlcov/index.html
```

Тесты не требуют запущенного PostgreSQL или Redis — используется SQLite in-memory и моки. Текущее покрытие: **139 тестов** (102 unit + 37 интеграционных), все проходят.

---

## 📊 Мониторинг и логирование

- Логи: структурированный текстовый формат (`%(asctime)s [%(levelname)s] %(name)s: %(message)s`) в stdout; middleware логирует каждый запрос (метод, путь, статус, длительность)
- Health check: `GET /health` — статус приложения и версия
- Метрики (Prometheus) и трейсинг (OpenTelemetry) пока не подключены

---

## 📚 API документация

После запуска доступны Swagger UI (`/docs`) и ReDoc (`/redoc`). Все эндпоинты требуют JWT, кроме `/auth/register`, `/auth/login`, `/auth/refresh` и `/health`.

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
| `POST` | `/api/v1/pets/{id}/avatar` | Загрузить фото |
| `DELETE` | `/api/v1/pets/{id}` | Удалить питомца |

### Препараты

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/api/v1/medications/pet/{pet_id}` | Курсы лечения питомца (без удалённых) |
| `GET` | `/api/v1/medications/pet/{pet_id}/stats` | Сводка по завершённым курсам (отменённым или закончившимся по дате) |
| `POST` | `/api/v1/medications` | Создать курс (генерирует дозы по `reminder_times`) |
| `GET` | `/api/v1/medications/{id}` | Карточка курса |
| `PATCH` | `/api/v1/medications/{id}` | Редактировать курс |
| `POST` | `/api/v1/medications/{id}/cancel?as_of_date=` | Отменить курс на указанную дату (по умолчанию — сегодня): дозы после неё стираются из календаря, дозы до и в этот день помечаются `cancelled` |
| `DELETE` | `/api/v1/medications/{id}` | Мягкое удаление курса: пропадает из списка препаратов, но уже отмеченные дозы (`taken`/`skipped`/`missed`) остаются в календаре |

### Календарь и дозы

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/api/v1/calendar/pet/{pet_id}/{date}` | Расписание дня (YYYY-MM-DD) |
| `PATCH` | `/api/v1/doses/{id}` | Отметить дозу (taken / skipped / missed) |

### Статусы дозы

| Статус | Описание |
|---|---|
| `pending` | Запланирована, ещё не принята |
| `taken` | Принята |
| `skipped` | Пропущена вручную |
| `missed` | Просрочена (проставлена планировщиком) или отмечена как «не принято» |
| `cancelled` | Курс отменён — доза на день отмены или раньше него, оставлена для истории |

---

## 📞 Контакты и поддержка

- 📧 Email: alena_sygrysheva@mail.ru
- 💬 Telegram: [@Blue_Koshara](https://t.me/Blue_Koshara)
- 🐛 Баги: [GitHub Issues](https://github.com/AlenaSygrysheva/pets_medication_tracker/issues)

---

## 🔄 Changelog

### [Unreleased]
- Мягкое удаление курса лечения (`Medication.is_deleted`, миграция `005`) — курс пропадает из вкладки «Препараты», но уже отмеченные дозы остаются видны в календаре; раньше `DELETE` каскадно стирал курс и все его дозы без возможности восстановить историю
- Реализована отмена курса из карточки дозы («🛑 Отменить курс» в модалке рядом с «Принято» / «Пропустить» / «Не принято»): дозы после выбранного дня стираются из календаря, дозы до и в этот день помечаются статусом `cancelled` и остаются в истории
- Новая вкладка «Статистика приёма» и эндпоинт `GET /medications/pet/{pet_id}/stats` — сводка (принято/пропущено/не принято) по каждому завершённому курсу, отменённому или закончившемуся по дате
- Настраиваемое время напоминаний (`reminder_times`) — раньше время доз генерировалось всегда с 8:00 с равным интервалом, теперь пользователь задаёт время каждой дозы сам
- Понятное сообщение об ошибке при неверном email/пароле на экране входа (раньше форма молча ничего не показывала)

### [1.0.0] — 2026-07-16
- Первая версия: JWT-аутентификация, питомцы, курсы лечения, автогенерация расписания доз, дневной календарь, фоновый планировщик просроченных доз, Redis-кэш
