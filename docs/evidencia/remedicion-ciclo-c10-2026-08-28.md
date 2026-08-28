# Evidencia · remedición del ciclo del vigilante (gate de C-10(b) / Hito 15)

**Fecha:** 2026-08-28. **Código:** `main@423c458` (ingesta ya enrutada por
la frontera de SPEC-006). **Propósito:** el gate que el plan del ciclo
fija para abrir el ADR de lectura incremental — *un ciclo completo del
vigilante tarda más que su intervalo* — medido con el **load registrado
al lado**, que es la regla de comparabilidad que impuso la ronda 4
(H1/H2) tras ver el mismo parseo en 9.5 s y 50.8 s el mismo día.

Método: read-only. Descubrimiento (`rglob` + `stat`) más `parsear()` de
cada archivo — lo que el ciclo ejecuta antes de tocar Mongo u Ollama.
Ni se escribió en Mongo ni se llamó a Ollama. Skopos **no** quedó
corriendo.

## Corpus y ciclo

| Dato | Valor |
|---|---|
| Archivos descubiertos | 643 |
| Tamaño | 2.42 GB |
| Descubrimiento (`rglob` + `stat`) | 0.01 s |
| Intervalo por defecto del vigilante | 5.0 s |

| Pasada | Parseo completo | Turnos | Load (inicio→fin) | Ratio vs intervalo |
|---|---|---|---|---|
| 1 | **22.6 s** | 16,252 | 7.89 → 8.31 | 5× |
| 2 | **33.3 s** | 16,252 | 8.31 → 11.65 | 7× |
| 3 | **39.1 s** | 16,252 | 11.65 → 14.85 | 8× |

**La máquina estaba cargada** (load 7.9–14.9, con el watcher de
escrubery y otros trabajos vivos), así que estas cifras son el extremo
alto. No hace falta discutir el extremo: **el criterio del gate se
cumple en todas las mediciones que existen**, cargadas o no — la más
rápida jamás registrada de este parseo es 9.5 s (snapshot 2026-08-20,
612 archivos), casi el doble del intervalo de 5 s, y el corpus sólo ha
crecido desde entonces (612 → 643 archivos).

**El argumento estructural pesa más que el número:** el trabajo por
ciclo escala con el **tamaño del corpus**, no con lo que llegó nuevo.
Hoy se re-parsean 2.42 GB cada 5 segundos para encontrar, casi siempre,
cero turnos nuevos. Eso no mejora con una máquina más rápida: empeora
con cada sesión que se archiva.

## Dónde se va el tiempo (lo que decide el diseño del cursor)

Medido sobre el mismo corpus, en la misma corrida y con el mismo load:

| Operación | Tiempo | Qué implica |
|---|---|---|
| Leer la instantánea de todo el corpus | **5.0 s** | El I/O no es el problema |
| Leer + `sha256` del prefijo completo | **7.0 s** | Validar un cursor por digest completo cuesta 2 s sobre el I/O |
| `sha256` de una ventana de 64 KiB por archivo | **0.21 s** | Validación acotada, garantía más débil |
| **Parsear (JSON por línea)** | **22.6–39.1 s** | **Aquí se va el ciclo entero** |

Conclusión operativa: **el coste dominante es el parseo de JSON, no la
lectura**. Un cursor que evite re-parsear lo ya visto ataca el 80–90 %
del ciclo aunque siga leyendo los bytes; y si además se valida con
digest de prefijo completo (7.0 s), sigue siendo 3–5× más barato que el
ciclo actual.

## Restricción que hereda del ADR-010 §5

El cursor **no puede** validarse con `tamaño+mtime`: el §5 prohíbe
expresamente volver a esa comparación entre dos lecturas. Cualquier
diseño tiene que verificar con evidencia de contenido (digest) o
declarar explícitamente qué garantía sacrifica. Las dos filas medias de
la tabla de arriba son justamente las dos opciones que respetan esa
restricción, con sus precios.

## Estado del gate

**Cumplido.** La condición que el plan exigía para abrir el ADR de
lectura incremental está satisfecha con evidencia fechada y con el load
registrado. La decisión sobre *qué* diseño adoptar es 🔒 del dueño —
propuesta en `docs/adr/ADR-011-lectura-incremental.md` (estado:
propuesto).
