# ADR-017: puerta índice→análisis (`skopos analyze`)

Estado: **aceptado** — decisión 🔒 del dueño, 2026-09-12 ("aceptadas tus
recomendaciones"), sobre las seis preguntas de
`docs/propuestas/P-006-analisis-sobre-turnos-indexados.md` §7. Acota —
sin contradecir— el alcance de ADR-008. Nombres según ADR-016.

## Contexto

La separación entre índice y análisis del hito 18 fue correcta: indexar
es barato y evita perder conversación; analizar cuesta ~19.6 s/turno con
`qwen3:8b`. Lo que nadie escribió es que **esa separación dejó los
turnos indexados fuera del alcance del análisis, para siempre**:

- `indexar` no llama al modelo — por diseño (P-004);
- `watch` analiza sólo lo nuevo y dentro de su ventana (ADR-008);
- `reanalizar` hace supersede de un análisis **existente** (ADR-007):
  necesita que ya haya uno, no crea el primero.

Estado medido el 2026-09-12: **25,909 turnos observados, 8
interpretados**, el último análisis del 2026-08-22. `skopos query`
—SPEC-004, la razón de ser declarada del proyecto— no tiene qué servir.
Cada decisión aislada fue buena; lo que nunca se revisó fue el estado
agregado.

## Decisión

### (a) Se autoriza un comando nuevo: `skopos analyze`

Selecciona turnos de `skopos.turnos` por los ejes que ya existen con
índice (`proyecto`, `cli`, `ocurrido_en` — C-9, hito 13) y los manda a
la misma ruta de análisis que usa el orquestador.

```
skopos analyze [--project P] [--cli C] [--anchor PATRON]
               [--since FECHA] [--until FECHA] [--limit N] [--dry-run]
```

Nombre y flags en inglés por ADR-016 (a) y (e). Publica el contrato de
superficie `skopos/cli-skopos-analyze v1` en el manifiesto al
implementarse, no antes.

`--dry-run` cuenta y estima el costo antes de comprometer horas de
cómputo, igual que `indexar`.

### (b) Nunca toca un turno que ya tiene análisis

`analyze` crea **el primer** análisis de un turno que no tiene ninguno.
Un turno con análisis previo se omite y se reporta como omitido.

El supersede sigue siendo territorio exclusivo de `reanalizar` y de
ADR-007. La regla es de autoridad, no de eficiencia: **una sola
superficie puede crear la segunda versión de un análisis**, y si dos
comandos pudieran hacerlo, la traza de por qué existe cada versión
dejaría de ser reconstruible.

### (c) El primer corpus son las 560 anclas `commit-write-plan`

Turnos que llevan evidencia de preservación deliberada — alguien se
detuvo y decidió que eso merecía guardarse. Medido el 2026-09-12: 560
(eran 448 el 2026-09-06; el corpus crece solo), repartidas en codex-cli
400, opencode 115, claude-code 45, y en decenas de proyectos
(an-kla-memory 82, argos 64, pinax 63, kratos 47, eduEMD 45).

≈3.0 h serial con `qwen3:8b`. Es el ~2 % del corpus con la mayor
densidad de señal por turno, y un conjunto curado que **ya existe sin
costo de etiquetado**.

`plan-write` (587 turnos) queda **fuera del primer corpus**: son planes
escritos, no necesariamente consumados — señal más ruidosa. Ampliar es
una corrida más si el resultado lo justifica; la diferencia entre ambos
conjuntos es en sí un dato a medir por separado.

### (d) Se corre en local, con `qwen3:8b`

> **ENMENDADO el mismo día — ver "Enmienda (d'), 🔒 2026-09-12" al final.**
> El piloto se corre con proveedor remoto por decreto del dueño. Lo que
> sigue se conserva porque su razonamiento sobre la frontera no caducó;
> lo que cambió fue el costo del lado local, no el valor del material.

Nada sale de la máquina. ADR-014 permite decretar proveedor remoto, y
este **no** es el caso para estrenarlo: las anclas son el material más
deliberado del corpus, de an-kla-memory, argos, pinax y kratos. Tres
horas de cómputo nocturno no valen cruzar esa frontera.

### (e) Los contratos de contexto se escriben DESPUÉS de la primera corrida

`skopos/curated-anchor/v1` y `skopos/context-block/v1` —la reformulación
de P-005 como contrato en vez de tercer proyecto— **no se escriben
todavía**.

Razón: ADR-010 no inventó `parser-contrato/v1` en abstracto. Se aceptó
con las precondiciones C-9..C-5 cerradas, el fragmento sellado y un
corpus piloto ya ingestado: **generalizó un parser que ya funcionaba**.
Esa es la regla que el proyecto sigue de hecho. Hoy `skopos.analisis`
tiene 8 documentos: nadie ha visto la capa interpretada funcionar un
solo día, y un contrato escrito sin experiencia operativa congela
suposiciones en obligaciones — v1 nacería para ser superseded.

Se escriben describiendo lo que se vio, no lo que se supone.

### (f) La ventana de ADR-008 gobierna a `watch`, no al análisis

ADR-008 fijó que el vigilante procesa sólo turnos cerrados desde su
arranque. Nunca dijo explícitamente que esa ventana acotara **todo** el
análisis del sistema — se asumió, porque no existía otra forma de
analizar.

Queda escrito: **la política de arranque de ADR-008 acota a `watch`.**
`analyze` es una ruta manual, explícita y fuera de esa ventana, y no la
contradice. Sin este apartado, quien lea ADR-008 en el futuro concluiría
que `analyze` lo incumple.

## Alternativas descartadas

**Que `watch --backfill` llenara el análisis.** Existe y funciona, pero
analiza todo lo que encuentra en orden de aparición: no permite elegir
las anclas, y a 19.6 s/turno sobre 25,909 turnos son semanas. El valor
está en la selección, no en el volumen.

**Extender `reanalizar` para que cree el primer análisis si no existe.**
Ahorraba un comando y rompía (b): el supersede dejaría de tener un único
dueño, por comodidad.

**Analizar el corpus completo.** Semanas de cómputo para interpretar
mayoritariamente turnos triviales. La hipótesis a probar es si el
contexto interpretado sirve, y eso se prueba con las anclas.

**Escribir `curated-anchor/v1` ya, para que AN-KLA avance en paralelo.**
Descartada por (e), reconociendo que tiene un costo real: la vía
contractual necesita contraparte dispuesta, y esperar retrasa esa
conversación. Se acepta el retraso a cambio de no publicar un contrato
que habría que superseder.

## Consecuencias

- `skopos analyze` entra a la superficie de comandos y al manifiesto.
- P-006 queda decidida en sus seis preguntas; deja de ser propuesta
  abierta.
- P-005 se destraba: obtiene la primera instancia viva que su contrato
  necesita generalizar, y su decisión pasa a ser un experimento con
  resultado — incluido el resultado nulo, que también cierra.
- `skopos query` deja de estar vacío por primera vez desde su
  implementación, y recién entonces el hito 11 (búsqueda semántica) se
  vuelve evaluable: su condición de disparo es que `$text` resulte
  insuficiente **en uso real**, y hasta ahora no había uso real.

## Lo que este ADR NO decide

- No decide la forma de `curated-anchor` ni de `context-block` — (e).
- No decide si P-005 se acepta: decide cómo se vuelve decidible.
- No cambia la política de `watch` ni la de `reanalizar`.
- No amplía el corpus a `plan-write` ni a los 25,909 turnos.
- No decide nada sobre la ampliación a conversaciones de cualquier
  origen, anunciada el 2026-09-12 y pendiente de su propio análisis.

## Firma de decisión

Dueño, 2026-09-12, sobre P-006 §7: seis preguntas, seis recomendaciones
del agente aceptadas sin variantes. Evidencia de la sesión en P-006 §1.


## Enmienda (d'): el piloto se corre con proveedor remoto 🔒 2026-09-12

**Decreto del dueño, 2026-09-12**, mismo día que (d) y sustituyéndolo
sólo para esta corrida. ADR-014 §c exige decreto explícito para salir de
local; queda dado aquí.

### Qué lo cambió

(d) se decidió estimando el costo local en ~3 h. La medición real lo
desmintió por dos lados a la vez:

| Medida | Estimado en (d) | Real |
|---|---|---|
| Ritmo con `qwen3:8b` | 19.6 s/turno | **195 s/turno** |
| Piloto de 129 anclas en local | ~3 h | **~7 h** |
| Contexto de llama-server | no considerado | **4096 tokens** |
| Anclas que caben en ese contexto | — | **42 %** (54/130) |

El segundo renglón es el que pesa. Las anclas tienen mediana de 17,164
caracteres contra 4,794 del turno típico — son grandes justamente porque
son turnos donde pasó algo. Con `-c 4096` y `--context-shift`, más de la
mitad se analizaba **con el principio del prompt descartado en
silencio**: primero las instrucciones, después `<texto_usuario>`. Un
piloto así no habría medido si la capa interpretada sirve; habría
medido el recorte.

Arreglarlo en local exigía subir `num_ctx` a 32K, que en un M2 de 16 GB
deja la máquina en ~9 GB entre modelo y caché KV.

### La medición del lado remoto

`glm-5.3-flash` vía Z.ai contra `https://api.z.ai/api/coding/paas/v4`
—el endpoint que cubre el Coding Plan; la API estándar `/api/paas/v4` se
paga aparte y responde `429 / 1113` sin saldo—, camino compatible-OpenAI
de ADR-014, probado con un turno **sintético** antes de tocar dato real:

- **4.1 s** de punta a punta, JSON válido, `modelo_analisis` registrando
  el proveedor real como manda ADR-014;
- ~6.4 s/turno en la corrida: **129 anclas en ~14 minutos** contra 7 h;
- sin caché KV local, el contexto deja de ser restricción y las anclas
  entran enteras — **el defecto que motivó la enmienda desaparece, no se
  mitiga**.

### Lo que la enmienda NO dice

- **No revoca el razonamiento de (d).** El material sigue siendo el más
  deliberado del corpus y sigue viajando **crudo**: la redacción de
  secretos de skopos actúa sobre campos derivados, no sobre lo que entra
  al prompt. Ahí van rutas absolutas y lo que haya pasado por la
  terminal. Eso se acepta a sabiendas, no se niega.
- **No autoriza el corpus completo.** 25,909 turnos a 4 s son ~29 h
  serial y eso vuelve viable lo que en local eran semanas, pero es
  decisión propia — y la recomendación del agente es que antes exista
  una capa de redacción sobre el prompt, hoy inexistente.
- **No cambia el default.** Sin variables de entorno, skopos sigue
  usando Ollama local byte-idéntico (ADR-014 §b). Remoto es opt-in por
  entorno, nunca por código.

### Nota técnica que conviene no perder

`glm-5.3-flash` es modelo de razonamiento: gasta tokens en
`reasoning_content` antes de producir `content`. El adaptador funciona
porque **no manda `max_tokens`**. Si alguien lo añadiera sin pensarlo,
todas las respuestas volverían vacías — observado con `max_tokens: 20`,
donde los 20 se fueron en razonamiento y `content` llegó en blanco.

### Los dos caminos, a elección

La capacidad ya existía desde ADR-014; lo que faltaba era tenerla a
mano. Queda así:

| Camino | Cómo se activa |
|---|---|
| **Local** (default) | sin variables `SKOPOS_LLM_*` en el entorno |
| **Remoto** | `source ~/.skopos-env` antes de invocar skopos |

`~/.skopos-env` vive **fuera del repo** con permisos `600` — la key
jamás se commitea (ADR-014 §c). Cambiar de camino es cargar o no cargar
ese archivo; no hay nada que editar en el código, y `modelo_analisis`
deja registrado por turno cuál se usó.
