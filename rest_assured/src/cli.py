import argparse
import asyncio
import os

import uvicorn
from alembic import command
from alembic.config import Config


async def start_server():
    from personal_assistant.src.configs.app import settings

    config = uvicorn.Config(
        "personal_assistant.src.main:app",
        host=settings.app.app_host,
        port=settings.app.app_port,
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
