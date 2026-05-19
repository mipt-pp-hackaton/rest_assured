import argparse
import asyncio
import os

import uvicorn
from alembic import command
from alembic.config import Config


def _settings_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../settings.toml"))


async def _start_server():
    os.environ["CONFIG_PATH"] = _settings_path()
    from rest_assured.src.configs.app.main import settings

    config = uvicorn.Config(
        "rest_assured.src.main:app",
        host=settings.app_settings.host,
        port=settings.app_settings.port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


def _run_migrations():
    base_path = os.path.dirname(__file__)
    alembic_cfg = Config(os.path.join(base_path, "alembic.ini"))
    command.upgrade(alembic_cfg, "heads")


def main():
    parser = argparse.ArgumentParser(prog="rest-assured")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("server", help="Start the FastAPI server")
    sub.add_parser("migrate", help="Run pending Alembic migrations")

    args = parser.parse_args()

    if args.command == "migrate":
        _run_migrations()
    else:
        asyncio.run(_start_server())


if __name__ == "__main__":
    main()
