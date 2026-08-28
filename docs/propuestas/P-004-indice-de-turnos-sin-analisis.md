# P-004: índice de turnos sin análisis — recordar todo, interpretar lo que haga falta

Estado: **aceptada** — decisión 🔒 del dueño, 2026-08-28, sobre las tres
preguntas del §6: (1) colección aparte **sí**; (2) el histórico va en
`skopos indexar` y lo nuevo en `watch` **después** de medir un piloto
acotado; (3) P3/P5 de ADR-009 **se extienden** a toda superficie que
sirva texto de turno. **Implementación parada por un hallazgo** — ver
§7.
Fecha: 2026-08-28.
Origen: sesión del 2026-08-28. El dueño observó que las transcripciones
de los CLIs "son buenas para el futuro análisis de lo que saca Skopos", y
al medir el corpus apareció el problema real: **hay mucha más
conversación de la que el modelo puede digerir**.

## 1. El problema, con números de hoy

| Medida | Valor |
|---|---|
| Turnos observables (4 CLIs soportados) | **19,811** |
| Texto de conversación | **159.3 M caracteres** |
| Ritmo de crecimiento | **~2.2 GB/mes** de transcripciones (92 % Codex) |
| Coste de análisis por turno (snapshot 2026-08-20) | 90–126 s |
| **Analizar el corpus entero con Ollama** | **500–690 horas en serie** |
| Documentos en `skopos.analisis` hoy | **8** |

El pipeline analiza más despacio de lo que el corpus crece. Con el motor
actual eso no se arregla afinando: son tres semanas de máquina a pleno
para ponerse al día una vez, y al terminar habría un mes nuevo esperando.

Mientras tanto, **la extracción no usa modelo**: la frontera de SPEC-006
recorre los 1,405 archivos y produce los 19,811 turnos en segundos, con
su texto, CLI, proyecto, fecha, offsets y sello. Ese trabajo ya está
hecho y se tira a la basura en cada ciclo.

## 2. Qué propone

Persistir **el turno** —no su análisis— en una colección propia,
`skopos.turnos`, y dejar el análisis con Ollama como una **segunda
etapa opcional y selectiva** sobre lo ya indexado.

- **Recordar todo** deja de depender del modelo: la búsqueda por texto
  sobre el corpus completo estaría disponible en cuanto corra la
  ingesta, no en 600 horas.
- **Interpretar** sigue siendo lo que hoy hace SPEC-002, pero se aplica a
  lo que merezca la pena (un proyecto, un rango de fechas, lo que una
  búsqueda devolvió), no a todo por orden de llegada.

**Ningún contrato aceptado cambia.** `documento-analisis-mongo v2` exige
`tema`, `resumen` y `modelo_analisis`, y por eso un turno sin análisis no
cabe ahí: en vez de enmendar ese contrato —que tocaría datos existentes,
el supersede de ADR-007 y el índice `(turn_id, version)`— se añade uno
nuevo, `documento-turno-mongo v1`, en una colección separada. Es
aditivo, igual que lo fue añadir un parser al registro del ADR-010.

## 3. Forma propuesta del documento

Los campos que el `Turno` ya produce (SPEC-001 + ADR-010 §5), sin
inventar ninguno: `turn_id`, `session_id`, `cli`, `proyecto`,
`ruta_origen`, `offset_inicio`, `offset_fin`, `fragmento_sha256`,
`ocurrido_en`, `texto_usuario`, `texto_agente`, `indexado_en`.

- Unicidad por `turn_id` (los adaptadores nuevos ya califican con su
  producto, ADR-010 §7, así que no hay colisión entre CLIs).
- Índice `$text` sobre `texto_usuario`/`texto_agente` — la misma
  decisión de ADR-006 que ya rige la búsqueda, aplicada al texto crudo.
- **Insert-only**, como el resto: un turno ya indexado no se reescribe.

## 4. Lo que hay que mirar de frente, no en letra pequeña

1. **El almacén pasa a contener conversación cruda.** Hasta ahora Mongo
   guardaba análisis (tema/resumen/entidades) y el texto vivía sólo en el
   archivo. Con esto, 159 MB de conversación entran en la base. Las
   mitigaciones de **ADR-009** (P3 dato-nunca-instrucción, P5 límite de
   salida) fueron diseñadas para el fragmento servido; **habría que
   extenderlas a cualquier superficie que sirva `texto_usuario`/
   `texto_agente`**, o el eco que C-5 midió tendría una puerta nueva.
2. **El detector de eco de C-5 se vuelve más necesario, no menos**: al
   indexar todo, las conversaciones sobre Skopos entran en Skopos. El
   piloto midió 0 hits sobre 6 turnos; con 19,811 el control positivo
   deja de ser una formalidad.
3. **Duplica el texto en disco** (~159 MB en Mongo además del archivo).
   Es poco al lado de los 3 GB de transcripciones, pero no es cero.
4. **`fragmento_completo` no cambia**: sigue viviendo en el archivo de
   origen (ADR-009). El índice guarda el texto normalizado del turno, no
   sustituye al fragmento ni releva de conservar los archivos.

## 5. Alternativas consideradas

- **Enmendar `documento-analisis-mongo` a v3** haciendo `tema`/`resumen`
  opcionales: mezcla dos cosas distintas —lo observado y lo
  interpretado— en la misma colección, obliga a que toda lectura
  distinga si hay análisis, y toca un contrato con datos vivos. Se
  descarta.
- **No indexar y acelerar el análisis** (modelo más pequeño, o externo):
  ataca el síntoma. Aun a 10 s por turno serían ~55 horas, y el mes
  siguiente vuelve a acumular. Además el motor externo es otra decisión
  (ADR-001 / REQ-9) que esta propuesta **no** necesita.
- **Índice fuera de Mongo** (SQLite, ficheros): añade un almacén más al
  proyecto sin motivo; Mongo ya está y ADR-006 ya decidió `$text`.

## 6. Decisión 🔒 que se pide al dueño

1. ¿Se aprueba `skopos.turnos` como colección aparte, con contrato
   propio y sin tocar `documento-analisis-mongo v2`?
2. ¿La ingesta del índice va **por defecto** en `skopos watch`, o detrás
   de un comando propio (`skopos indexar`) hasta ver su coste real?
3. ¿Se extienden P3/P5 de ADR-009 a las superficies que sirvan texto de
   turno? (recomendado: sí, y es lo que haría que esto no abra un canal
   de eco nuevo).

## Referencias

- Volumen y coste: medidos el 2026-08-28 en esta sesión; corpus de
  `docs/evidencia/ficha-*-2026-08-28.md` (4 CLIs, 1,405 archivos).
- Coste de análisis: `docs/evidencia/remedicion-ciclo-c10-2026-08-20.md`
  (90–126 s por llamada real).
- Contratos afectados (ninguno modificado):
  `docs/contratos/f1-contratos.md` — `documento-analisis-mongo v2`.
- Decisiones que enmarcan: ADR-006 (`$text`), ADR-007 (insert-only y
  supersede), ADR-009 (fragmento y mitigaciones de eco), ADR-010 §7
  (identidad calificada).

## 7. Parada tras el piloto: la identidad de Codex está rota

El piloto acotado se ejecutó el 2026-08-28 y **destapó un defecto previo
a esta propuesta**: el `turn_id` crudo de Codex no es único entre
sesiones. De 16,301 turnos extraídos hay 10,441 ids distintos, así que
**la dedup por `turn_id` descartaría 5,860 turnos (35 %)** — y 768 de
los ids repetidos apuntan a texto **diferente**, no al mismo turno.

Evidencia completa: `docs/evidencia/colision-turn-id-codex-2026-08-28.md`.

No es un problema del índice: afecta ya a `skopos.analisis` vía
`existe_turn_id` (ADR-005) y al índice único `(turn_id, version)` de
ADR-007. Calificar con la sesión
(`codex-cli:{session_id}:{turn_id}`) da **16,301 ids únicos, 0
colisiones**, verificado sobre el mismo corpus.

**Lo construido queda listo pero el índice NO se llena** hasta que se
decida la identidad: indexar 19,811 turnos con una identidad que se sabe
rota, para migrarla después, es pagar dos veces. La base del piloto se
eliminó por la misma razón.

Entregado y en verde: `documento-turno-mongo v1` (contrato),
`skopos.turnos` con sus índices, `indexar_turno`, el comando
`skopos indexar` (con `--limite` y `--dry-run`) y 22 tests.
