# Evidencia F1 · muestreo de cwd/workspace_roots para C-9

Snapshot: **2026-08-20** (regla X-2: estado fechado, no propiedad del
repo).
Corpus: 611 archivos `rollout-*.jsonl` en `~/.codex/sessions/`,
16,323 eventos `turn_context`.

## Datos

- `cwd` distinto de `workspace_roots` distinto: 44 / 100.
- `cwd == workspace_roots[0]` en 16,243/16,323 (**99.5%**); `cwd ∈
  workspace_roots` en 16,315/16,323 (**100.0%** con 8 excepciones).
- Top `cwd`: proyectos reales y estables (`entiendomidiabetes` 7338,
  `adrc-python` 2917, `cepiMedica` 1818, `aria/epistates` 1173,
  `an-kla-memory` 591, …).
- `workspace_roots` arrastra directorios de visualización de Codex
  (`~/.codex/visualizations/…`) como elementos extra en la mayoría de
  los casos — **contaminación**: no es fuente confiable de identidad de
  proyecto.
- `cwd` genérico (`/Users/krisnova/www`, no identifica proyecto):
  **4/16,323 (~0.02%)**.
- 0 turnos sin `turn_context` medibles aquí (los archivos sin ningún
  `turn_context` no aportan turnos cerrados en la práctica; el caso se
  cubre por diseño: campo ausente).

## Regla de derivación adoptada (Fase 1 / C-9, corrección H5)

> `proyecto = basename(normalize(cwd))` si y sólo si `cwd` tiene **al
> menos dos niveles bajo `$HOME`** (`$HOME/<a>/<b>…`, es decir, un
> subdirectorio de trabajo, no `$HOME` mismo ni un directorio
> intermedio de primer nivel tipo `~/www` o `~/Documents`) y el
> `basename` resultante no es `.`/`..`; en cualquier otro caso (cwd
> ausente, `$HOME`, un nivel bajo `$HOME`, fuera de `$HOME`, basename
> degenerado), el campo `proyecto` queda **ausente** — nunca un valor
> presente sin significado. Un `turn_context` que no deriva proyecto
> resetea el valor vigente (no se hereda entre turnos).

Justificación contra el muestreo:

- `basename(cwd)` discrimina proyectos reales en el 99.98% del corpus.
- Excluir ≤1 nivel bajo `$HOME` elimina el caso medido de valor sin
  significado (`/Users/krisnova/www` → 4 casos) sin coste apreciable.
- Se usa `cwd`, no `workspace_roots`: éste último contiene rutas de
  visualización ajenas al proyecto (contaminación medida arriba) y su
  primer elemento coincide con `cwd` en el 99.5% — `cwd` es la fuente
  mínima suficiente.
- Colisiones de `basename` entre rutas distintas (p.ej. `realtime-voice-chat`
  en dos fechas de `~/Documents/Codex/…`, 43+24 casos): aceptadas por
  ahora — el eje es filtro de búsqueda, no identidad canónica; si el uso
  real exige discriminación, la v2 del campo agregará la ruta completa y
  este documento lo registrará.
