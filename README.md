# Rest Assured — Система мониторинга доступности сервисов

[![CI](https://img.shields.io/github/actions/workflow/status/mipt-pp-hackaton/rest_assured/ci.yml?branch=main&label=CI&logo=github&style=flat-square)](https://github.com/mipt-pp-hackaton/rest_assured/actions)
[![Release Version](https://img.shields.io/github/v/release/mipt-pp-hackaton/rest_assured?label=release&logo=github&style=flat-square&color=blue)](https://github.com/mipt-pp-hackaton/rest_assured/releases)
[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg?logo=python&style=flat-square)](https://pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi&style=flat-square)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white&style=flat-square)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white&style=flat-square)](https://www.docker.com)
[![Poetry](https://img.shields.io/badge/Poetry-60A5FA?logo=poetry&logoColor=white&style=flat-square)](https://python-poetry.org)

---

## 📋 Описание проекта

**Rest Assured** — это интеллектуальная система мониторинга, предназначенная для автоматической проверки состояния REST-сервисов. Система обеспечивает непрерывный контроль доступности endpoint'ов, рассчитывает показатели **SLA (Service Level Agreement)** и мгновенно уведомляет ответственных лиц в случае сбоев.

### 🎯 Цель проекта
Разработать надежное решение для мониторинга, которое позволяет минимизировать время простоя (downtime) за счет оперативного оповещения и предоставления детальной статистики аптайма.

---

## ✨ Ключевые возможности

- 🔍 **Автоматический мониторинг**: Регулярная проверка REST-endpoint’ов по заданному расписанию.
- ⚙️ **Управление сервисами**: Гибкое добавление и удаление сервисов для мониторинга через API.
- 👥 **Ответственные лица**: Закрепление конкретных сотрудников за каждым сервисом для адресных уведомлений.
- 📈 **SLA и Uptime**: Расчет и хранение статистики доступности, отслеживание соблюдения SLA.
- 📧 **Умные уведомления**: Автоматическая отправка Email-оповещений при обнаружении недоступности.
- 📊 **Сводная аналитика**: Получение отчетов по состоянию всех отслеживаемых систем в одном месте.
- 🧪 **Тестовый полигон**: Наличие встроенного тестового сервиса для демонстрации работы мониторинга.

---

## 🛠 Технические требования

- **Язык**: Python 3.13
- **API**: Полное взаимодействие через REST API.
- **Хранилище**: PostgreSQL (хранение конфигураций, истории проверок и статистики).
- **Миграции**: Alembic для контроля схемы БД.
- **Контейнеризация**: Полная поддержка Docker и Docker Compose.
- **CI/CD**: Автоматическое версионирование (Semantic Release) и прогон тестов.

---

## 👤 Пользовательские сценарии (User Stories)

1. **Регистрация сервиса**: Специалист поддержки через API добавляет список URL для мониторинга.
2. **Настройка SLA**: Для каждого сервиса задается допустимый процент доступности и список Email ответственных сотрудников.
3. **Цикл проверки**: Система в фоновом режиме выполняет запросы. В случае ошибки `HTTP 5xx` или таймаута фиксируется инцидент.
4. **Оповещение**: При сбое система мгновенно отправляет письмо ответственному сотруднику.
5. **Анализ**: Менеджер запрашивает сводную статистику за месяц для проверки выполнения SLA.

---

## 🚀 Инструкции по запуску

### Быстрый старт через Docker
Это самый простой способ запустить всю инфраструктуру (БД + Приложение + Тестовый сервис):
```bash
make dprod
```

### Локальная разработка
1. **Установка зависимостей**:
   ```bash
   poetry install
   ```
2. **Настройка БД**:
   Убедитесь, что параметры в `settings.toml` верны, затем примените миграции:
   ```bash
   make migrate
   ```
3. **Запуск сервера**:
   ```bash
   make dev
   ```

---

## 🧪 Тестирование и проверка

Проект включает в себя как модульные, так и интеграционные тесты:

- **Unit-тесты**: `make utest`
- **Интеграционные тесты**: `make itest`
- **Проверка качества кода**: `make lint` && `make type`

---

## 🧭 Процесс работы над задачами

Все задачи отслеживаются в [GitHub Issues](https://github.com/mipt-pp-hackaton/rest_assured/issues). Эпики помечены лейблом `epic`, конкретные таски — `epic:1-catalog`, `epic:2-checks`, `epic:3-metrics`, `epic:4-notifications`, `epic:5-ui`.

### Шаг 1. Выбрать тикет

1. Открой [список открытых issues](https://github.com/mipt-pp-hackaton/rest_assured/issues).
2. Найди свободный тикет (без `assignees`) в нужном эпике.
3. Назначь себя через **Assignees → assign yourself** в правой панели.
4. Внимательно прочитай разделы **Зависит от**, **Что сделать**, **Тесты**, **DoD** — это полный контракт задачи.

### Шаг 2. Создать ветку

Имя ветки: `T<номер_эпика>.<номер_таски>-<краткое-описание-кебаб-кейсом>`. Базовая ветка — `main`.

```bash
git checkout main
git pull origin main
git checkout -b T1.1-fix-cli-imports
```

### Шаг 3. Решить задачу

1. Реализуй все пункты из раздела **Что сделать** в тикете.
2. Напиши тесты, перечисленные в разделе **Тесты**.
3. Прогони локально:
   ```bash
   make lint && make type && make utest && make itest
   ```
4. Коммить маленькими атомарными коммитами в формате [Conventional Commits](https://www.conventionalcommits.org) — это нужно для Semantic Release (см. ниже):
   ```bash
   git commit -m "feat(auth): add JWT login endpoint"
   git commit -m "fix(cli): correct package import path"
   ```

### Шаг 4. Создать Pull Request

1. Запушь ветку:
   ```bash
   git push -u origin T1.1-fix-cli-imports
   ```
2. Открой PR в GitHub: **Compare & pull request**.
3. Заполни:
   - **Title**: `T1.1 — Фикс импорта в src/cli.py` (тот же, что у тикета).
   - **Description**: добавь строку `Closes #27` (номер своего тикета — это автоматически закроет issue после мерджа).
   - Кратко опиши, что сделано и какие тесты проходят.
4. **Reviewers → AndreyQuantum** (правая панель PR).
5. **Labels**: проставь тот же label эпика, что и у тикета (например `epic:1-catalog`).

### Шаг 5. Дождаться ревью

- CI должен быть зелёным (lint + tests + типы).
- Если ревьюер оставил комментарии — фикси, пушь в ту же ветку, отвечай на комменты с **Resolve conversation**.
- После аппрува ревьюер мерджит PR в `main` (squash merge).

### Полезные команды

```bash
# посмотреть свои тикеты
gh issue list --assignee "@me"

# создать PR прямо из CLI
gh pr create --reviewer AndreyQuantum --label epic:1-catalog --body "Closes #27"

# проверить статус CI у текущей ветки
gh pr checks
```

---

## 🔄 Процесс релиза

Мы используем **Semantic Release** для автоматизации:
- `fix:` -> обновление патч-версии.
- `feat:` -> обновление минорной версии.
- `BREAKING CHANGE:` -> обновление мажорной версии.

Каждый релиз автоматически создает тег, обновляет `CHANGELOG.md` и пересобирает Docker-образ с актуальной версией.
