# CLI de Skopos — referencia operativa

Contrastada con `--help` y parsers el 2026-10-06; comando `custody` añadido
en laboratorio el 2026-10-08. Invocación instalable:
`python3 -m skopos`; desde este checkout usar `.venv/bin/python -m skopos`.
No se declara un ejecutable de consola `skopos` en pyproject.toml.
Los esquemas abreviados de contratos usan ese nombre como notación.
La ayuda no inicia servicios ni conecta a Mongo. No ejecutar ejemplos con
marcadores sin sustituirlos por recursos y decisiones autorizados.

## Elegir la frontera correcta

| Comando | Datos y efectos | Servicios |
|---|---|---|
| `index` | Escribe turnos observados; no interpreta | Mongo; sin LLM |
| `search` | Lee índice legado; texto redactado/acotado, sin verificar original | Mongo; sin LLM |
| `query` | Lee análisis; evidencia de origen cuando procede | Mongo; sin nueva llamada LLM |
| `analyze` | Crea análisis faltantes de turnos indexados | Mongo y proveedor configurado |
| `reanalyze` | Crea nueva versión explícita del análisis | Mongo; proveedor salvo `--solo-redaccion` |
| `watch` | Vigila, indexa y normalmente analiza turnos | Mongo; proveedor salvo `--solo-indice` |
| `source import` | Admite fuente/revisión v3 manualmente | Mongo replica set; sin LLM |
| `source search/fetch/fetch-runtime/receipt` | Lecturas v3 explícitas | Mongo; sin LLM |
| `custody` | Custodia mecánica PDF experimental bajo política del host | Mongo para admitir/recuperar; sin LLM |
| `custody-host serve/request` | Canal PDF con configuración de host fija y material exacto | Mongo dedicado para admisión/recuperación; sin LLM |
| `document-host serve/request` | Derivados PDF locales con política separada | Mongo dedicado y original v0.2 verificable; sin LLM |

`source` exige `--database`; URI predeterminada localhost:27017. No usar ese
default por comodidad en el perfil dedicado autenticado. El índice legado y
fuentes v3 no son intercambiables. `project_id` es selector, no autorización.
Nada en estos ejemplos autoriza exposición de red, envío remoto o reanálisis.
`custody` conserva el esquema de laboratorio. `custody-host` admitió el PDF
IMSS sólo en un piloto local monousuario con política y base dedicadas;
ver [evidencia bilateral](evidencia/pdf-custody-imss-pilot-2026-10-08.md).
El [procedimiento del piloto bajo demanda](evidencia/pdf-custody-pilot-operations-2026-10-08.md)
documenta `preflight/start/status/smoke/stop` sobre esa base dedicada.
La [guía de derivados PDF](evidencia/pdf-document-pilot-operations-2026-10-08.md)
encadena host y cliente con parada controlada al salir o recibir INT/TERM.
La CLI directa no es frontera para un agente con shell y credenciales.

## Turnos y análisis: opciones reales

- `query TEMA`: `--proyecto`, `--max`, `--no-evidence`, `--expand-accents`.
  `--no-evidence` evita releer/verificar el original; no valida su disponibilidad.
- `search TEXTO`: `--proyecto`, `--cli`, `--max`, `--tope-texto`,
  `--expand-accents`. Para frase exacta enviar comillas como parte del término:
  `python3 -m skopos search '"lectura incremental"'`.
- `index [RUTAS...]`: `--patron`, `--limite`, `--dry-run`.
  El límite es de archivos, no de turnos. Por defecto usa sesiones Codex;
  para otras fuentes, indicar rutas compatibles: no inferir escaneo universal.
- `analyze`: `--project`, `--cli`, `--anchor`, `--since`, `--until`,
  `--limit`, `--pause`, `--dry-run`. Dry-run consulta Mongo y estima sin LLM;
  su estimación histórica no es garantía de coste o duración.
- `reanalyze TURN_ID`: `--solo-redaccion` evita llamar al proveedor;
  sigue siendo una operación de escritura, no una consulta.
- `watch`: `--sessions-dir [DIR ...]`, `--intervalo`, `--solo-indice`,
  `--sin-indice`, `--backfill`. Sin backfill procesa desde el arranque;
  sus defaults cubren directorios de adaptadores registrados. `--sin-indice`
  no significa modo lectura: puede analizar y persistir análisis.

Alias compatibles: `buscar`, `indexar`, `reanalizar`. La ayuda de sus nombres
ingleses conserva el `prog` histórico español. Los flags no son uniformes:
`--proyecto` en query/search frente a `--project` en analyze y `--project-id`
en source. No renombrarlos en scripts suponiendo equivalencia.
`--expand-accents` es opt-in y acotado a palabras simples terminadas en `-cion`;
no es normalización española general, cambio de índice ni aceptación ADR-019.

## Fuentes v3: sintaxis y selectores

Opciones globales **antes** del subcomando:

```text
python3 -m skopos source --database DB --uri URI import PATH \
  --format FORMATO --project-id P --source-id S --revision N \
  --captured-at ISO_8601
```

Formatos: `diarized-text` (default), `whisperx-json`, `dsh-session-v0-jsonl`.
No autodetecta formatos, no importa ZIP ni directorios. Revisión inicial 1;
siguientes consecutivas con `--expected-previous-sha256 HASH` de la cabeza.
`--completeness unknown|partial|complete` y `--completeness-basis TEXTO`
declaran captura según contrato; hash no demuestra completitud ni veracidad.
El original debe permanecer accesible en custodia; Mongo no contiene una copia
íntegra recuperable de todos sus bytes.

```text
python3 -m skopos source --database DB --uri URI search TEXTO \
  --project-id P --kind runtime-events --limit 20
python3 -m skopos source --database DB --uri URI receipt \
  --project-id P --source-id S --revision N --source-sha256 HASH \
  --kind runtime-events
python3 -m skopos source --database DB --uri URI fetch-runtime \
  --project-id P --source-id S --revision N --source-sha256 HASH \
  --view text_projection --text-id ID
```

`search`/`receipt` usan `meeting-transcript` por defecto; para runtime es
obligatorio escoger `--kind runtime-events`. `source search` sólo busca
subcadenas en cabezas verificadas; no comparte ranking `$text` con `search`.
`--limit` admite 0–20, limita resultados, no fuentes escaneadas ni latencia.
Leer también `unavailable_sources` y `excluded`: vacío no demuestra inexistencia.

| Lectura | Selector |
|---|---|
| `fetch` de transcripción | `--segment-id ID` |
| `fetch-runtime --view text_projection` | `--text-id ID` |
| `fetch-runtime --view original_jsonl` | `--row-id ID` |
| `fetch-runtime --view derived_event` | `--event-id ID` |

Todas exigen proyecto, fuente, revisión y hash. Sólo un selector coherente con
la vista; no mezclar flags. `receipt` no relee el original: reconcilia admisión,
no acredita disponibilidad actual. Las vistas crudas verificadas **no están
redactadas**. No introducir URI con credenciales en argumentos ni ejemplos:
en el perfil operativo usar el lanzador privado que obtiene claves de Llavero.

## Perfil operativo local, no instalación universal

Sólo para el perfil ya configurado en este Mac, desde la raíz del checkout:

```bash
.venv/bin/python /Users/krisnova/Skopos-private/runtime-v3/operate.py status
.venv/bin/python /Users/krisnova/Skopos-private/runtime-v3/operate.py source --help
```

El lanzador fija base/URI y obtiene credenciales sin exponerlas en argv; no
acepta otra base/URI. Usarlo para ingestas operativas mantiene el bloqueo y el
respaldo post-ingesta. Invocar la CLI genérica directamente no incorpora esa
coordinación. `operate.py` no forma parte del paquete distribuido: rutas,
configuración, backend fijado y claves requieren preparación propia.
No ejecutar start/stop ni cambiar Mongo legado por seguir una guía de ayuda.

Mantenimiento autorizado: `scripts/runtime_operations.py backup [--if-changed]`
y `restore-latest`, ejecutados con la venv. Backup detiene brevemente el Mongo
dedicado; restore usa copia aislada. Son scripts del perfil local, no subcomandos
de `python3 -m skopos`. Requisitos, periodicidad provisional, reversión y límites:
[mantenimiento](evidencia/h252-mantenimiento-2026-10-06.md).

## Salidas y resultado incierto

`source`: JSON en stdout al completar, errores en stderr. Exit 0 indica que la
operación devolvió una respuesta; no equivale siempre a admisión: `receipt`
puede devolver `not_found`. Exit 1 es fallo operacional; argparse usa exit 2
para argumentos inválidos. La pérdida de comunicación puede ocurrir después
del commit: consultar receipt con la misma identidad antes de repetir o subir
revisión. No interpretar un timeout como rollback demostrado.
El lanzador privado devuelve 3 si import fue aceptado y el respaldo posterior
falló: la fuente no debe considerarse rechazada. Estos códigos no se extrapolan
automáticamente a otros comandos.

## Verificación y pendientes

Ayudas contrastadas sin ejecutar ingestas. Las pruebas con estado deben usar
Mongo temporal exclusivo: [README](../README.md#pruebas). No cuentan como prueba
de operación multiusuario ni de independencia del programador vigente.
No existen comandos `read`, borrado/retención o embeddings en esta CLI.
No activar automatizaciones ni instalar dependencias por leer esta referencia.
