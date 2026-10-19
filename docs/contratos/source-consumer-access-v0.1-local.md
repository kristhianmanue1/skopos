# Source consumer access v0.1 — alcance por consumidor en el almacén de fuentes

Estado: contrato nuevo, sin implementar. Es la T1 del
[plan multiproyecto 2026-10-13](../planes/activos/contrato-multiproyecto-2026-10-13.md).
No modifica `source-store-v3.md` ni `ctim-source-access-v0.2-local.md`: cubre
la pila runtime/source —donde el eje proyecto es real, identidad
`(project_id, source_id, source_revision)`—, no la pasarela CTIM, cuya lista
exacta de fuentes con SHA ya es más fina que cualquier eje proyecto.

## Instancia viva que generaliza

Conforme a la regla de ADR-010 —el contrato generaliza una instancia viva, no
la precede—, este documento parte de:

- **Piloto de consulta desde agente** (`experiments/agent-query-pilot/backend.py`):
  cada llamada sujetó su alcance comparando `project_id` contra
  `SKOPOS_PILOT_PROJECT` y rechazando `project_mismatch` (líneas 108–109) —
  instrucción de tarea bajo rúbrica, no frontera del almacén. Consumió por dos
  rutas: subproceso CLI (líneas 88–96) y API Python (`search_verified` /
  `fetch_verified`, líneas 48 y 74).
- **Corridas reales bajo la cuenta del Operador**: consultas de Ágora y de
  evaluación que citaron p18/p21, verificadas en la revisión de fidelidad del
  2026-10-13 (`docs/evidencia/rs1-fidelity-review-2026-10-13.md`).

Lo que se generaliza: el consumidor declara identidad y lista exacta de
proyectos; el almacén pasa de confiar en el filtrado del consumidor a
rechazar por política propia, fail-closed.

## Superficie de servicio declarada (T0)

Operaciones por donde un consumidor obtiene contenido o metadatos de
existencia del almacén de fuentes, con el punto exacto en código:

| Operación | Python (`src/skopos/runtime_store.py`) | CLI (`src/skopos/source_cli.py`) |
|---|---|---|
| search | `RuntimeSourceStore.search` (l. 175) | `search` (l. 33) |
| search runtime | `search_runtime` (l. 178) | `search --kind runtime-events` |
| fetch | `fetch` (l. 142) | `fetch` (l. 37) |
| fetch runtime | `fetch_runtime` (l. 152) | `fetch-runtime` (l. 41) |
| receipt | heredado `SourceStore.receipt` (`src/skopos/source_store.py` l. 156) | `receipt` (l. 39) |

`import` no está en la superficie: la admisión es operación de autoridad del
Operador, no acceso de consumidor. El control vive en un punto único por
encima de estas operaciones —no parcheado una por una—, de modo que las rutas
CLI y API Python quedan cubiertas por igual; el piloto usó ambas.

## Política

`skopos/source-consumer-access-policy/v0.1`: archivo JSON con conjunto exacto
de campos `schema`, `consumer_id`, `mongo_uri`, `database`,
`allowed_projects`.

- `schema`: exactamente ese valor.
- `consumer_id`: cadena de texto con contenido distinto de espacios.
- `mongo_uri`: cadena que casa exactamente con
  `mongodb://127.0.0.1:PUERTO[/resto]` — **un solo host loopback, sin
  lista de seeds (coma) ni parámetro `replicaSet=`**, de modo que el
  descubrimiento de topología no pueda ampliar la conexión fuera de
  127.0.0.1. No se fija puerto: los ensayos de laboratorio del plan usan
  instancias dedicadas efímeras y la política debe poder apuntarlas.
- `database`: cadena de texto con contenido distinto de espacios.
- `allowed_projects`: lista obligatoria de al menos una cadena con
  contenido distinto de espacios, sin repetidos. Lista exacta: sin
  patrones ni comodines.

Carga fail-closed, en carga y no en uso: archivo ausente o ilegible, mayor
de 64 KiB, JSON inválido o con claves duplicadas, conjunto de campos
distinto, o cualquier violación anterior → `policy_unavailable` y nada se
sirve.

## Conducta

Para cada operación de la superficie, antes de cualquier acceso a la base por
ese `project_id`: si no está en `allowed_projects`, se rechaza con
`project_not_allowed`. El rechazo es uniforme —no distingue proyecto
existente de inexistente— y ocurre antes de leer cabezas, colecciones o
archivos, para no servir contenido ni metadatos de existencia del proyecto
ajeno. Incluye `receipt`: el recibo revela existencia (`duplicate` frente a
`not_found`) y queda tras el control.

Cada respuesta servida a través del control declara `access` con
`consumer_id` y `policy_sha256` (SHA-256 del archivo de política): la
auditoría posterior puede saber qué política autorizó cada salida.

## Límites declarados

- Cero promesas de aislamiento multiusuario: perfil local monousuario vigente
  (decisión del Operador 2026-10-06). La política declara alcance, no
  identidad verificada: un proceso con la política puede poner el
  `consumer_id` que quiera.
- `project_id` sigue sin ser credencial (`source-store-v3`). La política no
  cubre `import`, operaciones Mongo directas ni el mantenimiento bajo la
  cuenta del Operador; es la frontera que se ofrece al consumidor, no un
  sandbox contra un proceso local hostil.
- No es autenticación entre agentes: dos agentes con la misma política tienen
  el mismo alcance. El multiusuario futuro exige contrato propio con
  autenticación, auditoría y pruebas negativas (`source-store-v3`, perfil
  operativo).
- No cambia la recuperación: `search` sigue siendo subcadena casefold, sin
  ranking ni semántica; este contrato no añade ninguna.

## Integración CLI

`skopos source --policy RUTA` sustituye a `--database` y `--uri` (combinarlos
es error de uso): el punto y la base salen de la política —el consumidor no
elige a dónde conectarse ni a qué base—, y ahí amarra de verdad la regla
loopback de `mongo_uri`. Bajo política sólo hay lectura: las cinco
operaciones de la superficie; `import` se rechaza con
`operation_not_allowed` antes de conectar y antes de cargar la política,
porque la admisión es autoridad del Operador. La política ausente o
inválida se rechaza en carga (`policy_unavailable`). Sin `--policy`, la CLI
conserva el uso de Operador (admisión y mantenimiento) sin cambios.

## Compatibilidad

Contrato nuevo: no hay políticas previas que romper ni cambios de esquema en
`source-record/v3`. La superficie actual (Operador, sin política) conserva su
uso de mantenimiento y admisión; el control es la ruta nueva para
consumidores, no una migración.
