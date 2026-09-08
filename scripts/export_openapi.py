from __future__ import annotations

import argparse
import json
from pathlib import Path

from gulfdocs_api.main import app

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs" / "openapi.json"


def rendered_schema() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write or verify the GulfDocs OpenAPI snapshot")
    parser.add_argument("--write", action="store_true", help="Update the committed snapshot")
    args = parser.parse_args()
    rendered = rendered_schema()
    if args.write:
        SNAPSHOT.write_text(rendered, encoding="utf-8")
        return 0
    if not SNAPSHOT.exists() or SNAPSHOT.read_text(encoding="utf-8") != rendered:
        print("OpenAPI snapshot drifted; run: uv run python scripts/export_openapi.py --write")
        return 1
    print("OpenAPI snapshot is synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
