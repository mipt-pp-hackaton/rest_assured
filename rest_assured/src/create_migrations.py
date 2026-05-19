import argparse
import os

from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from testcontainers.postgres import PostgresContainer

_settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../settings.toml"))
os.environ["CONFIG_PATH"] = _settings_path

from rest_assured.src.configs.app.main import settings  # noqa: E402


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

    postgres = PostgresContainer("postgres:18-alpine")
    postgres.start()

    settings.db_settings.name = postgres.dbname
    settings.db_settings.port = postgres.get_exposed_port(5432)
    settings.db_settings.user = postgres.username
    settings.db_settings.password = SecretStr(postgres.password)
    settings.db_settings.host = postgres.get_container_host_ip()

    base_path = os.path.dirname(__file__)
    alembic_cfg = Config(os.path.join(base_path, "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.db_settings.dsl)

    command.upgrade(config=alembic_cfg, revision="heads")

    upgrade_message = input("Введите описание миграции: ")
    command.revision(
        config=alembic_cfg,
        autogenerate=True,
        message=upgrade_message,
        branch_label=branch_label,
    )

    postgres.stop()


if __name__ == "__main__":
    main()
