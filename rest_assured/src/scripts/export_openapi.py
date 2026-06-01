"""Экспорт OpenAPI-схемы FastAPI в статический файл (``make openapi``).

Использование::

    poetry run python3 -m rest_assured.src.scripts.export_openapi [output.json]

Без аргумента пишет в ``openapi.json`` в текущей директории. Схема
генерируется из ``create_app()`` и не требует подключения к БД.
"""

import json
import sys

from rest_assured.src.main import create_app


def export(output_path: str = "openapi.json") -> str:
    app = create_app()
    schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return output_path


def main() -> None:
    output_path = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    path = export(output_path)
    print(f"OpenAPI schema written to {path}")


if __name__ == "__main__":
    main()
