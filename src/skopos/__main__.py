"""Punto de entrada de Skopos: despacho de comandos.

Nombres en inglés por ADR-016 (la frontera la leen otros sistemas). Los
tres comandos que nacieron en español conservan su nombre como alias
vivo: renombrarlos a secas rompería a quien los tenga en un script, y la
decisión de idioma no justificaba romper nada. El retiro del alias
exigiría decisión propia.
"""

from __future__ import annotations

import sys

from skopos import __version__
from skopos.analizador import analyze_command
from skopos.busqueda import buscar_command
from skopos.cli import query_command, reanalizar_command
from skopos.indexador import indexar_command
from skopos.vigilante import watch_command

COMANDOS = {"query": query_command, "watch": watch_command,
            "analyze": analyze_command,
            "reanalyze": reanalizar_command, "index": indexar_command,
            "search": buscar_command,
            # alias heredados (ADR-016 (d)): mismo comando, nombre viejo
            "reanalizar": reanalizar_command, "indexar": indexar_command,
            "buscar": buscar_command}

ALIAS_HEREDADOS = {"reanalizar": "reanalyze", "indexar": "index",
                   "buscar": "search"}

_AYUDA = f"""skopos {__version__}

Comandos:
  query <tema>              busca por tema en lo ya analizado (SPEC-004)
  watch [--sessions-dir DIR] [--intervalo SEGUNDOS] [--backfill]
                             vigila y procesa turnos nuevos (SPEC-005);
                             por defecto sólo desde su arranque (ADR-008)
  analyze [--project P] [--cli C] [--anchor PATRON] [--limit N] [--dry-run]
                             analiza turnos YA indexados que aún no
                             tienen análisis (ADR-017)
  reanalyze <turn_id> [--solo-redaccion]
                             supersede explícito: nueva versión del
                             análisis (SPEC-003 v2, ADR-007)
  index [RUTAS...] [--patron P] [--limite N] [--dry-run]
                             indexa turnos observados en skopos.turnos,
                             sin llamar al modelo (P-004)
  search <texto> [--proyecto P] [--cli C] [--max N] [--tope-texto B]
                             busca en los turnos observados; sirve texto
                             redactado y acotado (ADR-009 P3+P5)

Alias heredados, vigentes: reanalizar, indexar, buscar (ADR-016).

`skopos <comando> --help` muestra los argumentos de cada uno."""


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(_AYUDA)
        return 0
    if argv[0] in ALIAS_HEREDADOS:
        print(f"nota: `{argv[0]}` es alias heredado de "
              f"`{ALIAS_HEREDADOS[argv[0]]}` (ADR-016)", file=sys.stderr)
    comando = COMANDOS.get(argv[0])
    if comando is None:
        print(f"comando desconocido: {argv[0]}\n\n{_AYUDA}", file=sys.stderr)
        return 1
    return comando(argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
