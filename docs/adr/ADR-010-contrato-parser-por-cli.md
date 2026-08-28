# ADR-010: contrato de parser por CLI (familia multi-CLI)

Estado: **aceptado** — decisión 🔒 del dueño, **2026-08-21** (Fase 7 /
Hito 12), tras rondas adversariales 10–17 (actas en `docs/rondas/`;
ronda 17 = gate final, PROCEED) y revisiones de Pinax incorporadas
(11/11b/11c, 13, F1/F2). Acompañado de la SPEC-006 aceptada
(docs/specs/f1-specs.md). Sin código, módulos ni dependencias (stop
rules del dueño); la implementación futura exige autorización y plan
de fase propios. Commitear exige autorización separada.

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
conservadora — sólo se declara la versión cuyas marcas explícitas se
reconocen, y nada se parsea "por parecido"; todo lo demás se
diagnostica por la regla de decisión de esta sección (ronda 11b,
corrección 3 de Pinax: la frase anterior "todo lo demás es
`version_no_soportada`" contradecía la propia regla).

**Definición operativa de "marca declarada"** (ronda 10, H-1;
corregido por rondas 11/11b a partir de la revisión de Pinax): una marca
es un predicado verificable sobre la instantánea de bytes del archivo
(§5). Cada ficha declara: (i) su **predicado de identidad** — el que
distingue al CLI, respaldado por **muestras positivas y controles
negativos** de formatos reales, fechados en `docs/evidencia/` (ej.
parser-codex: primer `session_meta` con `payload.originator` que case
`(?i)^codex([ _-]|$)` — frontera de palabra completa, no subcadena;
616/616 positivos, 11/11 controles negativos sobre 2 formatos ajenos,
ver `docs/evidencia/predicado-identidad-codex-2026-08-20.md`;
enum observado: `codex-tui`, `codex_exec`, `Codex Desktop` —
remedición 2026-08-28 sobre 643 archivos: aparece un cuarto valor,
`codex-chrome-extension-sidepanel` (2), que casa por la frontera de
palabra sin cambiar predicado ni resultado, 643/643 positivos
(`docs/evidencia/fase-a-adaptador-codex-2026-08-28.md`); el enum
describe el corpus observado, no forma parte del predicado); (ii) las
**marcas de estructura** — con su **rol declarado por la ficha**
(extracción/cierre o reconocimiento de versión: parser-codex v1
declara el primer rol, ronda 14 R-3); (iii) el **alcance
del escaneo** (dónde se buscan unas y otras). La exclusividad de un
predicado nunca se afirma sin evidencia: si otro CLI apareciera con la
misma marca, el resultado es `deteccion_ambigua` **sólo si ese otro
producto está registrado y su predicado también casa**; un formato no
registrado que imite la identidad es un **límite residual de la
detección heurística** (ronda 13, corrección 1 de Pinax). La frontera
del predicado es cerrada por construcción (`^codex` seguido de fin de
cadena o separador `_`/`-`/espacio): `codexfoo` NO casa; un originator
futuro de Codex casa sólo si respeta la frontera — y si no la respeta,
el archivo cae en `formato_desconocido` (observable, no silencioso), y
la ficha se actualiza con evidencia nueva.

**Selección en dos niveles (ronda 13, corrección 1 de Pinax)** — la
identidad es del PRODUCTO; la versión es del FORMATO; nunca se
evalúan mezcladas:

**Nivel A — producto CLI:**
1. Evaluar los predicados de identidad **agrupados por
   `cli_producto`** (dos versiones del mismo producto no cuentan como
   dos identidades: parser-codex/v1 y parser-codex/v2 comparten
   identidad de producto y deben poder coexistir sin ambigüedad).
2. Cero productos candidatos ⇒ `formato_desconocido`.
3. Más de un `cli_producto` candidato ⇒ `deteccion_ambigua` (de
   producto, `detalle.codigo = identidades_producto_multiples` con
   `candidatos` = ids de ficha).
4. Exactamente uno ⇒ continuar con sus fichas de formato.

**Nivel B — versión de formato (fichas de ese producto):**
1. Evaluar los predicados de versión declarados para ese producto.
2. Una versión reconocida y activa ⇒ seleccionar su parser.
3. Una versión reconocida pero retirada ⇒ `version_no_soportada` con
   `detalle.codigo = parser_retirado`.
4. Más de una versión compatible ⇒ `deteccion_ambigua` (de versión,
   `detalle.codigo = versiones_formato_multiples` — la ambigüedad es
   de versión, no de producto).
5. Marcador positivo incompatible (regla de abajo) ⇒
   `version_no_soportada`.
6. Ausencia de marcador incompatible bajo el **perfil base** ⇒ `ok`.

**Perfil base (ronda 13)**: parser-codex/v1 es hoy el perfil base
compatible del producto codex-cli: la identidad Codex más la ausencia
de una firma incompatible registrada. **No se afirma que
codex-rollout/v1 se infiere de marcas estructurales** — su ficha no
declara ninguna obligatoria; es el perfil por defecto del producto
una vez confirmada la identidad. Cuando exista v2, su firma debe ser
positiva y la ficha v1 debe excluirla de forma explícita (y
viceversa). **Nunca se selecciona por orden del registro.**

La precedencia total entre diagnósticos (§3) gobierna ambos niveles:
lo ilegible primero, luego la ambigüedad (sea de producto o de
versión), luego la ausencia de identidad, luego la incompatibilidad
versionada, y `ok` como complemento.

**Predicados positivos de incompatibilidad** (para Nivel B regla 5;
declarados por la ficha, nunca inferidos de frecuencia — ronda 11c:
la regla genérica "tipo estructural desconocido recurrente ≥N" fue
eliminada por reproduciblemente inválida; el corpus contiene eventos
aditivos no reconocidos — `world_state` 3,540,
`inter_agent_communication_metadata` 1,256, `compacted` 1,016
eventos; 84/616 archivos con ≥10 ocurrencias — en rollouts
perfectamente parseables por parser-codex v1): (i) **marcador
explícito incompatible** — campo de versión del propio formato con
valor superior/superado al declarado; (ii) **firma conocida
mutuamente excluyente** — presencia del marcador estructural de OTRA
versión declarada en la ficha; (iii) **violación de una estructura
obligatoria reconocida** — el formato rompe algo que la ficha declara
obligatorio. Sin predicado positivo, no hay `version_no_soportada`.

**`ok` residual**: en cualquier caso no cubierto por los niveles
anteriores — incluido **un archivo vivo que todavía no contiene las
marcas posteriores** (sesión recién creada) y **archivos con eventos
aditivos desconocidos** — el diagnóstico es **`ok`**, con los turnos
que haya (posiblemente cero); si hubo **cero cierres de turno**,
`detalle.codigo = identidad_reconocida_sin_cierres` (la ausencia de
marcas tardías no es incompatibilidad, pero tampoco éxito opaco: los
conteos del ciclo agregan estos `ok` aparte y su acumulación anómala
es señal).

**Eventos no reconocidos (ronda 11c, corrección 2)**: los eventos de
tipos no declarados por la ficha — válidos como JSON, simplemente no
parte del contrato de extracción — se **ignoran para la extracción**
(no producen texto, turnos ni offsets) pero se **contabilizan
explícitamente** en `ResultadoParseo.eventos_no_reconocidos`
(total por archivo). Bordes (ronda 12, H-4): sólo se cuentan cuando el
archivo llega a parsearse (los descartes por diagnóstico no llevan
conteo — es 0 implícito); un evento JSON válido sin `type` o con
`type` no-string **no** cuenta (se ignora, como el resto de los no
declarados — sin arbitrariedad sobre formas corruptas de campo); una
línea JSON inválida cuenta SOLO en `descartes_linea` (conjuntos
disjuntos por definición). Son la señal primaria de evolución aditiva
del formato: su crecimiento en el corpus es lo que amerita revisar la
ficha y declarar una versión nueva del formato — un acto deliberado,
no un umbral automático.

**Destino de `version_cli`** (ronda 10, H-4): en v1 de este contrato no
se persiste — no forma parte del `Turno` ni del documento
(documento-analisis-mongo v2 intacto). Vive, cuando el rollout la
declara (Codex: `session_meta.payload.cli_version`, verificado en el
corpus — ver evidencia citada), como referencia de la
ficha/escrubery para avisos de obsolescencia. Persistirla exigiría una
enmienda explícita futura, no un cambio silencioso aquí.

## 2. Fuente y procedencia de `cli` y `proyecto` por CLI

Cada adaptador declara en su **ficha de adaptador** (parte de su SPEC,
obligatoria para aprobarse; corrección 4 de Pinax — campos completos):

- `cli`: constante del adaptador (= `cli_producto`, nombre escrubery).
  Nunca se infiere del contenido del archivo.
- `proyecto`: el evento/campo equivalente al `turn_context.cwd` de
  Codex, **con su regla de derivación y un muestreo de evidencia
  fechado** (el estándar que C-9/H5 fijó: muestreo del corpus real
  antes de codificar; valor sin significado ⇒ campo ausente). Si el CLI
  no expone nada equivalente, la ficha lo declara: `proyecto` siempre
  ausente para ese CLI — nunca se inventa ni se deduce de la ruta del
  archivo (que no es identidad de proyecto).
- **fuente/derivación de `session_id`**: qué campo/evento del formato
  lo aporta o cómo se deriva (y si es estable entre re-lecturas).
- **fuente de `turn_id`**: campo/evento exacto que lo aporta, y la
  estrategia de identidad (crudo-excepción o calificada, §7).
- **fuente de `timestamp_cierre`**: campo/evento exacto y su formato
  (incluido qué pasa si ausente — el Turno lo tolera como `None`).
- **predicado de cierre de turno**: la condición exacta que delimita
  un turno cerrado (ej. Codex: `event_msg.payload.type == "task_complete"`).
- **codificación y offsets en bytes**: la codificación del archivo
  (UTF-8 para Codex) y que `offset_inicio`/`offset_fin` son **byte
  offsets** del archivo original — sobre los que se computa el sello
  P4a (§5).
- **estrategia de identidad con su gramática** (§7) y evidencia fechada.

Referencia (Codex): `cli=codex-cli` por constante; `proyecto` de
`turn_context.cwd`, regla ≥2 niveles bajo `$HOME`
(docs/evidencia/muestreo-cwd-c9-2026-08-20.md).

## 3. Vocabulario cerrado de diagnósticos y `ResultadoParseo`

Diagnóstico por archivo (la lista es la totalidad; agregar uno exige v2
del contrato):

| Diagnóstico | Cuándo | Acción |
|---|---|---|
| `ok` | Identidad casa, sin predicado positivo de incompatibilidad — con turnos, o con cero cierres (`detalle.codigo = identidad_reconocida_sin_cierres`, observable aparte); los eventos aditivos no reconocidos no afectan el diagnóstico, sólo se cuentan | Turnos normalizados |
| `formato_desconocido` | Cero productos candidatos (Nivel A regla 2) | Descartar el archivo, contabilizar |
| `version_no_soportada` | Predicado positivo y versionado de la ficha (Nivel B regla 5), o versión reconocida de parser retirado (regla 3) | Descartar, contabilizar (nunca parseo parcial) |
| `entrada_corrupta` | La instantánea no puede materializarse bajo el protocolo §5: IO/decodificación imposible o short read | Descartar, contabilizar (la línea corrupta **dentro** de instantánea válida sigue siendo descarte de línea contable, como SPEC-001) |
| `deteccion_ambigua` | ≥2 productos candidatos (Nivel A regla 3) o ≥2 versiones compatibles (Nivel B regla 4) — `detalle.codigo` distingue cuál | Descartar, contabilizar — nunca "probar ambos" |

**`ResultadoParseo`** (corrección 3 de Pinax): la frontera produce un
objeto estructurado, no una lista suelta:

```text
ResultadoParseo := {
  diagnostico:            uno de los cinco (arriba) — siempre presente
  turnos:                 lista de Turno (vacía salvo en ok)
  cli_producto:           del adaptador seleccionado (None si no hubo)
  version_formato:        la declarada por la ficha (None si no hubo)
  version_cli_observada:  de la instantánea si el formato la declara (None si no)
  detalle:                null | {codigo} | {codigo, candidatos} —
                          unión cerrada (F1):
                           codigo: uno de {
                             identidad_reconocida_sin_cierres,
                             parser_retirado,
                             identidades_producto_multiples,
                             versiones_formato_multiples,
                             lectura_corta
                           },
                           candidatos: lista de ids de ficha —
                           OBLIGATORIA sólo para
                           identidades_producto_multiples y
                           versiones_formato_multiples
                           (lexicográficamente ordenada, sin
                           duplicados, >= 2 ids); PROHIBIDA para
                           identidad_reconocida_sin_cierres,
                           parser_retirado y lectura_corta
                         }
  eventos_no_reconocidos: int ≥ 0 — eventos de tipos no declarados por
                          la ficha (JSON válido), ignorados para la
                          extracción pero contabilizados (ronda 11c):
                          señal de evolución aditiva, nunca incompatibilidad
  descartes_linea:        int ≥ 0 — líneas JSON inválidas dentro de una
                          instantánea válida (observable, como SPEC-001)
}
```

**Forma de `detalle` congelada** (ronda 13, corrección 3 de Pinax;
**unión cerrada por completo en F1**, ronda de cierre): `detalle` es
`null`, o `{codigo}`, o `{codigo, candidatos}` — **nada más**.
`candidatos` es **obligatorio únicamente** para
`identidades_producto_multiples` y `versiones_formato_multiples`, y en
esos casos es una lista lexicográficamente ordenada, **sin
duplicados**, con **al menos 2** ids de ficha; está **prohibido** para
`identidad_reconocida_sin_cierres`, `parser_retirado` y
`lectura_corta`. No se permiten otras claves ni texto libre en ninguna
parte de `detalle`. Agregar un `codigo` exige nueva versión del
contrato. `diagnostico` continúa siendo el vocabulario principal:
`detalle` nunca cambia la precedencia ni reclasifica nada — sólo
explica.

**Precedencia total y testeable** (ronda 11; fija el orden de
evaluación — ningún archivo puede recibir dos diagnósticos):

`entrada_corrupta` > `deteccion_ambigua` > `formato_desconocido` >
`version_no_soportada` > `ok`

Justificación del orden: lo ilegible impide evaluar todo lo demás; la
ambigüedad se decide antes que la ausencia (si dos identidades casan,
no hay "ninguna"); la incompatibilidad requiere identidad previa; `ok`
es el complemento. Cada par (entrada, diagnóstico esperado) es un caso
de test declarable — la precedencia es testeable por construcción.

Observabilidad: todo descarte es contabilizable y atribuible a su
diagnóstico vía `ResultadoParseo` — un descarte sin diagnóstico es un
bug de contrato. La **superficie exacta** de los conteos (resumen por
ciclo del vigilante u otra salida) se define en el plan de
implementación; esta cláusula fija el requisito, no la forma (ronda 10,
H-3). *(El párrafo previo "Detalles de diagnóstico" — que permitía
metadato libre gobernado por la ficha — fue eliminado en la ronda 13,
F-1: contradecía la forma congelada de `detalle` en este mismo §3.)*

## 4. Prohibición de fallback silencioso al parser Codex

La selección es por detección, no por orden ni por defecto. Si el
formato detectado no tiene parser activo, el diagnóstico es
`version_no_soportada` (identidad que casó con ficha retirada —
incluida la forma stub de §8); la ausencia de identidad es
`formato_desconocido`, y ahí no hay nada que fallback-ear. Razón: un
parser equivocado produce turnos con texto cruzado, IDs falsos y
sellos sobre rangos que no son turnos; con el store
primer-análisis-gana (sólo reparable por supersede explícito), el
fallback silencioso es la forma más barata de contaminar la memoria
multi-CLI. Prohibición de contrato, testeable.

## 5. Conservación de offsets, ruta, fragmento, sello — e instantánea

El Turno normalizado conserva EXACTAMENTE los campos actuales
(`turn_id`, `session_id`, `texto_usuario`, `texto_agente`,
`timestamp_cierre`, `ruta_origen`, `offset_inicio`, `offset_fin`,
`cli`, `proyecto`, `fragmento_sha256`). El fragmento y su sello se
computan sobre los **bytes crudos del archivo original** (P4a,
ADR-009): la normalización nunca re-serializa el origen. Invariante:
todo turno normalizado es resoluble a bytes sellados de su archivo
original, sea cual sea el CLI.

**Instantánea materializada única — protocolo de lectura (ronda 11
corrección 5; congelado en ronda 13, corrección 2 de Pinax)**: una
lectura única hasta EOF no siempre distingue un archivo completo de un
prefijo válido observado durante truncamiento o de un archivo vivo que
aún crece — no se promete detectarlo mágicamente. El protocolo
implementable:

1. abrir el archivo **una sola vez**;
2. obtener los N bytes esperados mediante `fstat` **del mismo
   descriptor**;
3. leer exactamente los primeros N bytes **desde ese descriptor**;
4. short read, error de I/O o UTF-8 inválido ⇒ `entrada_corrupta`
   (`detalle.codigo = lectura_corta` cuando aplique);
5. bytes añadidos después de fijar N quedan **fuera de esta
   instantánea** y se observan en el siguiente ciclo (el vigilante
   re-visitará el archivo crecido; la dedup en Mongo — ADR-005 —
   absorbe la re-lectura);
6. detección, parseo, offsets y sello usan **exclusivamente** ese
   buffer.

**Límites declarados**: no es una snapshot atómica general del
filesystem; no detecta necesariamente una reescritura concurrente del
mismo tamaño (mismos N bytes, contenido distinto — residuo aceptado y
observable sólo por el sello en re-lecturas futuras); su garantía es
que **diagnóstico, turnos, offsets y sello corresponden exactamente a
los mismos bytes materializados**. Prohibido volver a tamaño+mtime
como comparación entre dos lecturas (eliminado en 11b, se mantiene
eliminado). Nota de implementación (actualizada 2026-08-28): `captura.py`
leía el archivo dos veces (iteración y sello por rango) — **no
conforme**; la fase A de P-003 (`ee37e28`) lo convirtió a este
protocolo, y el sello se computa sobre la misma instantánea de la que
salen los offsets.

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
  CLIs. **Gramática inequívoca del ID calificado** (corrección 4 de
  Pinax): `id_calificado := cli_producto ":" id_bruto`, donde
  `cli_producto ∈ ^[a-z][a-z0-9-]*$` (vocabulario cerrado alineado con
  escrubery — sin dos puntos por construcción) y `id_bruto` es el string
  crudo del formato, sin escapes: el **primer** dos puntos delimita, y
  como el prefijo jamás contiene uno, el parseo es único y sin
  ambigüedad. **Política de default** (corrección 4): el id crudo es
  una **excepción compatible y probabilística** — sólo se permite con
  la evidencia fechada de la ficha (muestreo de ids reales) y mientras
  ningún contraejemplo la refute; **todo adaptador nuevo usa ID
  calificado por defecto**. La ficha justifica su estrategia con
  evidencia (mismo estándar que §2 para `proyecto`). **Canario de
  colisión**: si un `turn_id` a guardar ya existe en Mongo con `cli`
  distinto, eso es un defecto de ficha y se reporta como señal
  explícita — nunca `omitido` en silencio (el principio de este
  contrato: nada baja en silencio). El índice único `(turn_id,
  version)` (ADR-007) NO cambia: la calificación, cuando hace falta,
  la hace el adaptador al producir el Turno. Alternativa considerada y
  descartada: identidad compuesta `(cli, turn_id)` en el store —
  exigiría enmienda v3 del CONTRATO documento-analisis-mongo y
  tocaría datos existentes (stop rule del dueño); la calificación por
  adaptador logra lo mismo sin migración.

## 8. Compatibilidad aditiva y política de retiro de parsers

- **Agregar** un parser es aditivo: nueva ficha de adaptador + registro
  (tabla inferior). Para un `cli_producto` **nuevo**, ningún parser
  existente cambia. **Precondición de registro** (ronda 13, F-5): si
  existe otra ficha del mismo `cli_producto`, la nueva debe declarar
  exclusión mutua explícita con cada una (firma positiva propia; la
  existente se enmienda para excluirla, con bump de su
  `version_parser`) — sin ella el registro se rechaza y el modo de
  fallo es `versiones_formato_multiples`, nunca contaminación.
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
| parser-codex (referencia) | codex-cli | v1 | codex-rollout/v1 | id crudo (UUIDv7, verificado ronda 10) | **activo — implementado en la fase A de P-003 (`ee37e28`, 2026-08-28): ficha abajo, detección en `src/skopos/parseo.py`, adaptador en `src/skopos/captura.py`; evidencia en `docs/evidencia/fase-a-adaptador-codex-2026-08-28.md`** |

**Ficha del adaptador de referencia (parser-codex v1, documental):**
`cli = "codex-cli"` (constante). `proyecto`: de `turn_context.cwd`,
regla ≥2 niveles bajo `$HOME`, valor sin significado ⇒ ausente
(evidencia: `docs/evidencia/muestreo-cwd-c9-2026-08-20.md`).
**Predicado de identidad**: primer evento `type == "session_meta"`
dentro de las primeras 10 líneas con `payload.originator` que case
`(?i)^codex([ _-]|$)` — muestras positivas 616/616, controles negativos
11/11 sobre 2 formatos ajenos
(`docs/evidencia/predicado-identidad-codex-2026-08-20.md`).
**Marcas de estructura** *(rol: extracción y cierre — **no reconocen
versión**; la versión v1 es perfil base por ausencia de firma
incompatible, no inferida de estas marcas — ronda 13, F-4)*: eventos
`type ∈ {"turn_context",
"response_item","event_msg"}`; cierre por
`event_msg.payload.type == "task_complete"` (predicado de cierre). Un
archivo vivo sin todas las marcas posteriores ⇒ `ok` + cero turnos con
`detalle.codigo = identidad_reconocida_sin_cierres` (§1, ok residual).
**Perfil base (ronda 13)**: parser-codex/v1 es el perfil base
compatible del producto codex-cli — identidad Codex + ausencia de firma
incompatible registrada; la ficha **no declara marcas estructurales
obligatorias** de las que se infiera codex-rollout/v1.
**Predicados positivos de incompatibilidad declarados en v1: ninguno**
(ronda 12, H-3): `session_meta.payload` no declara versión del formato
(verificado — `cli_version` es `version_cli`, no `version_formato`),
no existe firma de otra versión, y v1 no declara estructuras
obligatorias — `version_no_soportada` es **inalcanzable para
parser-codex v1 salvo vía retiro del parser**. Cierre malformado
(`task_complete` sin `payload.turn_id`): se ignora (comportamiento
SPEC-001 vigente), no es violación de estructura — cuando v2 exista y
amerite predicados positivos, se declaran aquí con evidencia y la
ficha v1 la excluye de forma explícita.
**Alcance del escaneo**: identidad en las primeras 10 líneas;
estructura en cualquier posición. **session_id**:
`path.stem` — **decisión de v1 por compatibilidad** (ronda 11b,
corrección 1 de Pinax): los documentos ya guardados (piloto, 6) usan
`path.stem`, y el nombre de archivo de Codex contiene el UUID de
sesión; `payload.session_id` se documenta como dato disponible pero
**no adoptado** — cambiar la fuente exigiría una migración autorizada
explícita, no un cambio de ficha. **turn_id**: `payload.turn_id` del
evento de cierre. **timestamp_cierre**: campo `timestamp` del evento de
cierre (ISO 8601 UTC con `Z`; ausente ⇒ `None`).
**Codificación/offsets**: UTF-8; `offset_inicio`/`offset_fin` son byte
offsets **de la instantánea materializada** (§5; sello P4a sobre
ellos). **Identidad**: id crudo (UUIDv7) como **excepción compatible y
probabilística** — evidencia: verificación empírica de la ronda 10
contra el corpus; revisable a calificada si aparece un
contraejemplo/canario. `version_cli_observada`:
`session_meta.payload.cli_version` (presente en 616/616). Roles
excluidos del texto conversacional: `developer`.
**Estado de la implementación (actualizado 2026-08-28, fase A de P-003
— actualización de estado, no de decisión):** la detección por
predicados, el `ResultadoParseo` y el vocabulario de diagnósticos
existen (`src/skopos/parseo.py`); el adaptador declara su ficha como
constantes (`src/skopos/captura.py`) y la ingesta pasa por la frontera
(`e6d8faf`), de modo que ya no se parsea incondicionalmente lo que se le
da. *(Redacción previa, hasta 2026-08-28: "el parser existe
(`captura.py`, SPEC-001); la detección por predicados aún no" —
ronda 10, H-2, honesta mientras duró.)*

## 9. Relación con escrubery — frontera precisa (corrección 6 de Pinax)

- **`listar` sólo descubre candidatos**: su salida no lleva procedencia
  por elemento y no prueba nada sobre un archivo observado — nunca
  selecciona parser ni autoriza identidad.
- **`ficha` aporta referencia con procedencia y caducidad**: fuente,
  fecha y hash del dato servido (CONTRATO_API_v0 §2.1). Es insumo de
  **referencia** (obsolescencia, `repo_url`, `mecanismo_changelog`), no
  de verdad actual: **un dato caducado no prueba vigencia** — la
  caducidad se declara, no se oculta.
- **Escrubery no selecciona parser** (la selección es local por
  predicados, §1), **no infiere `proyecto`** (la fuente vive en la
  ficha del adaptador, §2) y **nunca bloquea captura ya soportada**
  (sin escrubery, o con ficha ausente, o con fallo del canal, los
  parsers soportados funcionan igual — camino ensayado y tolerado:
  docs/evidencia/ensayo-escrubery-2026-08-20.md).
- **Consulta memoizada por CLI/sesión, no por turno** (hallazgo de la
  Fase 6: ~0.27 s/call; un subprocess por turno acumularía ~1.1 h en un
  backfill de 14,822 turnos para la misma ficha).
- **`cli_producto` es vocabulario interno alineado con escrubery**: los
  nombres coinciden por convenio de consumo (esta autorización del
  dueño, 2026-08-20), pero `cli_producto` **no es identidad canónica**
  — Skopos no adopta la taxonomía de Pinax ni la de escrubery como
  autoridad sobre sus archivos observados; la identidad de un archivo
  la decide el predicado de su ficha, localmente.

**Dependencia blanda** — su ausencia o fallo jamás rompe captura
soportada (ADR-004).

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

- Dueño: decisión 🔒 comunicada en canal del agente, aceptando ADR-010
  y SPEC-006 · Fecha: **2026-08-21** · Acto documental de aceptación
  registrado tras el gate final de la ronda 17 (PROCEED)
