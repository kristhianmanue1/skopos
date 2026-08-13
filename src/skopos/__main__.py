"""Punto de entrada de Skopos: `skopos` (versión) o `skopos query <tema>`."""

from __future__ import annotations

import sys

from skopos import __version__
from skopos.cli import query_command
from skopos.vigilante import watch_command


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(f"skopos {__version__}")
        return 0
    if argv[0] == "query":
        return query_command(argv[1:])
    if argv[0] == "watch":
        return watch_command(argv[1:])
    print(f"comando desconocido: {argv[0]}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
