# ADR-011: lectura incremental con cursor como caché verificable

Estado: **aceptado** — decisión 🔒 del dueño, 2026-08-28. Cierra
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

## Cláusulas que la implementación obligó a añadir (ronda 23, 2026-08-28)

Las cuatro salieron de escribir el código y de la ronda adversarial
sobre él; ninguna estaba en el texto aceptado, y sin ellas el cursor
**no** sería la caché inofensiva que este ADR promete. Se incorporan
como parte de la decisión, no como notas al margen.

1. **El cursor nunca adelanta un turno fallido.** Un turno cuyo análisis
   falló no está en Mongo; si el cursor pasara por encima, no se
   volvería a leer **nunca** — la dedup no puede rescatarlo porque nunca
   lo vio. El avance se congela en el primer `fallido` del archivo y se
   reintenta desde ahí en el ciclo siguiente. Los `omitido` (ya
   guardado, sin contenido, duplicado concurrente) sí avanzan: no exigen
   reintento.
2. **El estado que cruza la frontera se hereda explícitamente.**
   `proyecto` viene del último `turn_context` **anterior** al cursor y
   `version_cli_observada` del `session_meta` de cabecera. Sin herencia,
   toda lectura incremental degradaría el eje de proyecto de C-9 a
   `None` en silencio — peor que no tener cursor. La herencia de
   `proyecto` es una búsqueda de bytes hacia atrás, no un reparseo del
   prefijo.
3. **Los conteos pasan a ser de la lectura, no del archivo.**
   `eventos_no_reconocidos` y `descartes_linea` cuentan lo observado en
   **este tramo**. Es una **desviación declarada** de ADR-010 §3, que
   dice "total por archivo": en lectura incremental ese total no se
   puede afirmar sin reparsear todo, que es justo lo que se evita. Se
   prefiere un conteo honesto de lo leído a un total inventado.
4. **El cursor recuerda lectura, no ingesta.** Si se vacía la colección
   de Mongo, los cursores siguen diciendo "ya leído": recuperar el
   histórico exige `--backfill`, que **ignora los cursores** por
   diseño. Un backfill es "reléelo todo", y honrar cursores ahí saltaría
   exactamente lo que se pidió recuperar.

**Un archivo sin turnos cerrados no recibe cursor** (11 de 643 en el
corpus de hoy): avanzar hasta EOF saltaría el texto acumulado que aún no
tiene cierre, y el turno siguiente saldría con el contenido mutilado. El
precio es que esos archivos se reparsean enteros cada ciclo; es
deliberado.

## Consecuencias (si se acepta)

- El ciclo pasa de reparsear 2.42 GB a leer y sellar 2.42 GB más parsear
  únicamente la cola nueva — con los números de hoy, de 22.6–39.1 s a
  ~7 s de piso, y bajando en proporción según crezca la parte estable
  del corpus.
- Aparece **estado local** que antes no existía. Vive fuera del repo —
  `~/.local/state/skopos/cursores.json`, así que no hay ni que
  gitignorarlo—, es borrable sin consecuencias y se regenera solo. Un
  cursor ausente = un ciclo caro, nunca datos perdidos. Se **poda** en
  cada ciclo con los archivos descubiertos: sin eso, cada sesión
  archivada o borrada dejaría su entrada dentro para siempre.
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

- Dueño: decisión 🔒 comunicada en canal del agente · Fecha:
  **2026-08-28** · Sobre la propuesta con la evidencia fechada de
  `docs/evidencia/remedicion-ciclo-c10-2026-08-28.md`.
- **Implementado el mismo día** (`src/skopos/cursor.py`, soporte en
  `parseo.py`/`captura.py`, enrutado en `orquestador.py`/`vigilante.py`),
  con las cuatro cláusulas de arriba incorporadas tras la ronda 23.
  Evidencia y medición: `docs/evidencia/cursor-incremental-2026-08-28.md`.
