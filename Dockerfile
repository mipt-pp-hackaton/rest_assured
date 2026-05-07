FROM python:3.13-slim AS builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir poetry \
  && poetry config virtualenvs.create false \
  && poetry install --only main --no-interaction --no-ansi

FROM python:3.13-slim AS runtime

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY rest_assured/ rest_assured/
COPY settings.toml .
COPY main.py .

CMD sh -c "python -m alembic -c rest_assured/src/alembic.ini upgrade heads && uvicorn rest_assured.src.main:app --host 0.0.0.0 --port 8000"
