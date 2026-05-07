import argparse
import asyncio
import os

import uvicorn
from alembic import command
from alembic.config import Config


async def start_server():
    from rest_assured.src.configs.app.main import settings

    config = uvicorn.Config(
        "rest_assured.src.main:app",
        host=settings.app_settings.host,
        port=settings.app_settings.port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


def run_migrations():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config file")
    args, _ = parser.parse_known_args()
    os.environ["CONFIG_PATH"] = args.config

    base_path = os.path.dirname(__file__)
    alembic_cfg = Config(os.path.join(base_path, "alembic.ini"))
    command.upgrade(alembic_cfg, "heads")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config file")
    args = parser.parse_args()
    os.environ["CONFIG_PATH"] = args.config

    asyncio.run(start_server())


if __name__ == "__main__":
    main()
