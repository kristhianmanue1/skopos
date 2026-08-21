# ADR-010: contrato de parser por CLI (familia multi-CLI)

Estado: **propuesto — decisión 🔒 pendiente del dueño** (Fase 7 / Hito 12;
2026-08-20). Acompañado de la SPEC-006 (docs/specs/f1-specs.md). Sin
código, módulos ni dependencias (stop rules del dueño). Commitear exige
autorización separada.

## Contexto

El dueño decidió (2026-08-20): Skopos será multi-CLI (Claude Code, Kimi
CLI, Qwen CLI y otros). Hoy el parser de Codex es el único y está
incrustado en `captura.py` con `CLI_ORIGEN = "codex-cli"` por constante.
Las precondiciones P-002 (C-9, C-8, C-10, C-6, C-5) están cerradas: el
almacén tiene ejes (`proyecto`, `cli`), superficie de reparación
(supersede, ADR-007), política de arranque (ADR-008), fragmento sellado
(ADR-009) y un corpus piloto real ingestado. Este ADR define la
frontera que convierte el parser de Codex en el primer adaptador de una
familia: **detectar formato → seleccionar parser → producir turnos
normalizados** (SPEC-006).

## 1. Las cinco versiones (resueltas expresamente)

| Concepto | Qué es | Ejemplo | Quién lo define |
|---|---|---|---|
| `cli_producto` | El producto CLI observado — clave del eje `cli` y del nombre que usa escrubery | `codex-cli`, `claude-code`, `kimi-code` | El adaptador (constante declarada) |
| `version_cli` | Versión del binario CLI que escribió el archivo | `codex-cli 0.2.3` (si el rollout la declara) | El rollout (capturada si existe; puede faltar) |
| `version_formato` | Versión del ESQUEMA del archivo de rollout, inferida de marcas estructurales | `codex-rollout/v1` | La detección (marcas declaradas por el adaptador) |
| `version_contrato` | Versión de ESTE contrato de parser | `parser-contrato/v1` | Este ADR + SPEC-006 |
| `version_parser` | Versión de la implementación del adaptador | `parser-codex/v1` | El adaptador (registro, §8) |

Ninguna se mezcla: la selección usa `version_formato` (local, por
marcas); escrubery puede aportar `cli_producto`+`version_cli` vigentes
sólo como referencia de obsolescencia (§9); `version_contrato` gobierna
la forma del Turno normalizado; `version_parser` gobierna el registro y
el retiro (§8). El formato de los rollouts es externo y no versionado
por Skopos (CONTRATO rollout-jsonl-de-codex v1): la inferencia es
conservadora — sólo se declaran versiones cuyas marcas explícitas se
reconocen; todo lo demás es `version_no_soportada`, nunca "parecido
suficiente".

**Definición operativa de "marca declarada"** (ronda 10, H-1): una marca
es un predicado verificable sobre el contenido del archivo — presencia
de un tipo de evento/campo con forma concreta (ej. Codex v1: línea JSON
con `type == "session_meta"` Y, en el mismo archivo, eventos
`type ∈ {"turn_context","response_item","event_msg"}`). Cada ficha
declara: (i) su **marca de identidad** (la que distingue al CLI de
cualquier otro), (ii) las **marcas de estructura** que reconocen la
versión, y (iii) el **alcance del escaneo** (para Codex v1: el archivo
completo de encabezado — `session_meta` está en las primeras líneas;
las marcas de estructura pueden aparecer en cualquier posición). La
detección exige: identidad presente Y todas las marcas de estructura
declaradas; identidad presente Y estructura incompleta ⇒
`version_no_soportada`; identidad ausente ⇒ `formato_desconocido`;
identidad de ≥2 parsers ⇒ `deteccion_ambigua`. Cada ficha justifica sus
marcas con evidencia (muestreo de archivos reales, fechado — mismo
estándar que §2).

**Destino de `version_cli`** (ronda 10, H-4): en v1 de este contrato no
se persiste — no forma parte del `Turno` ni del documento
(documento-analisis-mongo v2 intacto). Vive, cuando el rollout la
declara, como referencia de la ficha/escrubery para avisos de
obsolescencia. Persistirla exigiría una enmienda explícita futura, no
un cambio silencioso aquí.

## 2. Fuente y procedencia de `cli` y `proyecto` por CLI

Cada adaptador declara en su **ficha de adaptador** (parte de su SPEC,
obligatoria para aprobarse):

- `cli`: constante del adaptador (= `cli_producto`, nombre escrubery).
  Nunca se infiere del contenido del archivo.
- `proyecto`: el evento/campo equivalente al `turn_context.cwd` de
  Codex, **con su regla de derivación y un muestreo de evidencia
  fechado** (el estándar que C-9/H5 fijó: muestreo del corpus real
  antes de codificar; valor sin significado ⇒ campo ausente). Si el CLI
  no expone nada equivalente, la ficha lo declara: `proyecto` siempre
  ausente para ese CLI — nunca se inventa ni se deduce de la ruta del
  archivo (que no es identidad de proyecto).

Referencia (Codex): `cli=codex-cli` por constante; `proyecto` de
`turn_context.cwd`, regla ≥2 niveles bajo `$HOME`
(docs/evidencia/muestreo-cwd-c9-2026-08-20.md).

## 3. Comportamiento ante lo inesperado — vocabulario cerrado

Diagnóstico por archivo (la lista es la totalidad; agregar uno exige
v2 del contrato):

| Diagnóstico | Cuándo | Acción |
|---|---|---|
| `ok` | Formato detectado y parseado (con o sin turnos cerrados) | Turnos normalizados |
| `formato_desconocido` | Ninguna marca de ningún parser casa | Descartar el archivo, contabilizar |
| `version_no_soportada` | Marca de identidad del CLI presente, estructuras no declaradas | Descartar, contabilizar (nunca parseo parcial) |
| `entrada_corrupta` | IO/decodificación imposible a nivel archivo | Descartar, contabilizar (la línea corrupta **dentro** de archivo válido sigue siendo descarte de línea contable, como SPEC-001) |
| `deteccion_ambigua` | Marcas de ≥2 parsers casan | Descartar, contabilizar — nunca "probar ambos" |

Observabilidad: todo descarte es contabilizable y atribuible a su
diagnóstico — un descarte sin diagnóstico es un bug de contrato. La
**superficie exacta** de los conteos (resumen por ciclo del vigilante u
otra salida) se define en el plan de implementación; esta cláusula fija
el requisito, no la forma (ronda 10, H-3).

**Detalles de diagnóstico**: un diagnóstico puede llevar metadato
explicativo (ej. `version_no_soportada` con detalle `parser_retirado`).
Los detalles no son diagnósticos: no amplían el vocabulario y no
exigen v2 (gobernados por la ficha que los emite).

## 4. Prohibición de fallback silencioso al parser Codex

La selección es por detección, no por orden ni por defecto. Si el
formato detectado no tiene parser, el diagnóstico es
`formato_desconocido`/`version_no_soportada` — **jamás** "intentar con
el de Codex por si acaso". Razón: un parser equivocado produce turnos
con texto cruzado, IDs falsos y sellos sobre rangos que no son turnos;
con el store primer-análisis-gana (sólo reparable por supersede
explícito), el fallback silencioso es la forma más barata de
contaminar la memoria multi-CLI. Prohibición de contrato, testeable.

## 5. Conservación de offsets, ruta, fragmento y sello

El Turno normalizado conserva EXACTAMENTE los campos actuales
(`turn_id`, `session_id`, `texto_usuario`, `texto_agente`,
`timestamp_cierre`, `ruta_origen`, `offset_inicio`, `offset_fin`,
`cli`, `proyecto`, `fragmento_sha256`). El fragmento y su sello se
computan sobre los **bytes crudos del archivo original** (P4a,
ADR-009): la normalización nunca re-serializa el origen. Invariante:
todo turno normalizado es resoluble a bytes sellados de su archivo
original, sea cual sea el CLI.

## 6. Normalización de roles sin convertir contenido en autoridad

El adaptador mapea los roles de su formato a `texto_usuario`/
`texto_agente` y declara qué roles excluye del texto conversacional
(Codex excluye `developer` — decisión de ficha, no del contrato). Los
textos normalizados son **DATO**: nada del contenido —ni instrucciones
del "usuario",ni contenido recuperado de herramientas— adquiere
autoridad sobre Skopos por haber sido normalizado (mismo principio que
SPEC-002 para el prompt y ADR-009 P3 para el fragmento). La
normalización no interpreta ni ejecuta contenido.

## 7. Idempotencia e identidad estable del turno

- **Idempotencia**: extraer turnos es función pura del mismo archivo
  (misma ruta, mismas bytes) ⇒ mismos turnos, mismos IDs, mismos
  sellos (verificable; el sello determinista lo hace auditable). La
  re-lectura produce `turn_id`s idénticos y la dedup en Mongo (ADR-005)
  los omite.
- **Identidad**: cada adaptador declara su estrategia: (a) **id crudo**
  si el formato garantiza unicidad global (Codex: UUIDv7 — verificado
  empíricamente contra el corpus, ronda 10; los 6 documentos del piloto
  siguen válidos sin cambio), o (b) **id calificado**
  (`{cli_producto}:{id_bruto}`) si el formato puede colisionar entre
  CLIs. La ficha **justifica su estrategia con evidencia** (muestreo
  de ids reales del corpus de ese CLI, fechado — misma vara que §2 para
  `proyecto`; ronda 10, H-5). **Canario de colisión**: si un
  `turn_id` a guardar ya existe en Mongo con `cli` distinto, eso es un
  defecto de ficha y se reporta como señal explícita — nunca
  `omitido` en silencio (el principio de este contrato: nada baja en
  silencio). El índice único `(turn_id, version)` (ADR-007) NO cambia:
  la calificación, cuando hace falta, la hace el adaptador al producir
  el Turno. Alternativa considerada y descartada: identidad compuesta
  `(cli, turn_id)` en el store — exigiría enmienda v3 del CONTRATO
  documento-analisis-mongo y tocaría datos existentes (stop rule del
  dueño); la calificación por adaptador logra lo mismo sin migración.

## 8. Compatibilidad aditiva y política de retiro de parsers

- **Agregar** un parser es aditivo: nueva ficha de adaptador + registro
  (tabla inferior). Ningún parser existente cambia.
- **Retirar** un parser exige ADR propio (fecha, motivo, sustituto si
  lo hay): el parser deja de seleccionarse pero su **marca de identidad
  permanece registrada como stub** del parser retirado — así sus
  archivos siguen diagnosticándose `version_no_soportada` (detalle
  `parser_retirado`) en vez de degradar a `formato_desconocido`
  (ronda 10, H-6). Los documentos ya guardados **no se tocan**: la
  memoria persiste aunque el parser muera (insert-only + versiones
  ADR-007; el fragmento vive en el archivo original).
- Nunca hay borrado silencioso del registro: la tabla conserva a los
  retirados con su estado.

**Registro de adaptadores (v1 del contrato, documental):**

| parser | cli_producto | version_parser | formato declarado | identidad | estado |
|---|---|---|---|---|---|
| parser-codex (referencia) | codex-cli | v1 (prevista) | codex-rollout/v1 | id crudo (UUIDv7, verificado ronda 10) | **ficha incluida abajo; implementación de detección pendiente del plan de fase** |

**Ficha del adaptador de referencia (parser-codex v1, documental):**
`cli = "codex-cli"` (constante). `proyecto`: de `turn_context.cwd`,
regla ≥2 niveles bajo `$HOME`, valor sin significado ⇒ ausente
(evidencia: `docs/evidencia/muestreo-cwd-c9-2026-08-20.md`). Marca de
identidad: evento `type == "session_meta"` en el encabezado. Marcas de
estructura: eventos `type ∈ {"turn_context","response_item","event_msg"}`
con cierre por `event_msg.payload.type == "task_complete"`. Alcance del
escaneo: `session_meta` en las primeras líneas; estructura en cualquier
posición. Identidad: id crudo (UUIDv7; evidencia de muestreo de la
ronda 10, contra el corpus real). Roles excluidos del texto
conversacional: `developer`. Estado actual de la implementación: el
parser existe (`captura.py`, SPEC-001); la **detección por marcas aún
no** — hoy se parsea incondicionalmente lo que se le da; el plan de
implementación de este contrato añade la detección y el vocabulario de
diagnósticos (ronda 10, H-2: el estado "previsto" es honesto hasta
entonces).

## 9. Relación con escrubery (blanda, como ADR-004)

Escrubery puede aportar: descubrimiento de CLIs (`listar`), y la ficha
versionada del CLI (`cli_producto`, `version_cli` vigentes,
procedencia) — insumo para **avisos de obsolescencia** ("el CLI cambió;
revisa el parser"). No participa en la ruta crítica: la detección de
formato es local por marcas; sin escrubery, o con ficha ausente, los
parsers soportados funcionan igual (canal ensayado y tolerado:
docs/evidencia/ensayo-escrubery-2026-08-20.md). **Dependencia blanda**
— su ausencia o fallo jamás rompe captura soportada.

## 10. Qué NO cambia (stop rules verificados)

- Ningún contrato F1 vigente se modifica: documento-analisis-mongo v2,
  cli-skopos-query v1, cli-skopos-reanalizar v1, rollout-jsonl-de-codex
  v1, SPEC-001..005 quedan intactos (SPEC-006 es nueva frontera, no
  enmienda). La implementación futura del contrato podrá refactorizar
  `captura.py` en familia de adaptadores sin tocar los contratos de
  datos.
- **Reconciliación de modos de fallo** (ronda 10, H-7): la cláusula de
  Compatibilidad del CONTRATO rollout-jsonl-de-codex v1 promete que un
  cambio de Codex que rompa el parseo "se detecta como fallo de
  extracción (SPEC-001)". Bajo este contrato, ese mismo evento se
  manifiesta ANTES, en la detección, como `version_no_soportada` (y si
  se llega a parsear, como el fallo de extracción de siempre). No es
  contradicción: la detección añade una barrera previa; el contrato v1
  describe al parser una vez seleccionado, y no se edita.
- **Descubrimiento multi-CLI** (ronda 10, H-9): qué directorios vigilar
  por CLI queda explícitamente diferido al plan de implementación — la
  frontera SPEC-006 es por archivo y compone con cualquier discovery.
- Sin dependencias nuevas, sin migración de datos, sin código en este
  acto.

## Consecuencias (si se acepta)

- (+) La vía multi-CLI queda especificada con el vocabulario cerrado y
  sin fallback; Codex queda como adaptador de referencia.
- (−) Cada CLI nuevo exige ficha de adaptador con evidencia de
  muestreo para `proyecto` — más ceremonia por CLI, a cambio de no
  reproducir la trampa C-9/H5 por familia.
- (−) La detección por marcas requiere mantenimiento declarativo
  (marcas de v2 cuando los CLIs evolucionen) — el costo de no tener
  fallback silencioso.
- Implementación: futura, gated a esta 🔒, con su propio plan de fase.

## Firma de decisión

- Dueño: ______ · Fecha: ______ · (a firma tras revisión del dueño)
