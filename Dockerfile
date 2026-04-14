FROM python:3.13-slim AS builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir poetry \
  && poetry config virtualenvs.create false

RUN poetry build --format wheel

FROM python:3.13-slim AS runtime


COPY --from=builder /app/dist /tmp/dist

RUN pip install --no-cache-dir /tmp/dist/*.whl \
  && rm -rf /tmp/dist

COPY settings.toml .

CMD pa-migrate --config settings.toml && pa-server --config settings.toml