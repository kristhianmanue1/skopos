# P-001 v3: jerarquía de memoria Skopos ↔ AN-KLA

Estado: **propuesta — no decidida. Insumo para rondas de consenso y
adversariales entre varios modelos.**
Fecha: 2026-08-19
Revisión: v3 — v2 sometida a ronda adversarial propia (§10). Dos
hallazgos de nivel BLOCKER contra la tesis central de v2.
Autor de estas rondas: Claude Opus 5, analizando **como agente consumidor
de esta memoria**.

> Advertencia de método: las tres revisiones las produjo el mismo modelo,
> con el mismo contexto. La convención de este proyecto para una ronda
> adversarial es **contexto fresco en un agente separado** (ver README,
> ronda del 2026-08-13). Esta ronda no cumple esa condición: es
> autocrítica, no independiente. Trátese como un piso de calidad, no
> como la ronda adversarial del hito.

## 1. Historial de correcciones

**v1 → v2.** v1 recomendaba promoción manual Skopos → AN-KLA con un
humano aprobando cada registro. Retirada por dos errores: de encuadre
(esta es memoria de agentes para agentes; una firma humana por recuerdo
la anula) y de arquitectura (automatizaba hacia el destino inmutable y
dejaba manual el barato — al revés de lo que la asimetría de costos
exige).

**v2 → v3.** v2 sostuvo que *la consolidación hacia Skopos es el `decay`
que le falta a AN-KLA*, y que eso hace la integración necesaria. La ronda
adversarial encontró que **el mecanismo no está disponible como se
describió** (A-1) y que **no reduce el conjunto caliente** (A-2). La
tesis sobrevive debilitada y con precondiciones que v2 no presupuestó.
Detalle en §10.

Sigue en pie desde v1: H-1 (`tool_observed` no pasa por CLI), H-2
(`fragmento_completo` no cruza), H-3 (prueba de amputación descarta
reemplazar Mongo), H-5 (superficie de inyección).

## 2. Los tipos de AN-KLA, observados

Verificado en `/Users/krisnova/www/an-kla-memory` @ `b70561e`.

| Eje | Valores | Estado real en beta.14 |
|---|---|---|
| Stream | `facts`, `events`, `episodes` | los tres existen; `retrieve` busca sólo `facts` por defecto (`an_kla/retrieval.py:38`) |
| Representación | `full`, `summary` | ambas; clases de agente topan en `summary` |
| Operación | `add`, `supersede`, `refute`, `decay` | **sólo `add` y `supersede`** (`an_kla/write_policy.py:54`) |
| Vigencia | `vigente`, `sustituida`, `refutada`, `eliminada` | `eliminada` no tiene operación gobernada |

Semántica declarada para el agente (`an_kla/context_text.py:258-261`):
`facts` para conocimiento versionado, `events` para la cronología,
`episodes` para experiencias y lecciones.

Un turno de conversación es un **`episode`**, no un `fact`. Un hecho
destilado *de* ese turno es un `fact`. No son el mismo registro y no
deben compartir `id`.

## 3. La contradicción central: AN-KLA no puede olvidar

`decay` está en el vocabulario pero produce `skip` con
`operation_not_supported`. `eliminada` no tiene operación gobernada. No
hay GC automático. La compactación es explícita, gobernada y destructiva.

**La operación que define la memoria de corto plazo es la única sin
implementar.** Sin olvido, AN-KLA en ese rol es un diario append-only con
etiqueta de memoria de trabajo: crece monótonamente y el conjunto que
`retrieve` debe puntuar crece con él.

### 3.1 La salida parcial: `supersede` — y sus dos límites

`supersede` sí está implementado. Escribe el registro nuevo y **oculta el
target de la recuperación**, sin mutar su contenido inmutable. v2
propuso usarlo así:

```
1. El agente escribe en AN-KLA          → memoria fresca, con traza
2. Skopos consolida el registro          → pasa a largo plazo
3. AN-KLA hace `supersede` del original  → sale del conjunto caliente
```

**La ronda adversarial encontró dos límites que v2 no vio.**

**Límite 1 — exige autoridad privilegiada (A-1).** La política prohíbe
explícitamente que `derived_from_retrieval` haga `supersede`
(`write_policy.py:414-421`, razón
`supersede_requires_non_derived_authority`). El comentario del código es
inequívoco: *"model_derived may supersede; derived_from_retrieval may
not."*

Si Skopos lee AN-KLA vía `retrieve` para consolidar, el linaje honesto
**es** `derived_from_retrieval`, y el `supersede` queda prohibido.
Declarar `model_derived` para esquivarlo sería lavado de autoridad —
justo lo que la política existe para impedir.

Salidas legítimas, ambas más caras de lo que v2 supuso:

- Consolidar leyendo **la cadena de revisiones/segmentos**, no `retrieve`.
  Es observación del sustrato, no contenido recuperado.
- Un adaptador Python con autoridad `tool_observed` — que es lo honesto
  ("Skopos observó que persistió esto"), pero choca con H-1: esa clase no
  pasa por el CLI y exige resolver autoridad fuera del contenido.

**Límite 2 — no reduce la cardinalidad del conjunto caliente (A-2).**
`supersede` es 1:1 (`supersedes` es un string único en
`write-proposal-v1`) y **escribe un registro nuevo que queda `vigente`**.
Consolidar N hechos deja N registros stub vigentes y recuperables.

Lo que mejora es el *contenido* del conjunto caliente (stubs cortos en
lugar de registros completos), no su *tamaño*. `retrieve` sigue teniendo
que puntuar N registros.

Existe un atajo —escribir stubs sin texto indexable, que `retrieve`
excluye como `no_text`— pero abusa de un diagnóstico
(`record_without_indexable_text`) que la propia política advierte como
"irrecuperable desde el CLI hasta añadir otro registro corregido". No lo
recomiendo; lo registro porque alguien lo va a proponer.

**Formulación corregida:** la consolidación es **compactación del
contenido caliente**, no `decay` de su cardinalidad. Ayuda a la frescura;
no sustituye a `decay`. La afirmación de v2 —"la integración es lo que
le permite a AN-KLA olvidar"— era demasiado fuerte.

## 4. Análisis crítico como agente consumidor

### C-2 (importante — reformulado en v3) — la vigencia se pierde al consolidar

AN-KLA tiene eje de vigencia. Skopos no tiene ninguno: el grep de
`vigencia|vigente|sustituid|supersede` sobre `docs/contratos/` y
`src/skopos/` devuelve cero.

**v2 exigía un eje de vigencia en cada documento de Skopos. La ronda lo
identificó como error de categoría (A-5):** las observaciones no
caducan. "El 2026-08-13 decidimos X" es verdad para siempre. Lo que
caduca son los *hechos derivados*, no el registro de que algo se dijo.

Reformulación:

1. Los `facts` consolidados desde AN-KLA **deben** llegar con su vigencia.
   Un `fact` marcado `sustituida` que aterriza en Skopos sin marca es
   degradación de información, no consolidación.
2. Los turnos observados por Skopos no necesitan vigencia, pero la
   recuperación **sí debe exponer orden temporal y contradicción**: si
   tres turnos hablan de índices en Mongo y el más reciente contradice a
   los dos viejos, devolver los tres sin señal me hace elegir al azar.

Sigue siendo el peor modo de fallo del rol de largo plazo. Como agente,
memoria obsoleta pero confiada es **peor que no tener memoria**: la
ausencia me hace preguntar, lo obsoleto me hace equivocarme con
seguridad. Pero la corrección es más barata que la que v2 pedía.

### C-3 (importante — degradado en v3) — recuperación léxica sobre corpus grande

ADR-006 es explícito: `$text` es coincidencia por palabra, y
"reformulaciones sin palabras en común siguen sin recuperarse".

**v2 declaró esto bloqueante. La ronda encontró que el argumento probaba
demasiado (A-3):** AN-KLA **también** es léxico —`sqlite-fts5/v1`
(`an_kla/index.py:18`) con un experimento BM25
(`an_kla/evaluation_strategies.py:39`)—. Si lo léxico descalifica a
Skopos para uso de agentes, descalifica igual a AN-KLA. El argumento
"léxico vs. semántico" es inválido tal como estaba planteado.

Reformulación válida, que es sobre **propiedades del corpus**, no sobre
el motor:

| | AN-KLA | Skopos |
|---|---|---|
| Tamaño | pequeño, curado | grande, todo lo observado |
| Vocabulario | lo escribió un agente; lo lee un agente | humano + modelo, mezclado |
| Ventana | reciente | meses |

El recall léxico se degrada con el tamaño del corpus y con la deriva de
vocabulario en el tiempo. AN-KLA opera donde lo léxico funciona bien;
Skopos, donde funciona peor. Eso justifica priorizar embeddings en
Skopos, **no** declararlo bloqueante por contraste con AN-KLA.

Degradado de bloqueante a importante. `nomic-embed-text` ya está en el
entorno (EV-6 de F0).

### C-4 (importante) — "organizar a petición del agente" exige presupuesto

AN-KLA recupera **bajo presupuesto de bytes** y devuelve
`excluded_detail.ids` con el motivo (`budget`, `zero_score`, `inactive`,
`no_text`, `invalid_record`). Skopos devuelve documentos completos, sin
noción de presupuesto.

Mi contexto es finito. Lo que más me importa no es el recorte sino saber
**qué quedó fuera**: sin eso no puedo distinguir "no hay más" de "no
cupo", y no sé si vale la pena pedir otra pasada.

Esto es lo que el requisito "tener partes ordenadas de acuerdo a la
petición del agente" significa como contrato. Es SPEC nueva, no un flag.
Sobrevivió la ronda sin objeciones.

### C-5 (hipótesis no probada — degradado en v3) — contaminación por eco

AN-KLA previó el problema: `derived_from_retrieval` marca el contenido
influido por memoria recuperada, y esa clase no puede `supersede` —"la
memoria recuperada es dato no confiable y no silencia un fact vigente".
**Skopos no tiene equivalente.**

El mecanismo hipotético: Skopos observa rollouts de un agente que estaba
leyendo Skopos; reingiere su propia salida como observación fresca;
`qwen3:8b` resume lo que ya era un resumen. `modelo_analisis` dice qué
modelo analizó, no si lo analizado ya era salida de un modelo.

**v2 lo declaró "el riesgo de largo plazo más serio". La ronda objetó que
era una afirmación sin evidencia (A-6). Intenté falsificarla contra el
corpus real: la colección `analisis` tiene 0 documentos** (se vació, ver
README), así que **no pude confirmarla ni refutarla**.

Queda como hipótesis con un detector concreto, ejecutable cuando el
corpus se repueble:

```python
col.count_documents({"fragmento_completo": {
    "$regex": r'"resumen"\s*:|"tema"\s*:|skopos query', "$options": "i"}})
```

Si eso da > 0, el eco es real y medible. Si da 0 tras un mes de uso, C-5
se archiva. **Una ronda futura debería ejecutarlo antes de que nadie
discuta más sobre esto.**

### C-6 (heredado) — la inyección persiste más donde menos se revisa

Skopos demostró el 2026-08-13 que contenido hostil en un rollout puede
atravesar Ollama y llegar al almacenamiento. En una jerarquía, ese
contenido aterriza en la capa de largo plazo: la que menos se revisa y
más tiempo lo conserva.

Mitigación estructural: sólo `summary` redactado cruza (H-2 lo fuerza), y
el linaje apunta al `turn_id` de origen para que la evidencia cruda quede
auditable en Mongo sin entrar al circuito de recuperación.

### C-7 (crítico — nuevo en v3) — la concurrencia entre modelos no está resuelta

**Hallazgo de la ronda (A-4), ausente de v2, y directamente aplicable al
flujo de trabajo real de este proyecto.**

AN-KLA declara: "admite una sola memoria activa" y "el lock de escritura
es local y no coordina varias máquinas" (README:336-337). Además, cada
commit mueve `CURRENT`, y un plan construido contra una revisión vieja
falla con `write_plan_base_changed`.

Este proyecto se está evaluando mediante **rondas de consenso y
adversariales con varios modelos**. Si esos modelos escriben
concurrentemente en la misma memoria:

- En una máquina: serializan por lock local. Cada commit invalida los
  planes en vuelo de los demás → **tormenta de replanificación**, con
  riesgo de inanición para el agente más lento. El costo de planear se
  desperdicia proporcionalmente al número de escritores.
- Entre máquinas: no hay exclusión mutua. Fuera de contrato.

Ni AN-KLA ni Skopos tienen hoy un modelo de memoria compartida entre
agentes. Toda la arquitectura de §3 y §6 asume **un agente escritor**.
Si el objetivo real es memoria común para un panel de modelos, esa
suposición es el problema de diseño más grande que queda abierto, y
ninguna de las tres revisiones lo había planteado.

## 5. Lo que cada lado debe ganar

**AN-KLA (corto plazo):**
1. `decay` implementado. v2 sostuvo que la consolidación podía
   sustituirlo; §3.1 muestra que sólo lo aproxima. **Sigue haciendo
   falta.**
2. Un modelo de concurrencia si va a haber varios agentes escritores
   (C-7).

**Skopos (largo plazo):**
1. Transporte de vigencia en la consolidación (C-2, reformulado).
2. Recuperación semántica (C-3, importante).
3. Recuperación bajo presupuesto con exclusiones explicadas (C-4).
4. Marca de linaje de eco + ejecutar el detector de C-5 antes de
   priorizarlo.
5. Ingesta de la cadena de revisiones como fuente —no vía `retrieve`,
   por A-1— preservando `subject_ref`, vigencia y linaje.

## 6. Dirección del flujo

**AN-KLA → Skopos (consolidación): automatizable**, con la precondición
de A-1 (leer el sustrato, no `retrieve`, o resolver `tool_observed`).
Destino mutable y barato, volumen bajo.

**Skopos → AN-KLA (destilación): probablemente innecesaria.** Choca con
H-1, H-2 y el volumen contra un historial inmutable. Y en esta
arquitectura, un agente que necesita algo viejo debería **consultar
Skopos directamente, no reinyectarlo en su memoria caliente** —
reinyectar es exactamente cómo se fabricaría el eco de C-5.

## 7. Preguntas para la siguiente ronda

1. **¿Hay uno o varios agentes escritores?** (C-7.) Cambia todo lo
   demás. Debe responderse antes que las otras cuatro.
2. **¿Se implementa `decay` en AN-KLA?** §3.1 muestra que la
   consolidación no lo sustituye, sólo lo aproxima.
3. **¿Qué gana Skopos observando AN-KLA, si ya lee el rollout crudo?**
   Mi respuesta: la **señal de curaduría** — qué turnos produjeron hechos
   que un agente juzgó durables. Es una etiqueta sobre el corpus bruto y
   probablemente vale más que el texto consolidado. **Si la respuesta
   honesta es "nada", la integración entera se cae.** Es el mejor blanco
   para la próxima ronda.
4. **¿Un `fact` superado se consolida o se descarta?** Sostengo que se
   consolida marcado: saber que algo se creyó y dejó de creerse es
   memoria legítima, y a veces más útil que el hecho vigente.
5. **¿Skopos guarda conversaciones de otros proyectos?** Si sí, la
   consolidación cruza fronteras de `subject_ref`, cuyo namespace deriva
   de la identidad del proyecto.

## 8. Posición de esta ronda

El reparto corto/largo plazo es correcto. La integración es **útil pero
no suficiente**: aproxima el `decay` que le falta a AN-KLA sin
sustituirlo, y exige autoridad privilegiada que v2 no presupuestó.

Skopos todavía no es memoria de largo plazo para agentes —le faltan
transporte de vigencia, recuperación semántica y presupuesto— y
consolidar hacia una capa sin esas propiedades produce un archivo grande
y confiado, no memoria.

**Y por encima de todo: si varios modelos van a compartir esta memoria,
ninguno de los dos sistemas lo soporta hoy (C-7).**

**Ordenar Skopos antes de conectar.** El flujo es AN-KLA → Skopos.

## 9. Fuentes

- Skopos: `README.md`, `AGENTS.md`, `docs/contratos/f1-contratos.md:35-60`,
  `docs/adr/ADR-006-busqueda-texto-completo.md`. Corpus consultado en
  vivo: colección `analisis` con 0 documentos al 2026-08-19.
- AN-KLA (`/Users/krisnova/www/an-kla-memory` @ `b70561e`):
  `an_kla/context_text.py:220-262`, `an_kla/write_policy.py:25,54,414-421`,
  `an_kla/retrieval.py:38`, `an_kla/index.py:18`,
  `an_kla/evaluation_strategies.py:39`, `README.md:336-337`,
  `docs/architecture/0007-write-policy-v1.md:75-115,205-215`,
  `docs/schemas/write-proposal-v1.schema.json`,
  `docs/schemas/revision-v3.schema.json`, `docs/write-policy-cli.md`.

## 10. Ronda adversarial sobre v2 (2026-08-19)

Método: autocrítica del mismo modelo, verificando cada afirmación contra
el código en vez de contra el razonamiento previo. **No es contexto
fresco** (ver advertencia de portada).

| Id | Nivel | Hallazgo | Efecto |
|---|---|---|---|
| A-1 | BLOCKER | `derived_from_retrieval` no puede `supersede` (`write_policy.py:414-421`). Si la consolidación lee vía `retrieve`, el mecanismo de v2 es ilegal por linaje honesto. | §3.1: exige leer el sustrato o autoridad `tool_observed` |
| A-2 | BLOCKER | `supersede` es 1:1 y deja un registro nuevo `vigente`. No reduce la cardinalidad del conjunto caliente. | §3.1: "consolidación = decay" degradado a "compactación de contenido" |
| A-4 | CRÍTICO | Concurrencia entre varios modelos escritores no soportada por ninguno de los dos sistemas. Ausente en v1 y v2. | C-7, nuevo |
| A-3 | ALTO | C-3 probaba demasiado: AN-KLA también es léxico (FTS5/BM25). El argumento era inválido. | C-3 rearmado sobre propiedades del corpus; degradado a importante |
| A-5 | MEDIO | C-2 era error de categoría: las observaciones no caducan, los hechos derivados sí. | C-2 reformulado, más barato |
| A-6 | MEDIO | C-5 se declaró "riesgo más serio" sin evidencia. Falsificación intentada contra el corpus: 0 documentos, no concluyente. | C-5 degradado a hipótesis con detector ejecutable |

Sobrevivieron sin cambios: C-4 (presupuesto), C-6 (inyección), H-1, H-2,
H-3, y la dirección del flujo AN-KLA → Skopos.

**Lo que esta ronda no pudo hacer y la siguiente debería:** ejecutar el
detector de C-5 contra un corpus poblado; atacar la pregunta 3 de §7 (si
la señal de curaduría no vale nada, sobra todo lo demás); y correr con
contexto fresco e independiente, que es lo que la convención del
proyecto pide y esta ronda no cumplió.
