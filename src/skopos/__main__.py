"""Punto de entrada de Skopos. Cascarón F2: sólo imprime versión."""

from __future__ import annotations

from skopos import __version__


def main(argv: list[str] | None = None) -> int:
    print(f"skopos {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
