# ADR-007: superficie de reparación del almacén de Skopos

Estado: **propuesto — decisión 🔒 pendiente del dueño** (Fase 2 / C-8 del
ciclo P-002, 2026-08-20). Al decidir el dueño, se completa la firma, el
estado pasa a aceptado y la alternativa elegida queda registrada.

## Contexto

El almacén es insert-only por diseño: `guardar_analisis` sólo hace
`insert_one` (`almacenamiento.py`), `turn_id` es único por índice y el
flujo es primer-análisis-gana. No existe `update_one`/`delete_one` en
`src/`.

La justificación original de C-8 (P-001 §4.2: "la vigencia consolidada
[de AN-KLA] se pudre en Skopos") **murió con P-001** (superada por la
decisión multi-CLI, 2026-08-20). Este ADR la re-justifica desde cero en
el mundo multi-CLI, donde cuatro necesidades concretas no tienen
reparación posible hoy:

1. **No determinismo de Ollama.** Un análisis malo (tema errado,
   resumen alucinado) queda petrificado. Con parsers de N CLIs, un bug
   de parser producirá análisis malos **a escala**, sin forma de
   corregirlos.
2. **Redacción por patrones.** `_PATRONES_SECRETOS` cubre formatos
   conocidos; un patrón descubierto mañana no puede aplicarse a lo ya
   guardado — un secreto en claro persiste para siempre en
   `tema`/`resumen`/`entidades`.
3. **Legacy de C-9.** Los documentos pre-C-9 no tienen `proyecto` y no
   pueden completarse (backfill) sin superficie de escritura.
   *Nota honesta (ronda 2, H3): hoy es conjunto vacío — la colección
   tiene 0 documentos (verificado 2026-08-20) y C-9 ya está desplegado
   antes de cualquier backfill; la necesidad queda como caso condicional
   (documentos escritos por un proceso con código pre-C-9), no como
   motivación vigente.*
4. **C-6 opción 4 retroactiva.** Sellar orígenes ya guardados con
   hash+tamaño exige escribir sobre documentos existentes.

A ellas se suma una quinta, de otra clase: **retención/privacidad**
(rutas absolutas persistidas — riesgo declarado en README; sin
expiración; multi-CLI multiplica volumen y sensibilidad).

## Necesidades vs alternativas

| Necesidad | A · Retención (TTL) | B · Supersede con versiones | C · Mutación plena |
|---|---|---|---|
| 1. Reanalizar turno mal analizado | ✗ | ✓ | ✓ |
| 2. Redacción retroactiva | ✗ | ✓ *exposición*: la vigente se sirve redactada; el secreto **permanece** en versiones superseded (store, índice `$text`, backups) — borrarlo exige componer con retención/borrado (ADR futuro) | ✓ |
| 3. Backfill `proyecto` legacy | ✗ | ✓ (conjunto vacío hoy, ver contexto) | ✓ |
| 4. Sellado hash+tamaño retroactivo | ✗ | ✓ | ✓ |
| 5. Acotar retención/privacidad | ✓ (por edad) | ✗ | ✓ (selectivo) |
| Proveniencia/auditoría | ✗ (borra) | ✓ (historia completa) | ✗ (salvo esfuerzo extra) |
| Insert-only | ✓ de aplicación (el TTL **borra físicamente**) | ✓ físico | ✗ |

## Decisión propuesta: B — supersede con versiones, por inserción

Desviación consciente respecto de P-002 §3.2 (ronda 2, H4): la
alternativa (2) se describía ahí como "marcar la vieja con
`reemplazado_por`" — lo que exige escribir sobre un documento existente
y contradice el insert-only que la misma frase prometía. Este ADR usa
**vigencia implícita** (la versión de número mayor) en su lugar: ningún
marcador se escribe sobre documentos viejos.

- Reanalizar un turno inserta una **versión nueva** del documento
  (versión N+1); el índice único pasa de `turn_id` a
  `(turn_id, versión)`; la **versión vigente es la de número mayor**.
- **Ningún documento existente se modifica ni se borra**: el
  insert-only físico queda intacto; "reemplazado" es implícito (existe
  una versión mayor), no un campo escrito sobre el viejo.
- `existe_turn_id` pasa a significar "existe cualquier versión": el
  vigilante omite el turno igual que hoy y **jamás reanaliza por sí
  mismo** — supersede es una operación explícita, disparada por
  comando, nunca automática.
- Las lecturas que sirven datos (`buscar_por_tema`, `skopos query`, y
  el futuro `skopos read` por `ocurrido_en` — ronda 2, H9) devuelven
  sólo la versión vigente. `existe_turn_id` NO filtra por vigencia, por
  diseño: es dedup (H6).
- La asignación de versión bajo concurrencia (dos supersede simultáneos
  toman el mismo N+1) la resuelve el índice único compuesto: uno falla.
  **Ojo (ronda 2, H2): hoy `orquestador.py` trata `DuplicateKeyError`
  como "omitido" sin reintento — correcto para ingesta, inaceptable
  para un comando explícito de reparación.** El supersede reintenta
  re-computando max(versión); el fallo silencioso de una reparación
  pedida a mano no es opción.
- Habilita las necesidades 1, 2 (exposición; ver residual en la tabla)
  y 4 con auditoría, y la 3 condicionalmente. **No cierra la puerta**
  a A: si el almacenamiento o la privacidad se vuelven problema medido,
  la retención se compone encima como ADR propio.

Alternativas descartadas:

- **A · Retención (índice TTL sobre `creado_en`/`ocurrido_en`).** No
  repara nada de la tabla (1–4): borra por edad, no por defecto. Borra
  evidencia (el fragmento de origen queda sin análisis que lo
  referencie) y choca con el espíritu de REQ-4 — la recuperación de
  conversaciones pasadas deviene imposible por antigüedad (paráfrasis
  del espíritu, no cita literal — ronda 2, H7). Su aporte de
  privacidad es acotado: elimina por antigüedad, no por sensibilidad.
  Diferida como capa componible, no rechazada de raíz.
- **C · Mutación plena (`update`/`delete` expuestos).** La más flexible
  y la más peligrosa: rompe la garantía por construcción que hace
  confiable al almacén (lo que leíste no cambió por debajo), no
  conserva historia salvo esfuerzo extra, y abre una superficie de
  gobierno nueva (quién puede borrar qué, cuándo). En un sistema cuyo
  propósito es recordar, el borrado silencioso es el peor modo de
  fallo. AN-KLA resolvió la misma tensión con CAS + supersede gobernado
  por razones análogas.

## Consecuencias (si se acepta B)

- (+) Reanálisis, redacción retroactiva (de exposición), sellado
  retroactivo y backfill condicional quedan habilitados con historia
  completa.
- (+) Componible con retención futura (ADR propio si la evidencia lo
  pide).
- (−) **El filtro de vigencia es una carga de seguridad, no sólo
  complejidad** (ronda 2, H1): toda lectura que lo olvide sirve la
  versión vieja — incluido un secreto pre-redacción. Afecta
  `buscar_por_tema`, `skopos query`, el futuro `skopos read` por
  `ocurrido_en` (H9) y cualquier consumidor externo.
- (−) El almacenamiento crece monótonamente: cada supersede duplica el
  documento. Aceptado de inicio; la tabla de arriba deja claro qué se
  compra con eso.
- (−) El CONTRATO documento-analisis-mongo exige **v2** (unicidad
  compuesta, campo `version`, semántica de vigencia) y SPEC-003 se
  enmienda — cambio enunciado, no ajuste silencioso. **La migración no
  es sólo crear el índice compuesto** (ronda 2, H5): hay que retirar el
  `create_index("turn_id", unique=True)` que `coleccion_local` ejecuta
  en cada arranque, bajar el índice viejo, y tolerar que un proceso con
  código viejo corriendo en paralelo lo resucite (hoy: única instancia
  local; el riesgo queda documentado).
- Puntos de diseño diferidos a la implementación (tras la 🔒):
  disparador exacto del supersede (comando, p.ej. `skopos reanalizar`),
  nombre del campo de versión, política de copia hacia adelante de
  campos, y la semántica de reintento con re-cómputo de versión (H2).

## Firma de decisión

- Dueño: ______ · Fecha: ______ · Alternativa elegida: ____
