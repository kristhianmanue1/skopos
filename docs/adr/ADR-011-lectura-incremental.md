# ADR-011: lectura incremental con cursor como caché verificable

Estado: **propuesto** — pendiente de decisión 🔒 del dueño. Cierra
C-10(b) de P-002 §3.3 / Hito 15 si se acepta. No revierte ADR-005: lo
extiende por el camino que el propio ADR-005 pre-registró ("si el
volumen… ese es un ADR nuevo sobre lectura incremental").

## Contexto

El vigilante relee **el corpus completo en cada barrido**. Con el
snapshot del 2026-08-28: 643 archivos, 2.42 GB, y un ciclo de parseo de
**22.6–39.1 s** contra un intervalo por defecto de **5 s** — entre 5× y
8× por encima, con el load registrado al lado
(`docs/evidencia/remedicion-ciclo-c10-2026-08-28.md`). El gate que el
plan exigía para abrir este ADR está cumplido.

Lo que decide el diseño es **dónde se va ese tiempo**, medido en la
misma corrida: leer los 2.42 GB cuesta 5.0 s; leer y sellar el prefijo
completo, 7.0 s; **parsear el JSON, 22.6–39.1 s**. El cuello no es el
disco: es volver a interpretar líneas ya interpretadas.

Y el problema no se arregla solo: el trabajo por ciclo escala con el
**tamaño del corpus**, no con lo nuevo. Cada sesión archivada lo empeora.

**Restricción heredada (ADR-010 §5):** está *prohibido* volver a
`tamaño+mtime` como comparación entre dos lecturas. El cursor tiene que
verificarse con contenido, o declarar qué garantía sacrifica.

## Decisión propuesta

Un **cursor por archivo** que es explícitamente una **caché
inofensiva**, no una fuente de verdad:

- **Qué guarda**, por ruta: `offset_procesado` (byte offset hasta donde
  se extrajeron turnos) y `digest_prefijo` (`sha256` de
  `bytes[0:offset_procesado]`).
- **Cómo se usa**, dentro del protocolo de instantánea vigente: se
  materializa la instantánea (una apertura, `fstat`, N bytes). Si
  `N >= offset_procesado` **y** el `sha256` del prefijo coincide con
  `digest_prefijo`, se parsea **sólo** `bytes[offset_procesado:N]` y los
  offsets de los turnos nuevos se calculan sobre la instantánea
  completa, sin cambiar su semántica. Si no coincide —rotación, edición,
  truncación, archivo sustituido— **se descarta el cursor y se reparsea
  el archivo entero**. La discrepancia es observable, no silenciosa.
- **Qué NO cambia:** la dedup autoritativa sigue en Mongo (ADR-005); el
  sello P4a sigue computándose sobre la instantánea (ADR-009); los
  diagnósticos y la selección de parser siguen siendo los de SPEC-006;
  la política de arranque sigue siendo la de ADR-008.
- **Peor caso de desincronización: reprocesar de más**, que la dedup
  absorbe. El cursor nunca puede *saltarse* contenido sin que el digest
  falle, y no puede aprobar un archivo que cambió por debajo.

Precio medido: la validación cuesta ~7.0 s por barrido completo (leer +
sellar), contra los 22.6–39.1 s de reparsear. El ahorro real es el
parseo de todo lo ya visto.

## Alternativas consideradas

- **(A) Ventana acotada (`sha256` de los últimos 64 KiB antes del
  cursor)** — cuesta 0.21 s en vez de 7.0 s, pero sólo prueba que *ese
  tramo* no cambió: una edición anterior al tramo pasa inadvertida y
  produciría offsets y sellos sobre bytes que ya no son los que se
  analizaron. Se descarta como **default**; queda registrada por si el
  coste de validación llegara a dominar en un corpus mucho mayor, y
  entonces exigiría su propio ADR declarando la garantía que suelta.
- **(B) `tamaño+mtime`** — más barato aún, **prohibido por ADR-010 §5**.
  No se propone.
- **(C) Sin cursor, subiendo el intervalo** — no resuelve nada: el
  trabajo por ciclo sigue escalando con el corpus, y sólo desplaza el
  problema mientras degrada la latencia de detección, que es el REQ-1.
- **(D) Cursor persistido en Mongo en vez de local** — acopla el
  descubrimiento a la disponibilidad de Mongo para una estructura que es
  una caché desechable. Un archivo local perdido sólo cuesta un ciclo
  caro; una dependencia de red añadida en el descubrimiento cuesta
  robustez.

## Consecuencias (si se acepta)

- El ciclo pasa de reparsear 2.42 GB a leer y sellar 2.42 GB más parsear
  únicamente la cola nueva — con los números de hoy, de 22.6–39.1 s a
  ~7 s de piso, y bajando en proporción según crezca la parte estable
  del corpus.
- Aparece **estado local** que antes no existía. Debe vivir fuera del
  repo (gitignorado), ser borrable sin consecuencias y regenerarse solo.
  Un cursor ausente = un ciclo caro, nunca datos perdidos.
- La fase B de P-003 (adaptadores nuevos) hereda este protocolo de
  lectura ya decidido, en vez de que cada adaptador improvise el suyo o
  haya que reescribir cuatro después.
- La implementación exige tests propios: cursor válido, digest que no
  casa (reparseo completo), archivo truncado por debajo del cursor,
  archivo rotado con el mismo tamaño, y cursor ausente.

## Lo que este ADR NO decide

No decide el backfill del histórico (C-10(c), pilotos medidos por
separado) ni toca el timeout de análisis de 120 s que el plan dejó
marcado como marginal antes de cualquier piloto.

## Firma de decisión

- Dueño: **pendiente**. Este documento es una propuesta con evidencia
  fechada; no se implementa nada hasta la 🔒.
