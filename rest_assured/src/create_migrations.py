import argparse
import os

from alembic import command
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

from rest_assured.src.configs.app.main import settings


def main():
    parser = argparse.ArgumentParser(description="Create Alembic migrations.")
    parser.add_argument(
        "--branch-label",
        type=str,
        help="Name of the Alembic branch label.",
        required=False,
    )

    args = parser.parse_args()
    branch_label = args.branch_label

    # Запускаем тестовый PostgreSQL
    postgres = PostgresContainer("postgres:18")
    postgres.start()

    # Обновляем настройки БД на тестовый контейнер
    settings.db_settings.name = postgres.dbname
    settings.db_settings.port = int(postgres.get_exposed_port(5432))
    settings.db_settings.user = postgres.username
    settings.db_settings.password = postgres.password
    settings.db_settings.host = postgres.get_container_host_ip()

    # ВАЖНО: путь к alembic.ini относительно rest_assured/src/
    base_path = os.path.dirname(__file__)  # rest_assured/src/
    alembic_cfg = Config(os.path.join(base_path, "alembic.ini"))

    # Обновляем sqlalchemy.url в конфиге Alembic на актуальный DSN
    alembic_cfg.set_main_option("sqlalchemy.url", settings.db_settings.dsl)

    # Применяем все существующие миграции
    command.upgrade(config=alembic_cfg, revision="heads")

    # Создаём новую миграцию
    upgrade_message = input("Введите описание миграции: ")
    command.revision(
        config=alembic_cfg,
        autogenerate=True,
        message=upgrade_message,
        branch_label=branch_label,
    )

    # Останавливаем контейнер
    postgres.stop()


if __name__ == "__main__":
    main()