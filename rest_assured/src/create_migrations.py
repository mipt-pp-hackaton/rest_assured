import argparse

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
    postgres = PostgresContainer("postgres:18")
    postgres.start()
    settings.db.db_name = postgres.dbname
    settings.db.db_port = postgres.get_exposed_port(5432)
    settings.db.db_user = postgres.username
    settings.db.db_password = postgres.password
    settings.db.db_host = postgres.get_container_host_ip()

    alembic_cfg = Config("alembic.ini")
    command.upgrade(config=alembic_cfg, revision="heads")
    upgrade_message = input("Введите описание миграции: ")
    command.revision(
        config=alembic_cfg,
        autogenerate=True,
        message=upgrade_message,
        branch_label=branch_label,
    )


if __name__ == "__main__":
    main()
