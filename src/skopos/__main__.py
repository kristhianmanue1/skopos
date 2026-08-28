"""Punto de entrada de Skopos: `skopos`, `skopos query <tema>`, `skopos watch`."""

from __future__ import annotations

import sys

from skopos import __version__
from skopos.cli import query_command, reanalizar_command
from skopos.indexador import indexar_command
from skopos.vigilante import watch_command

COMANDOS = {"query": query_command, "watch": watch_command,
            "reanalizar": reanalizar_command, "indexar": indexar_command}

_AYUDA = f"""skopos {__version__}

Comandos:
  query <tema>              busca por tema en lo ya analizado (SPEC-004)
  watch [--sessions-dir DIR] [--intervalo SEGUNDOS] [--backfill]
                             vigila y procesa turnos nuevos (SPEC-005);
                             por defecto sólo desde su arranque (ADR-008)
  reanalizar <turn_id> [--solo-redaccion]
                             supersede explícito: nueva versión del
                             análisis (SPEC-003 v2, ADR-007)
  indexar [RUTAS...] [--patron P] [--limite N] [--dry-run]
                             indexa turnos observados en skopos.turnos,
                             sin llamar al modelo (P-004)

`skopos <comando> --help` muestra los argumentos de cada uno."""


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(_AYUDA)
        return 0
    comando = COMANDOS.get(argv[0])
    if comando is None:
        print(f"comando desconocido: {argv[0]}\n\n{_AYUDA}", file=sys.stderr)
        return 1
    return comando(argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
