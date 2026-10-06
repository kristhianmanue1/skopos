# Hoja de ruta

> Hitos reales, con commit de cierre. No es un plan a futuro especulativo:
> los primeros siete ya pasaron y quedan como registro; de ahí en
> adelante son próximos pasos, no promesas de fecha.

| Hito | Qué entrega | Estado | Commit |
|---|---|---|---|
| 0 | F0 — análisis, requisitos, evidencia | Cerrado | `7f032b7` |
| 1 | F1 — specs, ADR, contratos, máquina de estados | Cerrado | `40812c5` |
| 1.1 | REQ-10 — escrubery como fuente opcional | Cerrado | `797aaf1` |
| 2 | F2 — cascarón (captura, sin dependencias nuevas) | Cerrado | `8c14455` |
| 3 | Análisis (Ollama) + almacenamiento (Mongo) | Cerrado | `cdd5367` |
| 4 | Orquestador + `skopos query` (pipeline completo) | Cerrado | `647412d` |
| 5 | Vigilante en vivo (`skopos watch`) | Cerrado | `896959a` |
| 6 | Metadata vital: `cli`, `modelo_analisis`, `ocurrido_en` | Cerrado | `863e2ee` |
| 6.1 | Ayuda de comandos (`--help`) + próximos pasos por escrito | Cerrado | `7fa01f2` |
| 7 | Ronda adversarial de arquitectura + 7 correcciones | Cerrado | `ab9f51b` |
| 8 | Política de arranque del vigilante (backfill opt-in vs "desde ahora") — hoy C-10(a) del ciclo P-002 | Cerrado (ADR-008, 🔒 2026-08-20) | `4f7900a` |
| 9 | Herramienta de lectura por sesión/fecha/rango (`skopos read`) — diferido explícito (2026-08-20, P-002 §2); lo prepara el índice `ocurrido_en` de C-9 | Diferido | — |
| 10 | Ensayo del canal escrubery contra el repo real (P-002 §3.6) | Cerrado | `8d68ed1` |
| 11 | Búsqueda semántica (embeddings) — condicional a que `$text` (ADR-006) resulte insuficiente en uso real | Futuro, no decidido — **la condición sigue sin evaluarse** y hasta el 2026-09-13 no se podía: los dos índices de texto estaban en `default_language: "english"` sobre corpus español, así que `de` recuperaba 331 de 332 documentos y el ruido parecía falta de semántica (`docs/evidencia/idioma-del-indice-de-texto-2026-09-13.md`). ADR-019 propone el parámetro; la métrica con la que este hito debe reabrirse es cuántas consultas reales **no comparten ninguna palabra** con su objetivo — lo único que un índice léxico no recupera, medido | — |
| 12 | Soporte multi-CLI (más allá de Codex) — confirmado por el dueño el 2026-08-20; precondiciones C-9..C-5 cerradas; **ADR-010 + SPEC-006 aceptados 🔒 2026-08-21** (rondas 10–18; 17 = gate final) | Cerrado documentalmente; implementación **autorizada 🔒 2026-08-28** con alcance A+B vía P-003 (hito 18) | `fc37a90` |
| 13 | C-9: eje de proyecto + eje CLI real + índices (P-002 §3.1) | Cerrado | `811e58c` |
| 14 | C-8: ADR superficie de mutación o retención (P-002 §3.2) — ADR-007, alternativa B (supersede con versiones), decisión 🔒 2026-08-20 | Cerrado | `f0f6134` |
| 15 | C-10: cursor de ingesta — decisión 8 + ADR de lectura incremental (P-002 §3.3) 🔒 | **Cerrado** — gate con remedición fechada (`remedicion-ciclo-c10-2026-08-28.md`), **ADR-011 aceptado 🔒 2026-08-28** e implementado tras la ronda 23 (4 hallazgos corregidos): ciclo de 13.9 s a **3.7–4.9 s** con carga normal, dentro del intervalo de 5 s; 159 tests (`cursor-incremental-2026-08-28.md`) | `7761607` |
| 16 | C-6: decisión sobre `fragmento_completo` — ADR-009, P4a+P5+P3, decisión 🔒 2026-08-20 | Cerrado | `21ce77a` |
| 17 | C-5: detector de eco sobre corpus piloto (P-002 §3.5) — 6/6 sellados, 0 hits, control positivo 3/3 | Cerrado | `27c1332` |
| 18 | Implementación multi-CLI, fases A+B de `docs/propuestas/P-003-colector-conversation-event.md` (aceptada 🔒 2026-08-28 tras la ronda 22; fases C/D de exportación **aplazadas** por no tener consumidor). A: parser codex → adaptador tras `parser-contrato/v1`. B: adaptadores claude-code, opencode, cline, kimi-code — Hito 15 ya cerrado, B destrabada. `qwen-code`: **diferido** por decisión del dueño 2026-08-28, con el reconocimiento hecho y guardado en `docs/evidencia/reconocimiento-qwen-2026-08-28.md` (no hay marca de cierre de turno; exigiría derivar la frontera y construir el predicado de identidad) | **A cerrada** (evidencia: `docs/evidencia/fase-a-adaptador-codex-2026-08-28.md` — 131 tests, 643/643 identidad, 0/394 falsos positivos, 45/45 archivos equivalentes al extractor previo); pipeline **enrutado por `parsear()`**; **B CERRADA: los 5 CLIs** — claude-code, cline, kimi-code y opencode (este último vía ADR-012, origen de filas) (`docs/evidencia/ficha-claude-code-2026-08-28.md` — 205/205 detectados, 0 falsos positivos sobre 2,187 ajenos, 1,800 turnos, 173 tests); opencode resuelto con **ADR-012 aceptado 🔒 2026-08-28** (localizador de origen: filas en vez de offsets, instantánea = transacción de lectura, fragmento = serialización canónica sellada; `docs/evidencia/ficha-opencode-2026-08-28.md`) | `4dd10f4` |
| 19 | opencode al vigilante — cursor incremental para orígenes de filas (**ADR-013, 🔒 2026-09-06**, revoca §d de ADR-012 con medición completa: extracción completa 18.3 s vs delta por `time_created` 91.8 ms/24 h con índice cubriente existente; sellos de la delta byte-idénticos a la completa — 45/45 re-verificados tras el fix). `skopos-cursores/v2` aditivo, marca de agua con abridor previo y segmento completo del turno abierto, `procesar_base_filas` con la regla de congelamiento de ADR-011, fuente de filas en `watch` (cold start = pasada completa degradada, nunca pérdida; dedup en Mongo manda, ADR-005). Ronda adversarial del cierre: `fix-and-retry` — BLOCKER corregido (los turnos que cruzaban 2+ ciclos se perdían enteros; test de regresión incluido) | Cerrado | `31ba387` |
| 20 | Análisis multi-proveedor (**ADR-014, 🔒 2026-09-06**; enmienda parcial de ADR-001 y del manifest): adaptador compatible-OpenAI en stdlib (`_llamar_openai_compat`, parseo tolerante de cercados), proveedor por entorno `SKOPOS_LLM_API/BASE_URL/MODELO/API_KEY` — Ollama local sigue siendo el default byte-idéntico; remoto sólo por decreto (la key vive en el entorno, jamás en el repo). Precedencia argumento > entorno > default; `modelo_analisis` registra el proveedor real. Watch reiniciado el mismo día con las 5 fuentes (opencode en vivo desde ADR-013) | Cerrado | `c1579bc` |
| 21 | Gate de Skevi adoptado (**ADR-015, 🔒 2026-09-06**): `scripts/check_sizes.py` + `check_plans.py` copiados verbatim desde skevi (HEAD `910cdc4`, clon sincronizado), canon propio en `skevi-gate.json` (`required` reemplaza; límites 800/200/300 heredados sin redeclarar). Primera corrida: 118 archivos en límites, 0 incumplimientos. Gate de planes E1-E5 inactivo (clave `plans` ausente, fail-closed): el único plan existente es registro de ciclo cerrado; el primer plan nuevo deberá conformarlo y declarar la clave. AGENTS/README/guía actualizados — la verificación exige el gate en verde junto a la suite | Cerrado | `7eb1922` |
| 22 | Idioma por audiencia (**ADR-016, 🔒 2026-09-12**): inglés en comandos, flags, campos e ids de contrato; español en módulos, funciones, comentarios, `docs/` y commits. Los 25,909 campos almacenados **no** se migran hoy: se renombran dentro del `v3` que exigirá la ampliación a conversaciones de cualquier origen, para no pagar dos migraciones. Alias en inglés para `reanalizar`/`indexar`/`buscar`, sin retirar los actuales | **Implementado** — `analyze`/`reanalyze`/`index`/`search` vivos, alias viejos avisan por stderr | — |
| 23 | Puerta índice→análisis, `skopos analyze` (**ADR-017, 🔒 2026-09-12**, sobre P-006 §7): los turnos indexados eran inalcanzables para el análisis —`indexar` no llama al modelo, `watch` sólo cubre su ventana, `reanalizar` supersede uno existente—, con 25,909 observados y **8 interpretados**. Primer corpus: las **560 anclas `commit-write-plan`** (~3 h serial, local con `qwen3:8b`). No toca turnos con análisis previo; la ventana de ADR-008 queda acotada a `watch` | **Implementado** — 19 tests nuevos (272 en total), `analyze` corrido contra el corpus real y `skopos query` sirviendo resultados por primera vez; primera corrida acotada a **ventana de 7 días** por decisión del dueño (2026-09-12): 129 anclas en vez de 608, y —por P-007— las únicas con offsets sanos, así que el piloto evalúa la capa interpretada con su evidencia cruda. **Piloto cerrado: 135/135 anclas, 0 fallos** (`docs/evidencia/piloto-anclas-2026-09-12.md`) — `skopos.analisis` pasa de 8 a 151 documentos y `skopos query` sirve resultados por primera vez. Hicieron falta cuatro pases (contexto local insuficiente, endpoint de Z.ai equivocado, reintento ausente); ninguno duplicó nada gracias a la idempotencia de (b). Destapó un fallo en `query`: reventaba con análisis de opencode por asumir offsets enteros — corregido con el estado `origen_de_filas` | `pendiente` |
| 23.1 | **Hallazgo P-007** — offsets irrecuperables en la parte del índice construida el 2026-08-29: el desfase crece turno a turno (firma de un acumulador que no se reinició por archivo) y el 78 % de una muestra cae fuera del EOF, así que `fragmento_completo` (ADR-009 P3, hito 16) se niega. **No es pérdida de contenido ni duplicados** (595 textos distintos de 608): el índice está segmentado distinto, no inflado. La ingesta con el parser de hoy nace sana (0/400 rotos). **REPARADO el mismo día** (`docs/evidencia/reconstruccion-indice-2026-09-12.md`): índice reconstruido de 26,007 a 16,974 turnos —los 9,033 de diferencia eran artefactos de la segmentación vieja, 0 turnos perdidos— con **0/12,156 offsets rotos y 300/300 sellos verificados**. El corpus anterior queda en `turnos_respaldo_20260912`, así que la operación es reversible. **Invariante de escritura implementada** el mismo día (`indexar_turno` rechaza offsets imposibles; 0 rechazos sobre el corpus, sin costo). Los 18 análisis con offsets rancios **resueltos con `reanalyze`** (supersede de ADR-007, que recomputa referencias de origen): 0 fallos de integridad sobre los 112 con turno vivo. **Huérfanos resueltos el 2026-09-13**: congelados —no borrados— en `skopos.analisis_huerfanos_20260913` por decisión del dueño, con el patrón reversible de P-007 (copiar, verificar documento a documento, retirar). 41 de 44 eran re-derivables, 2 residuo de tests y 1 irreproducible por rollout borrado; ninguno servía evidencia verificable y ocupaban 9 de 20 asientos en una consulta sin filtro (`docs/evidencia/congelamiento-analisis-huerfanos-2026-09-13.md`) | — |
| 24 | P-005 reformulada como contrato (`curated-anchor`, `context-block`) en vez de tercer proyecto — se escribe **después** de la primera corrida del hito 23, por la regla que siguió ADR-010: el contrato generaliza una instancia viva, no la precede | Contrato pendiente; la corrida previa ya consta en el hito 23. P-005 conserva su propuesta original, aún requiere reconciliación | — |
| 25 | Ampliación a conversaciones de cualquier origen (prime, agentes en runtimes y sandboxes), más allá de CLIs con rollout en disco — anunciada por el dueño el 2026-09-12. ADR-016 prevé `documento-turno-mongo v3` en inglés; ADR-020 acepta D1 para fuentes separadas; la migración v2 no está aprobada | H25.1 aceptado y publicado, T6 completado. Activación y segundo origen implementado pendientes. Hito 25 no cerrado | `7a30a9d` |

## Inicio del plan H25 — 2026-10-05

Iniciado el plan `docs/planes/activos/h25-fuentes-v1.md`, con autorrevisión
adversarial, reconocimiento F0, ADR-020 propuesto y constructor experimental
de sobre fuente. El gate de planes queda activo para el directorio de planes
vigentes. Evidencia: `docs/evidencia/h25-inicio-2026-10-05.md`.
Esto no adjudica D1 ni cierra el hito 25; la integración productiva sigue pendiente.

Actualización posterior del mismo día: el Operador aceptó D1 con referencias
externas. T4 incorpora colecciones de fuentes v3 separadas, transacciones y
la entrada manual source en la rama de trabajo, sin migrar datos v2. Evidencia:
`docs/evidencia/h25-t4-2026-10-05.md`. No adjudica D2a/D2b ni cierra el hito 25.
Mongo productivo no se convirtió a replica set; esa condición y la recuperación
O1 debían resolverse antes de operación real; estado posterior abajo.

Actualización T5/D2b: piloto real de 1186 segmentos, cinco consultas literales
correctas, 45 resultados y seis exclusiones; aceptación acotada del Operador.
Evidencia y autorrevisión: `docs/evidencia/h25-t5-aceptacion-2026-10-05.md`.
O1 recuperado con respaldo/restauración verificados; referencias rotas detectadas
no reparadas. Producción sigue standalone. T6 prepara cierre, sin merge ni
activación; segundo origen estructuralmente distinto aún requiere diseño.
AN-KLA rev11 recoge este estado sin contenido privado. Los datos temporales
permanecen fuera de Git hasta decisión expresa de retirada.
Verificación de este pase: 354 tests OK sin skips (97.618 s) sobre Mongo
temporal exclusivo y Ollama local, sin volver a ingerir la transcripción.

Afinamiento posterior autorizado: receipt/replay validan sello e identidad;
gate estricto, modelo de estados y combinaciones, caídas reales de mongod
temporal. Suite final 361 OK sin skips (75.916 s); gates 196 archivos/un plan.
Evidencia: `docs/evidencia/h25-refinamiento-2026-10-05.md`. Merge autorizado
tras verificación; no activa producción. AN-KLA rev11 es anterior a este pase.
Segundo origen diseñado en `docs/propuestas/h25-runtime-events-v0.md`, todavía
sin adaptador ni export real elegido. Hito 25 no cerrado.
Referencias/ADR-019: `docs/evidencia/referencias-adr019-copia-2026-10-05.md`;
cero relocalizaciones admisibles entre 202 candidatos; originales faltantes
o decisión de conservación requeridos. Ensayo léxico favorable al español con
regresión sin tilde; no se reconstruyó producción ni se activaron embeddings.
Publicación comprobada después: merge fast-forward a main en `7a30a9d`, SHA
remoto verificado. H25.1 aceptado y publicado; T6 completado con diseño del
segundo origen, no con su implementación. El hito 25 completo sigue abierto.

Incremento posterior ADR-019: expansión optativa --expand-accents en query/search,
sin cambio de índice productivo ni comportamiento por defecto. En copia española
reparacion recupera 7 análisis/635 turnos frente a 0/18 sin expansión; no es
evaluación de relevancia. Ver `docs/evidencia/adr019-expansion-2026-10-05.md`.
No corrige frases entre comillas ni todas las tildes. Referencias rotas siguen
pendientes de originales o decisión de conservación; no se reescribieron sellos.

Continuación autorizada: corrección `c49bf5c` y evaluación documental `b6981b2`
fusionadas y publicadas en main (SHA remoto comprobado). Revalidación: 365 tests
OK sin skips en 86.180 s; gates 199 archivos/un plan. Mongo temporal detenido.
Sonda bilingüe muestra pérdida run/running con español y expansión inversa
ausente; no activar ADR-019 todavía. Consultas/objetivos reales requieren juicio
del Operador. Segundo origen autorizado pero sin runtime/export identificado;
no se implementó un adaptador ficticio. Búsqueda acotada en Downloads no localizó
un respaldo inequívoco; no prueba ausencia global. Producción sin cambios.

AN-KLA vigente: revisión 12, registro `f-skopos-h25-followup-2026-10-06`,
digest `sha256:04607717edabe1a6d96dede22afd0a4f7b2595658626ad0457baf7123f5c1136`.
Supersede el cierre T5, conservándolo histórico. Plan/commit gobernados,
verify OK y retrieve presupuesto 8000: 2822 bytes, sin exclusión por presupuesto.
Representación summary/model_derived; no se presenta como atestación independiente.
El bloque de contexto gestionado AN-KLA no está instalado; escritura y recuperación
manual verificadas, sin activar automáticamente integración. Este registro precede
únicamente al commit documental que publica este puntero; no afirma su SHA futuro.

Incremento JSON ASR (ADR-021): fuente real reconocida y piloto temporal con
1186 objetos verificados; import/replay/fetch/búsqueda, sin reemplazar TXT ni
conversaciones ausentes. --format whisperx-json optativo, sobre v1; TXT/v0
intacto. Implementación en rama codex/whisperx-json-source, no merge ni activación.
El JSON es otra representación ASR, no el segundo origen runtime. La declaración
posterior del Operador confirma que no hay respaldo disponible de conversaciones:
conservar historia sin inventar reparación; no hubo borrado/cuarentena/reanálisis.
AN-KLA rev12 precede este incremento y no se actualizó en este pase.

## Sesión del 2026-09-13

Rama `docs/sync-language-and-state-20260912` **fusionada a main** (`3ac9885`)
tras suite y gate en verde; la lectura del diff destapó que el pase de ADR-018
había arrastrado la prosa española a spanglish y dejado dos `--help` en inglés
—corregido antes de empujar, el gate no detecta idiomas—.

Lo nuevo, en orden de lo que desbloquea:

- **`skopos query --no-evidence`** (fusionado en `9aa9eb7`): la evidencia cruda
  era el **97 % del egreso** de una consulta (512 KB de 529 para 20 resultados)
  y no había forma de pedir sólo la capa interpretada, 16.2 KB. Medido tras el
  cambio: 512.4 KB → 16.9 KB, mismos `turn_id`, mismo orden, mismos `excluidos`.
  `fragmento_completo` no desaparece —queda `null`, quitarlo exigiría v2— y el
  estado nuevo `evidencia_omitida` declara que el origen no se leyó, sin fingir
  un veredicto de integridad que nadie verificó (Y-5 de ADR-009).
- **44 análisis huérfanos congelados**, cerrando el primero de los tres
  pendientes del 2026-09-12. `skopos.analisis` queda sin ningún fallo de
  integridad entre las versiones vigentes, por primera vez.
- **`analyze --project skopos`**: 199 analizados, 14 omitidos por análisis
  previo, **0 fallos** en 59.3 min (~17.9 s/turno con `glm-5.3-flash`).
  Cobertura del proyecto: **213 de 224 turnos, 95.1 %**; global 314 de 17,417
  (1.80 %). El `--dry-run` sigue estimando con 19.6 s/turno, calibración que no
  corresponde a ningún corpus medido (las anclas costaron ~90 s, estos ~18).
- **ADR-019 propuesto** (no sellado): los índices de texto están en
  `default_language: "english"` sobre corpus español. `de` recuperaba 331 de
  332 documentos, y el ruido que parecía falta de semántica era una stopword
  arrastrando el corpus. Con índice español el top-1 acierta en las seis
  preguntas de arranque probadas. Recrear el índice de 17,417 turnos es
  operación sobre datos: pide decisión del dueño.

## Actualización documental del 2026-09-12

ADR-018 sustituye la política del hito 22 **sólo para identificadores
internos nuevos**: inglés; español predeterminado para comunicación,
producto y comentarios. El hito 22 conserva la decisión histórica de
ADR-016. No se migraron campos, flags ni módulos existentes.

La guía rápida, README y manifiesto se reconciliaron con la implementación
local de parsers, comandos y P-007. Las cifras y corridas de los hitos son
observaciones fechadas: esta revisión no las convierte en mediciones actuales.
Ver `docs/evidencia/reconciliacion-documental-2026-09-12.md`.

## Criterio de cierre por hito

Igual que en F3 de Skevi: un hito no se cierra por declaración, se cierra
con evidencia — tests en verde, comando real ejecutado, o documento
actualizado. Los hitos 0-7 tienen commit porque ya pasaron esa barra.

## Detalle de los pendientes

El **por qué y la forma** del ciclo vigente está en
`docs/propuestas/P-002-ajuste-ciclo-precondiciones.md`; el **cómo y el
orden de ejecución**, en `docs/planes/plan-ciclo-precondiciones.md`. No
se duplica aquí para no tener dos lugares que puedan desincronizarse.

## Trazabilidad entre sesiones

Estado guardado en AN-KLA local (`.an-kla/`, gitignorado — patrón de
ektel), como cadena de supersedes: `f-ciclo-multi-cli-2026-08-20` →
`f-ciclo-multi-cli-2026-08-28` → `f-skopos-cierre-2026-08-28` →
`f-skopos-cierre-2026-09-06` → `f-skopos-cierre-p005-2026-09-06` →
`f-skopos-cierre-h2-2026-09-10` → `f-skopos-cierre-2026-09-12` →
`f-skopos-cierre-2026-09-13` → `f-skopos-cierre-2026-10-05` →
**`f-skopos-h25-t5-2026-10-05`** (vigente, revisión nº 11,
`sha256:bac7db516b7d8dc204788ef96d7b941892dad55311afae921306d4dd8258ddbb`).
Escritura por plan-write/commit-write-plan, write-full, recibo attest de HEAD
`3c78356`; acredita ese SHA, no toda la narración. Verify OK; recuperación
3594 bytes del cierre, 4802 con acompañante, sin exclusión por presupuesto.
Orden de lectura: plan H25, evidencia T5, ADR-020 y contrato source-store-v3.
La publicación documental posterior no está acreditada por ese recibo.

Antecedente rev10 (sustituido; revisión
`sha256:94c5130203221a1b59e3c5fcb89ef07322628401eaf302f07003db936062995c`,
nº 10, `write-full`, autoridad `tool_observed` mediante recibo `attest`
de `git rev-parse HEAD`). Ese recibo acredita el SHA observado, no todas
las afirmaciones del cierre. Verificación y recuperación posteriores: OK.

Recoge commit/push/merge fast-forward en `main` hasta `8614581`, SHA remoto
comprobado, corrección de vigencia, pilotos de reuniones y lector diarizado.
Suite: 311 pruebas OK sin skips contra Mongo temporal, no el corpus vivo.
Evidencia y límites: `docs/evidencia/publicacion-fuentes-2026-10-05.md`.
Esta referencia documental se publica después de la escritura de memoria;
su commit puede ser posterior al SHA de código registrado.

Coexiste con `f-skopos-documentation-language-2026-09-12` como antecedente:
su mención de P-007 pendiente es histórica y quedó superada por la reparación
posterior. El cierre anterior conserva las mediciones de septiembre; no se
volvieron a comprobar corpus, cobertura ni índices de producción.

Recuperable con
`an-kla retrieve --query "skopos cierre hito 25" --budget 8000`.
Medido en rev10: 3,868 bytes del cierre, 5,076 con el acompañante,
sin exclusiones por presupuesto. Mantener 8000 y comprobar `used_bytes`
y exclusiones en cada consulta; las cifras de septiembre son históricas.

AN-KLA local: **0.1.0b22**, comprobado el 2026-10-05. El resultado de escritura
informa `context_diagnostics.installed:false`: no hay bloque gestionado por
AN-KLA en AGENTS.md; las instrucciones manuales de recuperación sí existen.
No se instaló ni activó esa integración. Versiones externas no consultadas.

## Índice de turnos (P-004) e identidad de Codex

P-004 aceptada 🔒 2026-08-28 e **implementada**: `skopos.turnos` con
`documento-turno-mongo v1` y el comando `skopos indexar`. El piloto
destapó que el `turn_id` crudo de Codex se repite entre sesiones —la
dedup habría descartado el 35 % de los turnos
(`docs/evidencia/colision-turn-id-codex-2026-08-28.md`)—, así que **la
identidad de parser-codex pasó a calificada** (🔒 2026-08-28, ADR-010
§7/§8 actualizados: la excepción de id crudo queda revocada por
contraejemplo). Con eso, **índice lleno: 22,870 turnos de los 5 CLIs en
65.9 s, 213 MB, búsqueda en <10 ms**
(`docs/evidencia/indice-de-turnos-2026-08-28.md`).

Los tres pendientes quedaron cerrados el mismo día
(`docs/evidencia/superficie-busqueda-y-eco-2026-08-28.md`):
**`skopos buscar`** sirve el índice con P3, P5 y redacción de secretos
(contrato `cli-skopos-buscar v1`); el **detector de eco** pasó su control
positivo 3/3 sin falsos positivos y midió 29 turnos con firma (0.1 %)
sobre la colección real; y **`watch` ya indexa** por defecto, sólo dentro
de la ventana de ADR-008 y de forma independiente del análisis —
verificado con Ollama caído: el turno queda indexado aunque el análisis
falle.
