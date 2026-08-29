# Evidencia · ficha del adaptador parser-opencode/v1 (fase B completa, 5 de 5)

**Fecha:** 2026-08-28. **Base:** ADR-012 (aceptado 🔒 el mismo día).
**Origen:** `~/.local/share/opencode/opencode.db` — SQLite de 4.4 GB con
879 sesiones, 52,741 mensajes y 227,875 partes.

Es el **primer adaptador de origen de filas**: no lee bytes de un
archivo, lee filas de una base.

## Cómo se honran las tres garantías del §5

| Garantía del §5 | En un archivo | Aquí |
|---|---|---|
| Instantánea consistente | `fstat` + leer N bytes | **transacción de lectura** (snapshot de SQLite) |
| Fragmento sellado | rango `[inicio, fin)` de bytes | **serialización canónica de las filas** del turno |
| Localización | `ruta` + offsets | `ruta` + `tabla` + **ids de fila** |

**Verificado, no afirmado:** se recuperaron 3 fragmentos releyendo sus
filas por id, re-serializando en canónico y recomputando el `sha256`:
**3/3 sellos reproducidos**. El invariante *"todo turno es resoluble a
bytes sellados"* sobrevive intacto; lo que cambió es cómo se direcciona,
no si se puede verificar.

## Resultado sobre la base real

| Medida | Valor |
|---|---|
| Diagnóstico | **`ok`** |
| Turnos extraídos | **3,909** |
| Tiempo de extracción | 11.7 s |
| Eventos no reconocidos | 0 |
| `version_cli_observada` | 1.17.7 |

Ejemplo de turno: `opencode:msg_ffe1d67a1001EsjfEPA8ht7q6A`, proyecto
`entiendomidiabetes`, **25 filas** componiendo el fragmento,
`offset_inicio = None`, `ocurrido_en = 2026-08-14T02:41:15.674Z`.

## Decisiones de ficha

- **Identidad**: cabecera `SQLite format 3\0` **más** las tablas
  `session`/`message`/`part`. Se comprueba **sin materializar** la base:
  16 bytes y una consulta al catálogo. Una base SQLite ajena no casa.
- **`turn_id` calificado** `opencode:{message_id}` (ADR-010 §7).
- **Cierre derivado** de usuario a usuario, como claude-code y cline;
  opencode no marca fin de turno. Además, **un turno nunca cruza de
  sesión**: al cambiar `session_id` se cierra el que estuviera abierto.
- **`proyecto`** de `session.directory` con la regla C-9 (79 directorios
  distintos en el corpus).
- **`ocurrido_en`** de `time_created`, epoch en milisegundos → ISO 8601
  UTC. Es la **tercera vez** que aparece esta trampa (cline, kimi,
  opencode): sin convertir, ADR-008 trataría todos los turnos como
  históricos y no entraría ninguno.
- **`reasoning` fuera del texto del agente** (28,775 partes), como
  `thinking` en cline y kimi.
- **Sin cursor**, medido: un barrido completo de la base cuesta 0.7 s
  contra los 3.7 s del ciclo de archivos con cursor.

## Nuance del contrato que este adaptador destapó

Una base SQLite **ajena** (sin las tablas de opencode) no la reclama
ninguna ficha de filas, cae al camino de archivo, y allí un binario no
decodifica como UTF-8: el diagnóstico es **`entrada_corrupta`**, no
`formato_desconocido`. Es lo que ADR-010 §3 dice literalmente
("decodificación imposible") y la precedencia total lo confirma, pero
conviene saberlo: para el contrato, "no es texto" y "está corrupto" son
el mismo diagnóstico. Queda registrado en un test con su explicación.

## Índice reconstruido: los cinco CLIs

Al añadir el localizador, los 19,826 turnos ya indexados quedaban sin
`origen_tipo`. En vez de dejar semántica de legado, **se reconstruyó el
índice entero** — es dato derivado, reproducible desde las fuentes:

| CLI | Turnos |
|---|---|
| codex-cli | 15,406 |
| opencode | **3,909** |
| claude-code | 1,848 |
| kimi-code | 1,637 |
| cline | 70 |
| **Total** | **22,870** |

Reconstrucción completa: **65.9 s**. 213 MB de datos, 99 MB almacenados.
Búsqueda `$text`: 1-7 ms. Por tipo de origen: 18,961 archivo, 3,909
filas.

**Deriva del corpus declarada:** codex bajó de 645 a 622 archivos entre
la medición de la mañana y esta — el propio Codex archivó 79 sesiones en
`~/.codex/archived_sessions` durante la sesión de trabajo. Los conteos
se citan como snapshot de su corrida (regla X-2), no como constantes.

## Verificación

**216 tests OK** (205 previos + 11 nuevos en `tests/test_opencode.py`:
identidad sin materializar, rechazo de base ajena, no-robo de identidad
frente a un JSONL, cierre derivado, ausencia de offsets con localizador
de filas, sello reproducible, turno que no cruza de sesión, proyecto,
timestamp y sesión sin cierres).
