# Ronda 23 — adversarial sobre la implementación de ADR-011 (2026-08-28)

**Objeto:** el cursor de lectura incremental recién escrito —
`src/skopos/cursor.py`, el soporte en `parseo.py`/`captura.py` y el
enrutado en `orquestador.py`/`vigilante.py`— antes de commitear.

**Método — con su límite declarado:** revisión del mismo agente que
escribió el código, buscando activamente formas de perder datos, con
**verificación por ejecución** de cada sospecha (no sólo lectura). No es
un revisor de contexto fresco ni una revisión de Pinax: vale como filtro
de calidad, no como gate independiente.

**Veredicto:** **CORREGIDO** — 4 hallazgos (2 ALTO, 2 MEDIO), los cuatro
arreglados y cubiertos con tests antes del commit; 1 desviación de
contrato declarada, no corregida, por ser inherente al diseño aceptado.

## Hallazgos

| Id | Nivel | Hallazgo | Cómo se verificó | Destino |
|---|---|---|---|---|
| C1 | **ALTO** | El cursor adelantaba turnos cuyo análisis había fallado. Ese turno no está en Mongo, así que **no se volvería a leer nunca**: el cursor dejaba de ser caché inofensiva y pasaba a ser pérdida silenciosa | Razonamiento sobre el flujo + test que falla sin la corrección | Corregido: `congelado` en el primer `fallido`; los `omitido` sí avanzan (no exigen reintento) |
| C2 | **ALTO** | `proyecto` sale del último `turn_context`, que en incremental queda **por debajo** del cursor: todos los turnos nuevos habrían salido con `proyecto=None`, hundiendo el eje de C-9 sin avisar | Ejecutado: lectura completa daba `skopos`, la incremental `None` | Corregido: herencia por `rfind` de bytes hacia atrás — no reparsea el prefijo |
| C3 | MEDIO | `version_cli_observada` se degradaba a `None` en incremental (el `session_meta` está en la cabecera) | Ejecutado: `0.147.0` vs `None` | Corregido: se lee de la cabecera, en el mismo alcance de escaneo que la identidad |
| C4 | MEDIO | El almacén no olvidaba nunca; cada sesión archivada, renombrada o borrada dejaba su entrada para siempre | Lectura del módulo: no existía ninguna operación de baja | Corregido: `podar()` por ciclo contra los archivos descubiertos |

## Desviación declarada (no corregida)

`eventos_no_reconocidos` y `descartes_linea` cuentan el **tramo leído**,
no el archivo — la letra de ADR-010 §3 dice "total por archivo". Afirmar
el total exigiría reparsear todo, que es precisamente lo que el cursor
evita. Se elige el conteo honesto de lo leído sobre un total inventado, y
queda anotado en ADR-010 §3 y en ADR-011.

## Lo que la ronda confirmó sano

- Un archivo sin turnos cerrados **no** recibe cursor: avanzar a EOF
  saltaría el texto acumulado sin cierre y mutilaría el turno siguiente.
  Son 11 de 643 archivos que se reparsean enteros cada ciclo, a
  propósito.
- El cursor **nunca** sustituye a la detección: un archivo sin identidad
  da `formato_desconocido` aunque traiga cursor (testeado).
- La lectura incremental produce turnos **idénticos** a la completa,
  campo por campo, incluidos offsets y `fragmento_sha256` (testeado).
- `--backfill` ignora los cursores; el cursor recuerda lectura, no
  ingesta.

## Estado tras la ronda

159 tests OK (137 previos + 22 nuevos). Las cuatro correcciones se
incorporaron al **texto del ADR-011** como cláusulas de la decisión, no
como notas de implementación: sin ellas, el ADR prometería algo que el
código no cumple.
