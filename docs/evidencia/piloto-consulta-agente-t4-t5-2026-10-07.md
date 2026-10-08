# Piloto de consulta desde agente — T4 y revisión T5

Estado: ejecución comparativa cerrada; evaluación semántica y adjudicación de
utilidad pendientes. Fecha: 2026-10-07. Autor y autorrevisor: Codex, misma
instancia. No constituye revisión independiente ni aceptación operativa.

## Identidad y lectura

Base de producto: Skopos `main@fe1e8cbf6fe521c3e45fb87e76acf38c5f476084`.
Cliente: OpenCode `1.18.35`; modelo solicitado:
`zai-coding-plan/glm-5.3-flash`. El modelo efectivo y el coste facturado
siguen sin telemetría independiente. El pie final personal de OpenCode fue
confirmado por el Operador como configuración intencional. Leer primero el
plan activo, luego el acta T0, los controles T1–T3 y este informe. Las
respuestas y recibos crudos están en los archivos indicados abajo.

## Serie congelada v0.4

El congelamiento `freeze-final.json` tiene SHA-256
`72aca9ded127b266ac598bdaca2bd59330cd09224a653587992200f61da7cc0c`.
Semilla `20261007`; 36 bloques de tarea-variante, con seis de cada una de las
seis permutaciones A/B/C. Corpus, código congelado, oráculo y rúbrica se
registran en ese archivo. Las 108 ejecuciones se iniciaron en sesiones
separadas, sin reintentos dentro de la serie. El progreso y las 108 carpetas
de slot constan en `series-v0.4`.

| Condición | Completadas | Fallidas | Mediana completadas | Máximo completadas | Entregas incorporadas/intentos |
|---|---:|---:|---:|---:|---:|
| A, referencia | 36 | 0 | 26 449,5 ms | 73 446 ms | 110/110 |
| B, Skopos explícito | 36 | 0 | 30 692,5 ms | 72 053 ms | 111/111 |
| C, Skopos prefetched | 35 | 1 | 29 646 ms | 89 039 ms | 136/136 |

Total: 107 completadas, una fallida, cero no iniciadas. Las medianas son
descriptivas de completadas y no implican ventaja causal. Los recibos prueban
correspondencia de entregas con el hook anterior a la llamada principal dentro
del harness; no capturan el cuerpo HTTP ni acreditan lectura semántica del
modelo. OpenCode reportó coste cero, que no acredita facturación cero. No se
mezclan los 28 intentos históricos v0.3.

El fallo v0.4 es slot `103-Q11-v2-C`, run
`Q11-v2-C-201c3db130e7`: intentó una novena llamada sobre el máximo ocho.
El hook la bloqueó, por lo que hay ocho pasos enviados y nueve hooks. Recibo
`model_call_budget_exceeded`; seis entregas sí se incorporaron antes del
bloqueo. No es un timeout ni una respuesta correcta omitida del denominador.

Las métricas mecánicas muestran la respuesta literal esperada en A 24/24,
B 23/24 y C 21/24 casos con valor literal; esto **no es la rúbrica de éxito**.
Por ejemplo, Q02-v1/B y Q02-v3/C no encontraron el valor disponible, y
Q11-v3/C tampoco. Q08/C fue más lento que A y B en sus tres variantes; en
Q08-v2/C hubo 15 errores de herramienta observados. La métrica no decide
procedencia, vigencia, abstención fundada ni violación de autoridad. Algunos
textos citan hashes abreviados; su respaldo requiere adjudicación explícita.

## Corrección acotada v0.5

Decisión posterior del Operador: ampliar el presupuesto sólo para los fallos.
En v0.4 hubo uno. Se creó una copia separada del arnés y del perfil, con
tope de llamadas 8→12 **sólo para Q11-v2/C**; permanecen 128 KiB acumulados,
3 búsquedas, 3 fetch, 5 resultados por búsqueda, 10 s por backend y 120 s por
turno. No se modificó el código congelado de v0.4; su copia y hashes se
conservan en `series-v0.4/frozen-code`. El manifiesto correctivo registra los
hashes del arnés usado.

Primer intento correctivo `Q11-v2-C-9a87209e0a99`: se invocó con Python del
sistema y el backend devolvió `ModuleNotFoundError: skopos` en todas las
consultas. El agente se abstuvo; cuatro llamadas, recibo de entrega positivo.
Es un **fallo del entorno correctivo** y queda conservado, no una medición
válida de utilidad.

Segundo intento `Q11-v2-C-e62ea8deb9e1`: se ejecutó con `.venv/bin/python`.
Tres llamadas y tres entregas incorporadas, recibo positivo, 21 677 ms,
sin timeout. Consultó tres veces, pero respondió que no podía verificar el
valor. El oráculo congelado esperaba `Órbita-11` de `s018` revisión 1.
Por tanto, el transporte funcionó y la tarea **no** se resolvió. Este intento
usó sólo tres de las doce llamadas permitidas; no demuestra que ampliar el
presupuesto corrija el fallo original. Las dos repeticiones tienen run_id
distinto y no sustituyen el slot 103 ni aumentan el denominador v0.4.

## Revisión adversarial y decisión limitada

- Entrega: el control omitido y los recibos T3 falsados respaldan la señal del
  hook en este cliente y versión. No hay captura independiente en el proveedor.
- Vigencia y verdad: hash e identidad de fuente no convierten el texto en
  autoridad. Q04 conserva conflictos simulados; las respuestas requieren
  evaluación por rúbrica antes de contar éxitos.
- Sólo lectura: el rol lector rechazó escrituras y los snapshots lógicos T3
  coincidieron. Eso cubre el intervalo del laboratorio, no todo entorno.
- Ventaja: los fallos de valor literal y Q08 impiden afirmar mejora general.
  C produjo más errores de herramienta y un fallo iniciado. El coste real es
  unknown. No se calculó aún éxito por rúbrica ni pares elegibles; por ello
  no se puede aplicar el umbral comparativo predefinido.

Recomendación: conservar consulta explícita B como candidato experimental,
sin promover C ni integrar hooks globales. La evaluación semántica de los
108 intentos y una revisión ajena al autor siguen pendientes antes de que
el Operador decida utilidad o cambio de fase. Si se quiere medir efecto del
tope 12 comparativamente, abrir otra serie A/B/C congelada bajo el mismo
límite; el correctivo aislado no es un contraste causal.

## Evidencia y conservación

- `experiments/agent-query-pilot/artifacts/series-v0.4.tar.gz`, SHA-256
  `02d8a0ac4ef2d7e6d200dbf0d4b7f30bde07ad1496b8bd10b496d5f31618352b`:
  corpus, freeze, progreso, eventos, solicitudes, entregas, recibos, métricas
  y copia del código congelado. Archivo sintético sin valores de credenciales
  del laboratorio según barrido del empaquetador.
- `experiments/agent-query-pilot/artifacts/series-v0.3.tar.gz`, SHA-256
  `01c69cdf43c8b1ec94f9a93501c98793a9701eafb0872999b7bb7541e2f10a6c`:
  intento histórico abortado; no participa en métricas v0.4.
- `experiments/agent-query-pilot/artifacts/correction-v0.5.tar.gz`, SHA-256
  `e75bc220162db97d8cd3be0c3a4345b92310a4f28fc7db9259792dd0324ce431`:
  ambos intentos, arnés, perfil y manifiesto correctivo. Incluye dependencias
  instaladas automáticamente por el perfil temporal de OpenCode; no implica
  nueva dependencia del proyecto.

En el cierre T5 los tres archivos eran locales y no publicados. La revisión
de publicación posterior del 2026-10-08 comprobó sus SHA-256 y los incorporó
a Git sin alterar sus bytes; el paquete v0.5 conserva dependencias temporales
de OpenCode y por eso es más grande. Esta publicación no reejecuta la serie ni
convierte recibos del harness en evidencia del modelo efectivo o del coste
facturado. La limpieza del Mongo del laboratorio no se infiere del archivo ni
de su publicación; requiere un recibo operativo separado.
