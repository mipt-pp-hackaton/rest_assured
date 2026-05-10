# Epic-2 Health Checking Scheduler — Post-Review Fixes

**Branch:** `epic-2-health-checking-scheduler` (already exists — do NOT create a new one)
**Scope:** ~30 fixes from PR review covering security (SSRF, hardcoded credentials, log injection, secrets handling), correctness (SQLModel filter bug, `datetime.utcnow` deprecation, `assert` in prod paths), runtime hygiene (signal forwarding, lifespan, retries, healthchecks), and infra hardening (Docker, compose, pyproject, gitignore).

**Review reference:** PR review of Epic-2 Health Checking Scheduler (May 2026).

**Grouping rule:** one file = one task to avoid worktree conflicts.
**Dependency rule:** `listener.py` depends on `runner.py` (uses new public methods); `main.py` depends on `runner.py` + `listener.py` (factory + lifespan).
**INFRA tasks** (Dockerfile, docker-compose, pyproject.toml, .gitignore, .dockerignore, settings.toml.example, .env, deletion of artifacts) are independent.

---

## Wave 1 — Independent (no deps)

### T1 [INFRA] Delete duplicate root `main.py`
**Files:** `/home/andrey/repos/rest_assured/main.py`
**Описание:** Удалить байт-в-байт дубликат `rest_assured/src/main.py`. Также убрать строку `COPY main.py .` из Dockerfile в задаче T13.
**Acceptance criteria:**
- Файл `/home/andrey/repos/rest_assured/main.py` отсутствует.
- `git status` чистый после удаления (или удаление закоммичено).
- `grep -r "^from main " /home/andrey/repos/rest_assured/` ничего не находит.

---

### T2 [INFRA] Remove committed test-result XML artefacts
**Files:** `/home/andrey/repos/rest_assured/integration-test-results.xml`, `/home/andrey/repos/rest_assured/unit-test-results.xml`
**Описание:** Удалить закоммиченные xml-отчёты pytest-junit. (`.gitignore` правится в T3.)
**Acceptance criteria:**
- Оба файла отсутствуют в репозитории.
- `ls /home/andrey/repos/rest_assured/*-test-results.xml` возвращает «No such file».

---

### T3 [INFRA] Update `.gitignore` (xml results, settings.toml, .env)
**Files:** `/home/andrey/repos/rest_assured/.gitignore`
**Описание:** Добавить шаблоны:
- `*-test-results.xml`
- `/settings.toml` (только в корне, чтобы settings.toml.example не попал под игнор)
- Убедиться что `.env` уже присутствует (он уже есть).
**Acceptance criteria:**
- `git check-ignore /home/andrey/repos/rest_assured/integration-test-results.xml` возвращает 0.
- `git check-ignore /home/andrey/repos/rest_assured/settings.toml` возвращает 0.
- `git check-ignore /home/andrey/repos/rest_assured/settings.toml.example` возвращает 1 (не игнорируется).

---

### T4 [INFRA] Create `settings.toml.example`, untrack `settings.toml`
**Files:** `/home/andrey/repos/rest_assured/settings.toml.example`, `/home/andrey/repos/rest_assured/settings.toml`
**Описание:**
- Создать `settings.toml.example` с теми же ключами, но с плейсхолдерами (`password = "CHANGE_ME"`, `host = "localhost"`).
- `git rm --cached settings.toml` (после T3, который добавил его в gitignore — здесь deps на T3).
**Acceptance criteria:**
- `settings.toml.example` коммитится; `settings.toml` отсутствует в индексе.
- В `settings.toml.example` нет реальных значений `password = "password"`.
**deps:** T3

---

### T5 [INFRA] Fix `pyproject.toml` deps, dev-group, version sync
**Files:** `/home/andrey/repos/rest_assured/pyproject.toml`, `/home/andrey/repos/rest_assured/poetry.lock`
**Описание:**
- `syncpg (>=1.1.3,<2.0.0)` → `asyncpg (>=0.30.0,<0.31.0)`.
- Явно добавить `httpx (>=0.28.0,<0.29.0)` в main deps.
- Перенести `testcontainers` из main в dev-группу.
- Вернуть `[tool.poetry.group.dev.dependencies]` (или PEP 735 `[dependency-groups]`): `pytest`, `pytest-asyncio`, `pytest-httpx`, `ruff`, `mypy`, `python-semantic-release`.
- Поправить `[tool.pytest.ini_options]`: `testpaths = ["rest_assured/tests", "rest_assured/integrational_tests"]`, `asyncio_mode = "auto"`.
- Сохранить версию `1.1.0` (синхронизация со срезом FastAPI делается отдельно в T22).
- `poetry lock --no-update` затем `poetry lock` чтобы перегенерировать `poetry.lock`.
**Acceptance criteria:**
- `poetry check` проходит без ошибок.
- `poetry lock --check` проходит.
- `grep syncpg pyproject.toml` ничего не находит.
- `grep "^asyncpg" poetry.lock` находит запись.
- `poetry install --with dev --dry-run` показывает все dev-пакеты.

---

### T6 [INFRA] Multi-stage Dockerfile hardening (layer caching, non-root, exec-form CMD, pinned base)
**Files:** `/home/andrey/repos/rest_assured/Dockerfile`
**Описание:**
- Закрепить базовый образ: `python:3.13.3-slim@sha256:<digest>` (выбрать актуальный digest, оставить комментарий с командой `docker pull` для проверки).
- Pin Poetry: `pip install --no-cache-dir poetry==1.8.4`.
- Разделить кеширующие слои: сначала `COPY pyproject.toml poetry.lock ./`, затем `poetry install --only main --no-root --no-interaction --no-ansi`, и только потом `COPY . .`.
- Убрать `COPY main.py .` (T1 удалил файл).
- Создать non-root юзера: `RUN groupadd -r app && useradd -r -g app app` и `USER app` в runtime-стейдже.
- CMD в exec-form: `CMD ["sh", "-c", "exec python -m alembic -c rest_assured/src/alembic.ini upgrade heads && exec uvicorn rest_assured.src.main:app --host 0.0.0.0 --port 8000"]` — либо разнести на entrypoint-скрипт `docker/entrypoint.sh` с `exec uvicorn ...`.
- Файлы, принадлежащие `app:app` (`chown` после COPY).
**Acceptance criteria:**
- `docker build -t rest-assured:test -f Dockerfile .` собирается.
- `docker run --rm rest-assured:test id -u` возвращает не-`0`.
- `docker inspect rest-assured:test --format '{{.Config.Cmd}}'` содержит JSON-массив (exec-form).
- `hadolint Dockerfile` проходит без ошибок ERROR-уровня.
- Pull базового образа по digest успешен.
**deps:** T1, T5

---

### T7 [INFRA] Create root `.dockerignore`
**Files:** `/home/andrey/repos/rest_assured/.dockerignore`
**Описание:** Исключить из build-context: `.git`, `.venv`, `__pycache__`, `*.pyc`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `tests/`, `integrational_tests/`, `*-test-results.xml`, `.env`, `settings.toml`, `docker/`, `README*`, `CHANGELOG.md`.
**Acceptance criteria:**
- `.dockerignore` существует и содержит как минимум перечисленные паттерны.
- `docker build` (после T6) даёт меньший контекст (< 10 MB на стандартном репо).

---

### T8 [INFRA] Create `test-service/.dockerignore`
**Files:** `/home/andrey/repos/rest_assured/test-service/.dockerignore`
**Описание:** Исключить `__pycache__`, `*.pyc`, `.venv`, `.pytest_cache`.
**Acceptance criteria:**
- Файл существует.
- Содержит минимум `__pycache__/` и `*.pyc`.

---

### T9 [INFRA] Harden `docker-compose.prod.yml` (secrets, healthchecks, networks, pgdata, pinned tags)
**Files:** `/home/andrey/repos/rest_assured/docker/docker-compose.prod.yml`, `/home/andrey/repos/rest_assured/.env.example`
**Описание:**
- `image: postgres:17-alpine` (18 ещё не stable).
- `POSTGRES_USER: ${POSTGRES_USER:?required}`, `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?required}`, `POSTGRES_DB: ${POSTGRES_DB:?required}`.
- `env_file: ../.env` для всех сервисов, читающих credentials.
- Заменить `pgdata_test:/var/lib/postgresql` → `pgdata:/var/lib/postgresql/data` и переименовать ключ volume в `pgdata:`.
- `image: rest-assured:latest` → `image: rest-assured:${APP_VERSION:?required}` (берётся из `.env`).
- `image: test-service:latest` → `image: test-service:${TEST_SERVICE_VERSION:?required}`.
- Добавить healthcheck для `app` на `http://localhost:8000/api/v1/misc/health`.
- Добавить healthcheck для `test-service` на `http://localhost:8000/healthy`.
- Объявить explicit network: `networks: { backend: { driver: bridge } }`, подключить все сервисы.
- Создать `.env.example` с `POSTGRES_USER=user`, `POSTGRES_PASSWORD=CHANGE_ME`, `POSTGRES_DB=test_db`, `APP_VERSION=1.1.0`, `TEST_SERVICE_VERSION=0.1.0`.
**Acceptance criteria:**
- `docker compose -f docker/docker-compose.prod.yml config` валиден (с подгруженным `.env`).
- `grep "password\s*:\s*\"password\"" docker/docker-compose.prod.yml` ничего не находит.
- `grep ":latest" docker/docker-compose.prod.yml` ничего не находит.
- `grep "pgdata:/var/lib/postgresql/data" docker/docker-compose.prod.yml` находит.
- `.env.example` существует и в `.gitignore` отсутствует (только `.env` игнорится).

---

## Wave 2 — CODE: модели (без зависимостей)

### T10 [CODE] `models/services.py`: validation, SSRF guard, datetime fix, length limits, interval lower bound
**Files:** `/home/andrey/repos/rest_assured/rest_assured/src/models/services.py`
**Описание:**
- `url: str = Field(..., max_length=2048, description=...)` + `@field_validator("url")` (Pydantic v2):
  - Парсить через `urllib.parse.urlparse`.
  - Разрешить только `scheme in {"http", "https"}`.
  - Резолвить hostname через `socket.getaddrinfo`; для каждого IP проверять `ipaddress.ip_address(ip)`: запрещать `is_private`, `is_loopback`, `is_link_local`, `is_multicast`, `is_reserved`, а также явные диапазоны `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `::1`, `fc00::/7`, `fe80::/10`.
  - Опционально пропускать резолв в тестах: проверить `settings.app_settings.allow_private_urls` (default False); либо вынести validator-логику в pure-function `validate_public_url(url) -> str` чтобы её было удобно мокать.
- `http_method: Literal["GET", "POST", "HEAD", "PUT", "DELETE", "PATCH", "OPTIONS"] = "GET"`.
- `name: str = Field(..., max_length=255)`.
- `interval_ms: int = Field(default=60000, ge=1000, description=...)`.
- `created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), ...)`.
- Импорт `from datetime import datetime, timezone`.
**Acceptance criteria:**
- Pydantic validation отклоняет `ftp://...`, `file://...`, `http://127.0.0.1`, `http://10.0.0.1`, `http://169.254.169.254`, `http://[::1]`.
- Pydantic validation принимает `http://example.com`, `https://api.example.com:8080/path`.
- `Service(name="x", url="http://example.com", http_method="TRACE")` падает с ValidationError.
- `Service(name="x", url="http://example.com", interval_ms=500)` падает (ниже 1000).
- `Service(name="x"*256, url="http://example.com")` падает (max_length).
- `Service(...).created_at.tzinfo is timezone.utc`.
**Test guidance:**
- `tests/models/test_service_url_validator.py`:
  - parametrize accept: список «хороших» URL.
  - parametrize reject: scheme-violations, loopback, private nets, link-local, IPv6 loopback.
  - mock `socket.getaddrinfo` чтобы тесты были детерминированными.
- `tests/models/test_service_field_constraints.py`: `interval_ms < 1000` падает; `name` длиннее 255 падает; `http_method` не из Literal падает; `url` длиннее 2048 падает.
- `tests/models/test_service_created_at.py`: `created_at` aware и в UTC.

---

### T11 [CODE] `models/checks.py`: datetime tz-aware
**Files:** `/home/andrey/repos/rest_assured/rest_assured/src/models/checks.py`
**Описание:** `default_factory=datetime.utcnow` → `default_factory=lambda: datetime.now(timezone.utc)`; импорт `from datetime import datetime, timezone`.
**Acceptance criteria:**
- `CheckResult(service_id=1, is_up=True).checked_at.tzinfo is timezone.utc`.
- Все вхождения `datetime.utcnow` в файле отсутствуют (`grep -n utcnow rest_assured/src/models/checks.py` пусто).
**Test guidance:**
- `tests/models/test_check_result_defaults.py`: дефолтный `checked_at` aware и в UTC; разница с `datetime.now(timezone.utc)` < 1с.

---

### T12 [INFRA] Alembic migration: timezone-aware DateTime columns
**Files:** `/home/andrey/repos/rest_assured/rest_assured/alembic/versions/001_initial.py`
**Описание:** Заменить `sa.DateTime()` → `sa.DateTime(timezone=True)` в колонках `created_at` (services) и `checked_at` (check_results). Поскольку миграция ещё не в продакшне — правим ту же ревизию, не плодим новую. Если есть сомнения — создать новую ревизию `002_make_datetimes_tz_aware.py` с `alter_column ... type_=sa.DateTime(timezone=True), postgresql_using="<col> AT TIME ZONE 'UTC'"`.
**Acceptance criteria:**
- `grep "sa.DateTime()" rest_assured/alembic/versions/` ничего не находит.
- `alembic upgrade heads` на свежем postgres выполняется без ошибок.
- `psql -c "\d+ services"` показывает `timestamp with time zone` для `created_at`.

---

### T13 [CODE] `scheduler/evaluate.py`: error redaction, tz-aware datetime, no assert in prod
**Files:** `/home/andrey/repos/rest_assured/rest_assured/src/scheduler/evaluate.py`
**Описание:**
- `datetime.utcnow()` → `datetime.now(timezone.utc)` (импорт `timezone`).
- `assert response is not None, "..."` → `if response is None: raise RuntimeError("Either response or exception must be provided")`.
- Замена `repr(exception)` (может содержать URL с Basic Auth) → `_truncate(f"{type(exception).__name__}: {str(exception)[:480]}")`.
**Acceptance criteria:**
- `grep -n utcnow rest_assured/src/scheduler/evaluate.py` пусто.
- `grep -n "^\s*assert " rest_assured/src/scheduler/evaluate.py` пусто.
- При вызове с `httpx.RequestError("http://u:p@host/x")` сохранённый `error` не содержит подстроки `"u:p@"`.
**Test guidance:**
- `tests/scheduler/test_evaluate_response.py`:
  - given exception with creds in URL → error не содержит userinfo.
  - given `response is None and exception is None` → `RuntimeError`.
  - given response 200 with `expected_status=200` → `is_up=True`.
  - given response 500 with `expected_status=None` → `is_up=False`, `error` указывает ожидание `2xx`.
  - `CheckResult.checked_at` aware и в UTC.

---

## Wave 3 — CODE: scheduler/runner (depends on models, evaluate)

### T14 [CODE] `scheduler/runner.py`: SSL/SQL/concurrency hardening + public API for listener
**Files:** `/home/andrey/repos/rest_assured/rest_assured/src/scheduler/runner.py`
**Описание:**
- Поправить SQLModel-фильтр: `where(Service.is_active is True)` → `where(Service.is_active.is_(True))` (строка 57).
- `httpx.AsyncClient(..., follow_redirects=False)`.
- DB-retry на старте: 3 попытки с интервалом 1с (можно через простой цикл). Если все три неуспешны — НЕ падать fatal, а логировать warning и стартовать с пустыми воркерами (listener/poll наполнит позже).
- `assert self._client is not None` (`@property http_client`) → `if self._client is None: raise RuntimeError("SchedulerRunner not started")`.
- Перенести `from rest_assured.src.scheduler.worker import worker_loop` на верх модуля (циклической зависимости нет).
- `logger.info("scheduler started: {} workers", len(self._tasks))` → `logger.info("scheduler started: %s workers", len(self._tasks))`.
- В `stop()` после `asyncio.gather(*tasks, return_exceptions=True)` — пройтись по результатам и для каждого `isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError)` вызвать `logger.error("worker raised: %r", r, exc_info=r)`.
- Разбить `reschedule(sid)` на:
  - `async def stop_service(self, service_id: int) -> None:` — отменяет задачу, ждёт, удаляет из `_tasks`.
  - `async def refresh_service(self, service_id: int) -> None:` — `stop_service` + перечитать `Service` из БД + `ensure_running(service)` если `is_active`.
- Новые публичные методы для listener'а:
  - `def active_service_ids(self) -> set[int]: return set(self._tasks)`.
  - `def ensure_running(self, service: Service) -> None:` — обёртка над `_spawn` идемпотентная.
- Убрать модуль-level singleton `scheduler_runner = SchedulerRunner()` (миграция на factory в main делается в T16). Оставить класс — singleton создаётся в `lifespan`.
**Acceptance criteria:**
- `grep -n "is_active is True" rest_assured/src/scheduler/` пусто.
- `grep -n "follow_redirects" rest_assured/src/scheduler/runner.py` находит `follow_redirects=False`.
- `grep -n "^\s*assert " rest_assured/src/scheduler/runner.py` пусто.
- `grep -n "scheduler_runner = SchedulerRunner" rest_assured/src/scheduler/runner.py` пусто.
- В модуле есть публичные методы `active_service_ids`, `ensure_running`, `stop_service`, `refresh_service`.
**Test guidance:**
- `tests/scheduler/test_runner_filter.py`: создать 2 service (active=True, active=False); `await runner.start()` поднимает воркер только для активного.
- `tests/scheduler/test_runner_db_retry.py`: monkey-patch `get_session` чтобы первые 2 вызова кидали `OperationalError`, на 3-й возвращали реальную сессию; `runner.start()` не падает.
- `tests/scheduler/test_runner_db_fatal.py`: 3 неуспешные попытки → `runner.start()` завершается, `active_workers_count == 0`, ВНУТРИ логов есть warning.
- `tests/scheduler/test_runner_no_redirects.py`: httpx_mock мокает 302 на приватный URL; воркер не следует по редиректу — фиксируется `is_up=False` (или специальный статус).
- `tests/scheduler/test_runner_public_api.py`:
  - `ensure_running(service)` идемпотентна (повторный вызов не плодит задач).
  - `stop_service(sid)` отменяет задачу, удаляет ключ.
  - `refresh_service(sid)` перечитывает БД: если стал `is_active=False` — не перезапускает.
  - `active_service_ids()` возвращает текущий снапшот.
- `tests/scheduler/test_runner_gather_logs_exceptions.py`: воркер кидает RuntimeError; `await runner.stop()` логирует exception (через caplog).

---

## Wave 4 — CODE: scheduler/worker (depends on runner public API & evaluate)

### T15 [CODE] `scheduler/worker.py`: counter accounting moved to finally + safety
**Files:** `/home/andrey/repos/rest_assured/rest_assured/src/scheduler/worker.py`
**Описание:**
- Переписать блок сохранения так, чтобы `checks_total`/`checks_failed` и `last_loop_at` инкрементировались ДО `commit()` (а лучше — в `finally` блоке с try/except для commit). Целевой инвариант: «факт проверки зафиксирован в счётчиках даже при падении commit».
- Пример:
  ```python
  check = evaluate_response(...)
  runner.checks_total += 1
  if not check.is_up:
      runner.checks_failed += 1
  runner.last_loop_at = datetime.now(timezone.utc)
  session = get_session()
  try:
      session.add(check)
      await session.commit()
      await session.refresh(check)
  except Exception:
      await session.rollback()
      log.exception("failed to persist check_result")
  finally:
      await session.close()
  await runner.fire_callbacks(check)
  ```
- `service.http_method` теперь Literal — httpx-вызов не меняем.
- Убедиться, что используем `runner.http_client` (через property, который теперь кидает RuntimeError если не стартовал).
**Acceptance criteria:**
- При исключении в `session.commit()` `runner.checks_total` и `runner.checks_failed` уже отражают факт проверки.
- При is_up=False счётчик `checks_failed` всегда инкрементируется, даже если БД упала.
**Test guidance:**
- `tests/scheduler/test_worker_counters_on_commit_failure.py`:
  - monkey-patch session: `commit()` кидает `OperationalError`.
  - воркер делает одну итерацию (через очень короткий interval_ms + `asyncio.wait_for`).
  - `runner.checks_total == 1`, `runner.checks_failed == 1` (если httpx 500) или `0` (если 200).
- `tests/scheduler/test_worker_no_redirect_persist.py`: ответ 302 → is_up False (если expected_status=200), CheckResult сохраняется с http_status=302.
**deps:** T14, T13

---

## Wave 5 — CODE: scheduler/listener (depends on runner public API)

### T16 [CODE] `scheduler/listener.py`: public callback, log injection sanitizer, public runner API, SecretStr
**Files:** `/home/andrey/repos/rest_assured/rest_assured/src/scheduler/listener.py`
**Описание:**
- Переименовать `_on_service_changed` → `on_service_changed` (без подчёркивания); обновить вызов `add_listener("service_changed", self.on_service_changed)`.
- Санитизация payload перед логированием: helper `_sanitize_log(s: str, limit: int = 200) -> str` (заменяет `\r`, `\n`, непечатаемые символы на `\\x..`). Применить в строках логирования NOTIFY и в poll-loop'е.
- Заменить приватные обращения:
  - `self._runner._tasks.keys()` → `self._runner.active_service_ids()`.
  - `self._runner._spawn(s)` → `self._runner.ensure_running(s)`.
  - `await self._runner.reschedule(sid)` → `await self._runner.refresh_service(sid)` (или `stop_service` в зависимости от семантики; deactivation → `stop_service`).
- `where(Service.is_active is True)` → `where(Service.is_active.is_(True))`.
- В `start()` catch блок: `logger.warning("Could not start LISTEN, falling back to poll-only mode", exc_info=True)`.
- В асинхронной коннект-настройке `password=settings.db_settings.password.get_secret_value()` (T21 переводит конфиг на SecretStr).
**Acceptance criteria:**
- `grep -n "_on_service_changed\|_runner\._tasks\|_runner\._spawn\|_runner\.reschedule" rest_assured/src/scheduler/listener.py` пусто.
- `grep -n "is_active is True" rest_assured/src/scheduler/listener.py` пусто.
- В логах для payload `"\n\nINFO: hacked"` отображается экранированная форма.
**Test guidance:**
- `tests/scheduler/test_listener_sanitize.py`: вызвать `on_service_changed(None, 0, "service_changed", "1\nFAKE LOG")` с моком runner; через caplog убедиться что в записи нет реальных `\n`.
- `tests/scheduler/test_listener_uses_public_api.py`: подменить runner на `MagicMock(spec=SchedulerRunner)`; вызвать `on_service_changed(..., payload="42")`; убедиться что вызван `refresh_service(42)`.
- `tests/scheduler/test_listener_poll_diff.py`: runner.active_service_ids возвращает {1}, БД возвращает Service(id=2, is_active=True) — poll-цикл вызывает `ensure_running(service)` и `stop_service(1)`.
- `tests/scheduler/test_listener_invalid_payload.py`: payload `"not-int\nINJECT"` → лог содержит экранированную форму, runner не вызывается.
**deps:** T14

---

## Wave 6 — CODE: configs (SecretStr)

### T17 [CODE] `configs/app/main.py`: DBConfig.password as SecretStr, version helper
**Files:** `/home/andrey/repos/rest_assured/rest_assured/src/configs/app/main.py` (или путь, где определён `DBConfig` — найти `grep -rn "class DBConfig" rest_assured/src/configs/`)
**Описание:**
- `password: str` → `password: SecretStr` (Pydantic v2 `pydantic.SecretStr`).
- При построении DSN/коннекта: `password.get_secret_value()`. Найти все вхождения `settings.db_settings.password` и обернуть.
- Добавить хелпер `def get_app_version() -> str: return importlib.metadata.version("rest_assured")` — будет использован в T22.
**Acceptance criteria:**
- `repr(settings.db_settings)` не содержит plaintext пароля.
- Все клиенты (runner, listener, alembic env) получают пароль через `.get_secret_value()`.
**Test guidance:**
- `tests/configs/test_secret_str.py`: загрузка settings c паролем `"s3cret"` → `repr(settings.db_settings.password)` содержит `"**********"`, `password.get_secret_value() == "s3cret"`.
- `tests/configs/test_version_helper.py`: `get_app_version()` возвращает значение, совпадающее с `pyproject.toml`.

---

## Wave 7 — CODE: api / main (depends on runner, listener, configs)

### T18 [CODE] `main.py`: app factory + lifespan + auth on /api/health/scheduler + version sync
**Files:** `/home/andrey/repos/rest_assured/rest_assured/src/main.py`
**Описание:**
- Убрать модуль-level `listener = ServiceChangeListener()` и `scheduler_runner` (он больше не singleton после T14).
- Ввести `def create_app() -> FastAPI:`:
  - Внутри инстанцирует `runner = SchedulerRunner()`, `listener = ServiceChangeListener()`, `listener.set_runner(runner)`.
  - Регистрирует callback'и (если будут) ДО `lifespan.startup`.
  - В `lifespan`: `await runner.start(); await listener.start(); app.state.runner = runner; app.state.listener = listener; yield; await listener.stop(); await runner.stop()`.
  - Возвращает FastAPI app.
- `app = create_app()` остаётся как модульный экспорт для uvicorn (`rest_assured.src.main:app`).
- `version=` из `importlib.metadata.version("rest_assured")` (через хелпер T17).
- Auth для `/api/health/scheduler`:
  - `from fastapi import Header, HTTPException, Depends, status`.
  - `async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:` сравнить с `settings.app_settings.api_key.get_secret_value()` (новое поле в конфиге; для теста удобно добавить SecretStr).
  - Если ключ не совпадает или отсутствует — `raise HTTPException(status.HTTP_401_UNAUTHORIZED)`.
  - `@app.get("/api/health/scheduler", dependencies=[Depends(require_api_key)])`.
  - Внутри хендлера читать `request.app.state.runner.stats`.
**Acceptance criteria:**
- `from rest_assured.src.main import create_app, app` импортируется.
- `client.get("/api/health/scheduler")` без `X-API-Key` → 401.
- `client.get("/api/health/scheduler", headers={"X-API-Key": "..."})` с правильным ключом → 200.
- `app.version == "1.1.0"` (или то, что указано в pyproject).
- Нет модульных singleton'ов `scheduler_runner`/`listener` в `main.py`.
**Test guidance:**
- `tests/api/test_health_scheduler_auth.py`:
  - missing header → 401.
  - wrong key → 401.
  - correct key → 200 + body содержит `checks_total`, `checks_failed`, `active_workers_count`.
- `tests/api/test_create_app_factory.py`:
  - `create_app()` возвращает новый instance каждый раз.
  - `app.state.runner` появляется после startup (через `TestClient(app) as c`).
- `tests/api/test_app_version.py`: `app.version` совпадает с `importlib.metadata.version("rest_assured")`.
**deps:** T14, T16, T17

---

## Wave 8 — test-service & integration tests

### T19 [CODE] `test-service/main.py`: real 500 status, async sleep
**Files:** `/home/andrey/repos/rest_assured/test-service/main.py`
**Описание:**
- `return {...}, 500` (FastAPI трактует как 200 OK с tuple-body) заменить на `JSONResponse(content={...}, status_code=500)`. Применить в `/down`, `/flaky` (ветка fail), `/controlled` (ветка down).
- `time.sleep(3)` в `/slow` → `await asyncio.sleep(3)` (импорт `asyncio`).
- Импорт: `from fastapi.responses import JSONResponse`.
**Acceptance criteria:**
- `curl -i http://localhost:8001/down` → `HTTP/1.1 500`.
- `curl -i http://localhost:8001/slow` не блокирует event loop (можно параллельно дёрнуть `/healthy` и получить ответ < 0.1с).
**Test guidance:**
- `test-service/tests/test_endpoints.py` (или в основной test-suite через httpx):
  - `/down` → 500.
  - `/controlled` после `/toggle` → 500.
  - `/slow` не блокирует другие запросы (параллельно через `asyncio.gather`).

---

### T20 [CODE] `integrational_tests/test_worker.py`: deflake + adapt to new runner
**Files:** `/home/andrey/repos/rest_assured/rest_assured/integrational_tests/test_worker.py`
**Описание:**
- В тестах: `interval_ms=200` → `interval_ms=100`, ассерт `len(results) >= 2` → `>= 3` (или применить `asyncio.wait_for` на условие).
- Использовать новые публичные методы runner вместо `runner._tasks` (например, `runner.active_service_ids()` в `test_worker_stops_on_cancelled_error`).
- Помнить: после T14 нет глобального `scheduler_runner`; локальный `runner = SchedulerRunner()` в тестах остаётся валидным.
- `test_worker_respects_interval`: с `interval_ms=500` и 1.2s ожидания verify `2 <= len(results) <= 4` — оставить как есть, но если нестабильно — поднять до 1.5s.
**Acceptance criteria:**
- `pytest rest_assured/integrational_tests/test_worker.py -q` проходит на 10 последовательных прогонов без flake.
- `grep -n "_tasks" rest_assured/integrational_tests/test_worker.py` пусто.
**Test guidance:**
- Запускать тесты по 10 раз в CI (`pytest -x --count=10` via `pytest-repeat`) — добавить в Makefile при необходимости.
**deps:** T14

---

## Wave 9 — финальные мелочи

### T21 [INFRA] Sync FastAPI version with package metadata
**Files:** (изменения в `rest_assured/src/main.py` уже в T18 — этот таск зарезервирован, помечен done вместе с T18)
**Описание:** Покрыто в T18; отдельная строка для трекинга в чек-листе.
**Acceptance criteria:**
- `app.version == importlib.metadata.version("rest_assured")`.
**deps:** T18

---

## Сводная таблица волн

- **Wave 1 (parallel, no deps):** T1, T2, T3, T6 (deps T1+T5), T7, T8, T9, T5
  - Строго без deps: T1, T2, T3, T5, T7, T8, T9.
  - С deps: T4 (T3), T6 (T1+T5).
- **Wave 2 (CODE models, no deps):** T10, T11, T12, T13
- **Wave 3 (CODE runner, deps T10/T11/T13):** T14
- **Wave 4 (CODE worker, deps T14/T13):** T15
- **Wave 5 (CODE listener, deps T14):** T16
- **Wave 6 (CODE configs, no deps):** T17
- **Wave 7 (CODE main, deps T14/T16/T17):** T18
- **Wave 8 (CODE test-service & integration, deps T14):** T19 (no deps), T20 (T14)
- **Wave 9 (tracking):** T21 (T18)

---

## Минимальный чек-лист (для скана)

- [ ] T1  [INFRA] Delete duplicate root `main.py`
- [ ] T2  [INFRA] Remove committed test-result XML
- [ ] T3  [INFRA] Update `.gitignore`
- [ ] T4  [INFRA] `settings.toml.example` + untrack `settings.toml` (deps: T3)
- [ ] T5  [INFRA] Fix `pyproject.toml` (asyncpg, httpx, dev-group, testpaths) + relock
- [ ] T6  [INFRA] Harden Dockerfile (deps: T1, T5)
- [ ] T7  [INFRA] Root `.dockerignore`
- [ ] T8  [INFRA] `test-service/.dockerignore`
- [ ] T9  [INFRA] Harden `docker-compose.prod.yml` + `.env.example`
- [ ] T10 [CODE]  `models/services.py` validators + SSRF + tz
- [ ] T11 [CODE]  `models/checks.py` tz-aware
- [ ] T12 [INFRA] Alembic migration: `DateTime(timezone=True)`
- [ ] T13 [CODE]  `scheduler/evaluate.py` redact + raise + tz
- [ ] T14 [CODE]  `scheduler/runner.py` is_(True), retries, public API, no singleton (deps: T10, T11, T13)
- [ ] T15 [CODE]  `scheduler/worker.py` counters in finally (deps: T14, T13)
- [ ] T16 [CODE]  `scheduler/listener.py` public callback + sanitize + public runner API (deps: T14)
- [ ] T17 [CODE]  `configs/app/main.py` SecretStr + version helper
- [ ] T18 [CODE]  `main.py` factory + lifespan + auth + version (deps: T14, T16, T17)
- [ ] T19 [CODE]  `test-service/main.py` real 500 + async sleep
- [ ] T20 [CODE]  `integrational_tests/test_worker.py` deflake + new API (deps: T14)
- [ ] T21 [INFRA] Version sync tracking (deps: T18)
