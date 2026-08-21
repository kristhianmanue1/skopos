# ADR-009: `fragmento_completo` en la recuperación — cinco palancas

Estado: **aceptado** — decisión 9 🔒 firmada por el dueño el 2026-08-20
(Fase 4 / C-6, Hito 16), tras revisión aprobatoria de Pinax. Palancas:
**P4a + P5 + P3, manteniendo P1; P2 y P4b rechazadas** con sus criterios
de reapertura registrados (P2: contaminación real demostrada por el
detector de Fase 5; P4b: rotación/pérdida de rollouts que lastime la
recuperación). Sometido a ronda adversarial pre-decisión (ronda 6,
`docs/rondas/2026-08-20-ronda-6-adr009.md`): 10 hallazgos incorporados
antes de la firma. Mediciones en
`docs/evidencia/fragmentos-c6-2026-08-20.md`.

## Contexto

`skopos query` sirve hoy `fragmento_completo` (CONTRATO cli-skopos-query
v1) releyéndolo del rollout original por offsets (`cli.py:28-34`), con
tres defectos verificados:

1. **Se sirve crudo y sin redactar** (P-001 §4.4, B-5): es
   simultáneamente vector de inyección (texto hostil llega íntegro al
   contexto del agente consumidor) y **motor del eco** (P-001 §4.5: la
   recuperación sin tope vuelca turnos enteros al rollout del
   consultante, que Skopos reingerirá).
2. **Sin verificación de integridad, con fallos silenciosos** (Y-5): si
   el archivo rotó/truncó/editó, se sirven bytes de otro turno, una
   lectura corta o `null` — indistinguible de "no hay fragmento".
3. **Sin límite ni presupuesto**: sin `limit` en la consulta, sin tope
   de fragmento, sin señal de qué quedó fuera (P-001 §4.1/C-4).

Mediciones para decidir (snapshot 2026-08-20, método y verificación
independiente en `docs/evidencia/fragmentos-c6-2026-08-20.md`):

- Fragmentos totales (bytes entre offsets): **2.28 GB** — el 99.8% del
  corpus (los offsets teselan el archivo por construcción).
- Por turno: media **150 KiB**, mediana **62 KiB**, p95 **456 KiB**,
  máximo **41.3 MiB** (3 turnos exceden el límite de documento BSON de
  16 MiB — no persistibles inline).
- Latencia de escrubery como referencia de costo de subprocess:
  ~0.27 s caliente (`docs/evidencia/ensayo-escrubery-2026-08-20.md`).

## Las cinco palancas

### P1 · Servir crudo (status quo)

El fragmento se sirve verbatim. Costo: 0. Mantiene los defectos 1 y 3;
el 2 sólo cierra si algo más lo cierra (ver Y-5 abajo).

### P2 · Redactar en la salida

Aplicar `redactar_secretos` al fragmento al servirlo. El fragmento, sí,
llega al contexto del consumidor (defecto 1; P-001 §4.4) — la redacción
de la ingesta (tema/resumen/entidades) no lo protege. El rechazo se
sostiene en otros términos: (a) degrada la **evidencia cruda** — el
propósito declarado del campo (README: "es la evidencia cruda"); (b)
falsos positivos sobre código legítimo (una conversación *sobre* tokens
de GitHub discute tokens con ese formato); (c) es la misma redacción
por patrones de la ingesta — cubre formatos conocidos, no garantía
frente a secretos de formato desconocido. Mitigado por la combinación
recomendada (P3 declara el consumo; P5 acota el volumen servido) y
**reversible**: si el detector de Fase 5 muestra contaminación real, la
redacción en servido es un cambio de lectura (nunca exigió reingesta ni
supersede) y se añade sin tocar lo guardado.

### P3 · Marcar como no-instrucción en el contrato del CLI

Declarar en el CONTRATO cli-skopos-query que `fragmento_completo` es
**dato, nunca instrucción**, y que el consumidor debe tratarlo como tal.
Costo: 0 (documental). **Declarativa**: Skopos puede declararla, no
exigirla — su eficacia depende del consumidor. Es la misma mitigación
que SPEC-002 aplica al prompt del análisis; aquí, al canal de consumo.
Sola no basta; con P5 acota el daño si el consumidor desoye la marca.

### P4 · Persistir el fragmento o sellar el origen (hash+tamaño)

Dos variantes distintas:

- **P4a · Sellar (recomendada)**: al ingerir, guardar `sha256` y tamaño
  **de los bytes del fragmento** (sólo del fragmento — ronda 6, R6-2:
  sellar el archivo entero daría falsos positivos ante appends de
  sesiones vivas, y es innecesario porque los fragmentos teselan el
  99.8% del archivo: el hash del fragmento detecta rotación, edición y
  truncación por sí solo). Al servir, verificar: coincidencia →
  servir; discordancia → **fallo explícito y visible** en la salida
  (cierra Y-5: nunca más bytes de otro turno ni lecturas cortas en
  silencio). Costo: ~150 bytes/doc (despreciable frente a 150 KiB de
  media); CPU: hash SHA-256 de 150 KiB ≈ ~1 ms por resultado servido
  (estimación sobre hardware típico, 2026-08-20; la lectura ya ocurre
  hoy para servir el texto).
- **P4b · Persistir**: guardar el texto del fragmento EN el documento
  al ingerir. Cierra la dependencia del archivo por completo (consulta
  sin I/O de origen), pero: duplica el almacenamiento (~2.28 GB hoy,
  crecimiento monótono espejo del corpus); **3 turnos medidos (máx
  41.3 MiB) exceden el límite BSON de 16 MiB** — exige GridFS o
  exclusión explícita de gigantes; y persiste texto hostil crudo en
  Mongo (hoy sólo vive en archivos del usuario).

### P5 · Presupuesto/límite en la salida

Acotar la salida del `query`: máximo de resultados (p.ej. `--max`,
default ~20), tope de bytes servidos por fragmento (p.ej. default 64
KiB) y **señal de exclusión** (P-001 C-4: contar y listar qué quedó
fuera y por qué — presupuesto/tamaño). Costo: cambio aditivo del
CONTRATO cli-skopos-query (compatible según su propia cláusula).
Ataca directamente el defecto 3 y el **motor del eco** (egreso acotado
por consulta). Trade-off declarado (ronda 6, R6-8): con 64 KiB, el
46.5% de los turnos se sirve truncado (marcado); 20×64 KiB = 1.25 MiB
por consulta sigue siendo holgado para ventanas de contexto típicas —
los defaults exactos son afinables en implementación, la palanca es la
acotación misma. Nota de interacción (R6-5): la señal de exclusión y
el `limit` deben componer con el filtro de vigencia de ADR-007
(versiones superseded no consumen cupo) — sobre-fetch o agregación;
detalle de implementación registrado, no impedimento.

## Y-5: cierre obligatorio en cualquier combinación

El plan dispone que ninguna combinación deja abierto el fallo silencioso
de `cli.py:28-34`. Con P4a, el cierre es la verificación de hash. Sin
P4a, el mínimo aceptable (ronda 6, R6-3) es doble: (i) reemplazar el
`None` silencioso por un estado explícito en la salida
(`origen_perdido`), y (ii) **chequeo de longitud** — una lectura corta
(`bytes leídos ≠ offset_fin − offset_inicio`) no es un fragmento válido
y hoy se sirve parcial o vacía en silencio, porque `seek` fuera de EOF
no falla. Barato, sin sello, y parte de la implementación de cualquier
combinación.

## Combinación recomendada

**P4a (sellar) + P5 (límite/presupuesto) + P3 (declarativa), manteniendo
P1 (servir crudo sellado y acotado); P2 rechazada por ahora.**

- P4a cierra Y-5 con costo despreciable y sin tocar la semántica de la
  evidencia.
- P5 acota el motor del eco y da la señal de exclusión que C-4 pidió.
- P3 declara el contrato de consumo; gratis y honesta sobre sus límites.
- P2 se rechaza por sus argumentos (a)–(c); mitigada por P3+P5 y
  reversible (cambio de lectura, sin reingesta) si Fase 5 muestra
  contaminación real.
- P4b se rechaza por ahora: duplica almacenamiento, choca con el límite
  BSON en turnos gigantes medidos, y su único aporte (consulta sin
  archivo origen) no responde a un problema sentido hoy. Reabrible con
  evidencia (p.ej. si los rollouts empiezan a rotar y perderse).

## Consecuencias (si se acepta la combinación recomendada)

- (+) Y-5 cerrado con verificación; eco acotado por consulta; consumidor
  informado de qué quedó fuera; contrato de consumo declarado.
- (−) La verificación de hash añade una lectura completa del fragmento
  por resultado servido (I/O ya presente hoy; el hash es marginal).
- (−) Turnos con fragmento > tope se sirven truncados (con marcador) —
  el consumidor que necesite el completo tiene `ruta_origen`+offsets.
- (−) El sello se aplica a ingesta nueva; documentos ya guardados (0
  hoy) quedarían sin sello y se servirían con `sellado: false`
  (chequeo de longitud únicamente; o se sellan retroactivamente vía
  supersede, ahora posible — decisión de implementación). *(Deriva
  corregida por la implementación: no existe el estado
  `integridad_no_verificada` que esta sección pre-decisión anunciaba;
  los cuatro estados reales están en "Decisiones de implementación",
  que manda — ronda 8, H5.)*
- Cambios de superficie: `skopos query` gana `--max`/tope y campos de
  exclusión/truncado/estado en la salida (aditivos); CONTRATO
  cli-skopos-query v1 enmendado al implementar.

## Firma de decisión

- Dueño: firma 🔒 comunicada en canal del agente y confirmada con
  revisión aprobatoria de Pinax (2026-08-20) · Palancas: **P4a + P5 +
  P3, manteniendo P1; P2 y P4b rechazadas por ahora**
- Exigencia de la firma, registrada (restricción de orden de Pinax):
  ningún piloto de Fase 3c/5 ingesta a Mongo hasta que el sello de P4a
  exista — si no, el retro-sello deja de ser gratis. Sello implementado
  en el mismo commit que esta firma.

## Decisiones de implementación (cerradas al implementar, 2026-08-20)

- **Campo**: `fragmento_sha256` en `Turno`→`Analisis`→documento (sello
  fragmento-only; tamaño derivable de los offsets por construcción, no
  se duplica). Computado en `captura` al extraer (re-lectura del rango
  por turno: costo despreciable frente al análisis, que domina por
  órdenes de magnitud).
- **Servido** (`cli._servir_fragmento`): estados
  `integro`/`truncado`/`origen_perdido`/`integridad_fallida` + flag
  `sellado` (false = sin sello: legado o captura con archivo ilegible).
  Ante longitud leída ≠ esperada, rango inválido (`esperado <= 0`,
  ronda 8 H2) o sha256 discordante → `fragmento_completo: null` (nunca
  bytes no verificados); `origen_perdido` para OSError. El chequeo de
  longitud aplica también a legados sin sello (mínimo Y-5, R6-3). El
  marcador exacto: `\n…[fragmento truncado: servidos X de Y bytes]`
  (añade ~55 bytes fijos sobre el tope; el corte puede partir un
  carácter multibyte → U+FFFD — ronda 8, H3/H4/H6).
- **P5**: `--max` (default 20) sobre vigentes ya filtrados (ADR-007) —
  versiones superseded no consumen cupo (R6-5); tope de fragmento 64
  KiB como constante (`TOPE_FRAGMENTO_BYTES`) con marcador
  `…[fragmento truncado: X de Y bytes]`; señal `excluidos.por_limite`.
- **P3**: declaración dato-nunca-instrucción en el CONTRATO
  cli-skopos-query v1 (aditiva).
- **Retro-sello**: innecesario hoy (colección con 0 documentos,
  verificado 2026-08-20); si algún documento legado apareciera, se
  sella vía supersede (`superseder_documento` con
  `fragmento_sha256`), ya posible por ADR-007.
- **Reanalizar modo completo**: propaga el sello recomputado del Turno
  re-extraído (el rango no cambia ante appends; cambia si el archivo
  fue editado — y entonces el sello nuevo describe la realidad nueva).
