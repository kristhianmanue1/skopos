# Piloto de consulta desde agente — controles T1–T3

Estado: controles técnicos de v0.3, con enmienda v0.4 al final; no es
aceptación de uso operativo. Observado el 2026-10-07, antes de iniciar las
series congeladas. Autor y autorrevisor: Codex, misma instancia.

## Alcance y procedencia

Skopos `main@fe1e8cbf6fe521c3e45fb87e76acf38c5f476084`, fuente runtime
v3. Cliente OpenCode `1.18.35`; modelo solicitado
`zai-coding-plan/glm-5.3-flash`. El identificador aparece en la configuración
y exportación local de sesión; no hay telemetría independiente del proveedor
que acredite el modelo efectivo. La configuración personal de OpenCode incluye
una salida final propia; el Operador confirmó que es deliberada. Para el
experimento se usó un perfil temporal con sólo las dos herramientas del piloto,
permiso denegado para las demás y directorio de trabajo vacío. No se abrió la
llave declarada en Llavero.

El corpus está en `/private/tmp/skopos-agent-query.179bLU/corpus-r2`:
3 variantes, 20 identidades de fuente por variante, 66 revisiones y 36 tareas.
El MongoDB del piloto usa un puerto loopback temporal, réplica única y base
`skopos_agent_query`, con escritor de preparación y lector de consultas. El
control de rol rechazó una escritura del lector; no se usó la instancia
operativa. La importación registró las 66 revisiones. La comparación fija de
36 búsquedas y tres fetch devolvió paridad exacta entre referencia A y Skopos.
Los archivos `admission.json`, `t1-check.json` y `backend-parity.json` conservan
el detalle; son artefactos locales del laboratorio, no publicaciones.

## Controles observados

| Propiedad | Evidencia local | Resultado y límite |
|---|---|---|
| Recepción en llamada principal | `client-probe-E`, `run-one-A`, `run-one-B`, `run-one-C2`: eventos `step_start/finish`, `deliveries.jsonl` y hook `call-trace.jsonl` | A, B y C enlazaron entregas con las llamadas de su sesión. En C el prompt de OpenCode codifica el bloque como cadena JSON; se conserva hash de representación original y efectiva. Es señal del harness anterior a la petición, no captura de bytes HTTP del proveedor. |
| Control omitido y acuses falsos | `client-probe-F` y `verify_controls.py` | La omisión deliberada falló como `not_incorporated`; hash cambiado, sesión ajena, duplicado y acuse antiguo se rechazaron. El control positivo pasó. |
| Integridad y alcance | `control_checks.py`, `t1-check.json`; regresión `test_runtime_store.py` y `test_runtime_verification.py` | Search/fetch sanos funcionaron en A/B; hash alterado falló. Q08 mostró indisponibilidad. Los tests del producto cubren original alterado/restaurado e histórico. La selección de proyecto no se presenta como ACL. |
| Límites | `control_checks.py`, `fault_controls.py`, `trace_controls.mjs` | Se observaron 0,1,5,20 resultados; 21 fue rechazado por backend. El adaptador negó cuarta búsqueda, operación ajena y campos extra. El hook aceptó 65 535 y 65 536 bytes y rechazó 65 537. Salida excesiva, JSON inválido, aborto y timeout de procesos sintéticos se clasificaron. |
| Concurrencia y continuidad | `control_checks.py`, `verify_controls.py` | Dos invocaciones simultáneas conservaron IDs distintos y contador 2 bajo lock; el siguiente proceso conservó presupuesto. Un acuse de sesión ajena o sin entrega asociada falló. No se ensayó carga multiusuario. |
| Unicode y lectura | `control_checks.py`, `db-before.json`, `db-after.json` | Casefold con tilde devolvió el mismo resultado. Entre dos huellas, tras consultas, tres colecciones y 127 documentos conservaron igual digest lógico. Este intervalo no prueba ausencia universal de escrituras transitorias; el rol de lector limita la capacidad. |
| Regresión de Skopos | `regression.stderr`; MongoDB temporal distinto en puerto 63968 | 475 pruebas, cero fallos y cero omisiones en 85.355 s. El proceso temporal fue identificado y detenido. Los tests existentes cubren límites, CRLF, revisiones y frescura dentro de sus propios fixtures. |
| Gates documentales | `scripts/check_sizes.py`, `scripts/check_plans.py` | 311 archivos dentro de límites y dos planes con estructura válida antes del congelamiento. No sustituyen pruebas funcionales. |

Una corrida C de desarrollo superó el presupuesto inicial de 16 KiB en el
cuarto paso y no produjo acuse válido. Antes de congelar, se corrigió el mapeo
de la cadena codificada y se fijaron 64 KiB acumulados, contando cada reenvío.
La repetición C pasó con tres llamadas, tres entregas y 12 309 bytes. Todas las
corridas de desarrollo quedan excluidas de los 108 slots.

El corpus no es ciego para el autor del arnés. Los controles de título se
acotan fijando `--title` y contrastando número de hooks y pasos principales;
no demuestran comportamiento de otros clientes ni capturan el cuerpo HTTP.
La suite del producto y los controles del piloto tienen métodos distintos.
No hubo revisor independiente ni verificación de coste facturado. Los valores
de `cost: 0` que puede emitir OpenCode no prueban gratuidad del plan.

## Congelamiento y continuación

El congelamiento final se guardó en
`/private/tmp/skopos-agent-query.179bLU/series-v0.3/freeze-final.json`, SHA-256
`cdad00565c5b326aaf8a8acc5c5f78d009a6fe11db24e827cacb1cbbaa26179f`.
Incluye hashes de código, perfil, corpus, oráculo y rúbrica, semilla `20261007`
y 108 slots con seis bloques por permutación A/B/C. El archivo anterior
`freeze.json` fue un borrador de desarrollo y no rige la serie. T4 está en
ejecución secuencial, con sesión nueva por slot. Un cambio de entrada obligará
a detenerla y abrir otra serie, preservando los intentos ya observados.

## Enmienda v0.4 posterior a la parada de v0.3

La serie v0.3 terminó en el slot 28: 27 completados y un fallo iniciado, 80 no
iniciados. En Q10-C, el cuarto hook calculó 67 630 B candidatos frente al
límite de 65 536 B; no se envió esa cuarta llamada. El verificador v0.3 contó
el hook bloqueado como llamada principal y devolvió además
`main_call_trace_count_mismatch`, lo que activó la parada conservadora.
`series-v0.3/runner.stderr`, `progress.jsonl` y el directorio
`028-Q10-v1-C` conservan el intento. No se mezclan esos 28 con v0.4.

La corrección cuenta sólo hooks sin violación como llamadas enviadas y excluye
entregas presentes únicamente en un hook bloqueado. Al reprocesar el slot
fallido, el error quedó limitado a `context_budget_exceeded`. Se fijó 128 KiB
antes de v0.4: el control de frontera aceptó 131 071 y 131 072 B, y rechazó
131 073 B. Una corrida Q10-C de desarrollo cerró con acuse positivo; no es un
resultado de la nueva serie. Persisten los límites de 3 búsquedas, 3 fetch,
8 llamadas y 120 s. No se ajustaron tareas, oráculo ni rúbrica a partir de
respuestas.

El nuevo congelamiento es
`/private/tmp/skopos-agent-query.179bLU/series-v0.4/freeze-final.json`, SHA-256
`72aca9ded127b266ac598bdaca2bd59330cd09224a653587992200f61da7cc0c`.
La serie v0.4 consta de 108 intentos nuevos; su evaluación se reportará aparte.
