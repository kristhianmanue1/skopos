# Evidencia · lectura incremental con cursor (ADR-011 implementado)

**Fecha:** 2026-08-28. **Alcance:** implementación de **ADR-011**
(aceptado 🔒 2026-08-28) — Hito 15 / C-10(b).
`src/skopos/cursor.py` (almacén), soporte en `parseo.py` y `captura.py`,
enrutado en `orquestador.py` y `vigilante.py`.

## Qué se construyó

- **`Cursor(offset, digest_prefijo)`** por archivo, persistido en
  `~/.local/state/skopos/cursores.json` — fuera del repo, borrable,
  regenerable. Escritura atómica (`tmp` + `os.replace` + `fsync`); un
  almacén corrupto o de versión desconocida se trata como vacío.
- **Validación por contenido**: el cursor sólo se usa si el `sha256` del
  prefijo sigue casando byte a byte. Rotación, edición o truncación ⇒ se
  descarta y se reparsea entero. `tamaño+mtime` sigue prohibido
  (ADR-010 §5).
- **Poda por ciclo**: las entradas de archivos que ya no se descubren se
  olvidan; si no, el almacén crecería para siempre.
- **Sin cursores en `--backfill`**: releerlo todo es el encargo.

## Medición sobre el corpus real (643 archivos, 2.42 GB)

Read-only, con almacén efímero: ni Mongo ni Ollama. **El load va al lado
de cada cifra** — sin él, estos números no son comparables (regla de la
ronda 4).

| Corrida | Ciclo frío (sin cursor) | Ciclo 2 | Ciclo 3 | Load |
|---|---|---|---|---|
| Máquina muy cargada | 44.7 s | **9.3 s** (4.8×) | 11.4 s (3.9×) | 40 → 46 |
| Máquina menos cargada | 13.9 s | **3.7 s** (3.7×) | 4.9 s (2.8×) | 8.9 → 7.8 |

- **632 de 643 archivos** se leen incrementalmente. Los 11 restantes son
  los que no tienen ningún turno cerrado: **no reciben cursor a
  propósito** (avanzar hasta EOF saltaría el texto acumulado sin cierre
  y mutilaría el turno siguiente).
- Con carga normal el ciclo cae a **3.7–4.9 s contra un intervalo de
  5 s**: la condición que abrió el hito 15 —el ciclo tarda más que su
  intervalo— **deja de cumplirse**, que era exactamente el objetivo.
- Bajo carga extrema sigue por encima del intervalo (9.3 s), pero 4.8×
  mejor que antes. El cursor no compra inmunidad a una máquina saturada;
  compra que el trabajo escale con lo nuevo y no con el corpus.

## Corrección: los turnos incrementales son idénticos a los completos

El riesgo del cursor no es la velocidad, es producir turnos distintos.
Verificado en tests: una lectura incremental produce los mismos `Turno`
que la completa **campo por campo, incluidos `offset_inicio`,
`offset_fin`, `fragmento_sha256` y `proyecto`** — los offsets siguen
siendo de la instantánea completa, así que el sello P4a y el fragmento
servido no cambian de semántica.

## Ronda 23 (adversarial sobre esta implementación)

Cuatro hallazgos, los tres primeros verificados ejecutando:

| Id | Nivel | Hallazgo | Estado |
|---|---|---|---|
| C1 | **ALTO** | Un turno cuyo análisis falla no está en Mongo; si el cursor lo adelanta, **no se vuelve a leer nunca**. La dedup no puede rescatarlo porque nunca lo vio | Corregido: el avance se congela en el primer `fallido`; los `omitido` sí avanzan |
| C2 | **ALTO** | `proyecto` viene de un `turn_context` anterior al cursor: toda lectura incremental lo degradaba a `None`, hundiendo el eje de proyecto de C-9 en silencio | Corregido: herencia por búsqueda de bytes hacia atrás, sin reparsear el prefijo |
| C3 | MEDIO | `version_cli_observada` salía `None` en incremental (el `session_meta` queda bajo el cursor) — verificado: `0.147.0` vs `None` | Corregido: se lee de la cabecera, en el mismo alcance que la identidad |
| C4 | MEDIO | El almacén no olvidaba nunca: cada sesión archivada o borrada dejaba su entrada para siempre | Corregido: poda por ciclo contra los archivos descubiertos |

**Desviación declarada, no corregida:** `eventos_no_reconocidos` y
`descartes_linea` pasan a contar el **tramo leído**, no el archivo, lo
que se aparta de la letra de ADR-010 §3 ("total por archivo"). Afirmar
el total exigiría reparsear todo — justo lo que el cursor evita. Se
prefiere un conteo honesto de lo leído a un total inventado; queda
anotado en ADR-010 §3 y en ADR-011.

Las cuatro correcciones se incorporaron al ADR-011 como cláusulas de la
decisión, no como notas al margen: sin ellas el cursor no es la caché
inofensiva que el ADR promete.

## Verificación

**159 tests OK** (137 previos + 22 nuevos: `tests/test_cursor.py` con
lectura incremental, herencia de estado, validación del sello, almacén y
poda; más `AvanceDelCursorTests` en `tests/test_orquestador.py` para la
regla del turno fallido).
