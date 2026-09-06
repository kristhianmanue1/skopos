# ADR-013: cursor incremental para orígenes de filas — opencode entra al vigilante

Estado: **aceptado** — decisión 🔒 del dueño, 2026-09-06. Implementado el
mismo día: marca de agua en `skopos-cursores/v2` (`cursor.py`),
`extraer_delta` sobre la máquina de estados única (`opencode.py`),
`procesar_base_filas` en el orquestador y `FUENTE_FILAS_POR_DEFECTO` en
el vigilante. Revoca el §d de ADR-012 en el punto exacto que declara
("eso sería otro ADR, con su propia evidencia"); no toca nada más de
ADR-012.

## Contexto

ADR-012 §d decidió no tener cursor para orígenes de filas midiendo el
**barrido crudo** de la base (0.7 s: 52,742 mensajes + 227,881 partes).
El cierre del 2026-08-28 detectó el punto ciego: la decisión se tomó
sobre el barrido, no sobre la **extracción completa** — decodificar el
JSON de cada parte y derivar turnos. Medido hoy sobre la base real
(`~/.local/share/opencode/opencode.db`, 4.4 GB):

| Medición (2026-09-06) | Costo |
|---|---|
| `extraer_de_base` completa | **18.34 s** → 4,253 turnos, 0 no reconocidos |
| Delta 24 h (`WHERE time_created > ?`) | **7.2 ms** → 702 filas |
| Plan de la consulta delta | `SCAN message USING COVERING INDEX message_session_time_created_id_idx` (0.09 ms) |
| Escaneo puro de `message` | 5.8 ms (56,665 filas) |

Es el patrón ya registrado dos veces en este proyecto: *una medición
correcta pero incompleta lleva a una decisión equivocada*. 18.34 s por
ciclo satura al vigilante (presupuesto: ciclo ≤ 5 s, ADR-008/ADR-011) —
por eso opencode está fuera de `FUENTES_POR_DEFECTO` y se indexa a
mano. El corpus de opencode (el segundo más grande) queda sin
observación continua por un costo que **sólo paga la parte vieja**: los
turnos cerrados hace una semana no necesitan re-derivarse cada ciclo.

## Decisión propuesta

### (a) Marca de agua por `time_created`, servida por el índice existente

`time_created` es monótono y opencode ya mantiene un índice cubriente
`(session_id, time_created, id)` sobre `message`. El cursor de filas
guarda una **marca de agua**: el `time_created` del mensaje de usuario
abierto más antiguo cuya turno aún no cierra. Cada pasada lee
`WHERE time_created >= marca` (7 ms medidos) y deriva turnos cerrados
con la misma máquina de estados de `extraer_de_base` — usuario abre,
usuario siguiente cierra, un turno nunca cruza de sesión.

La ventana acotada **incluye siempre el turno abierto completo**, porque
la marca de agua es su mensaje de apertura: el sello canónico
(ADR-012 §c) se computa sobre todas las filas del turno, sin excepción.

### (b) Sin marca de agua → extracción completa (degradación honesta)

El cursor sigue siendo **caché, nunca fuente de verdad** (ADR-011
intacto; la dedup autoritativa vive en Mongo, ADR-005). Almacén
ausente, corrupto o con la base movida: una pasada completa de 18 s,
jamás pérdida silenciosa. Formato del almacén: entrada aditiva
`skopos-cursores/v2` junto a las entradas de archivo existentes, que no
cambian.

### (c) opencode como fuente propia del vigilante

`FUENTES_POR_DEFECTO` gana la base como fuente de filas (una ruta, no
un globo): `ciclo()` la despacha por su tipo y el resto del vigilante
(presupuesto, reporte, índice P-004, `--solo-indice`) la trata igual
que un archivo. El backfill de opencode sigue siendo explícito
(`skopos indexar`, ADR-008).

### (d) El presupuesto queda medible

Costo esperado por ciclo con opencode incluido: ciclo actual de
archivos (3.7–4.9 s) + delta de filas (fracción de segundo: ventana del
turno abierto, no 24 h — 702 filas de un día completo costaron 7.2 ms).
Si una pasada delta supera el presupuesto (base gigante, turno abierto
anormal), el vigilante la reporta y **no** la reintenta dentro del mismo
ciclo.

## Alternativas descartadas

- **Cursor por `rowid`**: ADR-012 ya lo rechazó para dedup (reasignable
  tras `VACUUM`); como marca de agua tendría el mismo defecto. El
  `time_created` es el campo que la fuente declara monótono.
- **Espejo JSONL exportado**: rechazado en ADR-012 por deshonesto con
  la garantía del §5 — nada cambia.
- **Consultar por sesión viva en vez de por marca de agua global**:
  obligaría a adivinar qué sesión está "viva"; la marca de agua mínima
  entre turnos abiertos es equivalente y no adivina nada.

## Consecuencias (si se acepta)

- opencode entra a `watch`: observación continua del segundo corpus del
  ecosistema sin llamadas al modelo (P-004) y sin superar el presupuesto
  de ciclo.
- La extracción completa queda como camino de cold-start y de
  recuperación de caché — su costo deja de ser recurrente.
- El §d de ADR-012 queda revocado en su conclusión (no había cursor
  porque no hacía falta — con la medición completa, hace falta) y
  cumplido en su espíritu ("eso sería otro ADR, con su propia
  evidencia": este documento).
- `documento-analisis-mongo` sigue en v2: este ADR no toca análisis
  (Ollama), sólo observación e índice.

## Lo que este ADR NO decide

No decide cuándo se analiza opencode con Ollama (la ruta de análisis y
el salto a v3 del contrato de análisis siguen en su propia cola), ni
toca ADR-008 (backfill), ni introduce escrituras en la base de
opencode — la conexión sigue siendo de sólo lectura.

## Firma de decisión

- Dueño: decisión 🔒 **"aceptado y adelante"** · Fecha: **2026-09-06** ·
  Sobre las mediciones de esta misma sesión (reproducibles con
  `skopos.opencode.extraer_de_base` y sqlite3 contra la base real).
- **Implementado el mismo día**, con una salvedad de diseño registrada:
  la §a decía "marca de agua = mensaje de usuario abierto más antiguo";
  la implementación la simplificó a `max_visto + 1` **sin perder la
  garantía** — la ventana siguiente re-deriva cada turno abierto desde
  su abridor, buscado hacia atrás por el índice cubriente
  (`_abridor_previo`, ≤ 200 filas por sesión activa), de modo que el
  sello canónico se computa siempre sobre las filas completas del
  turno. Verificación sobre la base real: sellos de la delta
  **byte-idénticos** a los de la lectura completa (43/43 en la ventana
  de prueba), delta 24 h en 91.8 ms.
