"""CLI wrapper to invoke alembic with the project's alembic.ini.

Usage:
    caption-agent-migrate upgrade head
    caption-agent-migrate revision --autogenerate -m "add x"
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    from alembic.config import CommandLine

    config_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    if not config_path.exists():
        print(f"alembic.ini not found at {config_path}", file=sys.stderr)
        return 1

    cli = CommandLine(prog="caption-agent-migrate")
    args = ["-c", str(config_path), *sys.argv[1:]]
    return cli.main(argv=args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
