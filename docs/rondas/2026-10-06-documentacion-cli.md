# Publicación, limpieza y revisión documental CLI

Autoridad: Operador, publicar, limpiar ramas integradas, analizar críticamente
la documentación y realizar ronda adversarial para afinar y proceder.
Alcance: README, guía rápida, nueva referencia CLI, estado de source-store-v3 y
enlaces con hoja de ruta/evidencia. No auditoría exhaustiva de todo el archivo
histórico. Productor y revisor: misma instancia; **autorrevisión adversarial**,
no revisión independiente. No se cambió código de producto, índices operativos
ni servicios operativos; la suite usó un servicio Mongo temporal.

## Publicación y limpieza

Aclaración de independencia OpenAI publicada en main: `da9407d`.
Se verificó main local/remoto antes de limpiar. Las siete ramas locales y siete
remotas siguientes eran ancestros de ese main; no se integró código nuevo ni
se eliminó trabajo pendiente. Los dos casos con punta local adelantada respecto
de su rama remota también estaban íntegramente en main.

| Rama eliminada | Punta local | Punta remota |
|---|---|---|
| codex/adr019-accent-expansion | b6981b2 | c49bf5c |
| codex/h25-source-contract-plan | 7a30a9d | 7a30a9d |
| codex/meeting-source-currency | 8614581 | 8614581 |
| codex/whisperx-json-source | 4106667 | 08c8309 |
| docs/adr-019-idioma-indice-texto-20260913 | 93b4b79 | 93b4b79 |
| docs/sync-language-and-state-20260912 | a455288 | a455288 |
| feat/query-no-evidence-20260913 | 37dfd58 | 37dfd58 |

Eliminación remota atómica, condicionada a SHA con force-with-lease individual;
eliminación local con `git branch -d`. No se borraron tags ni worktrees.
Inventario SHA completo antes/después y bundle verificado:
`runs/branch-cleanup-j29365q0/`. Sólo main quedó en ambos lados al comprobarlo.
El bundle gitignorado conserva referencias y objetos; también son recuperables
desde el historial de main y el inventario. No es respaldo independiente remoto.
No se limpió el repositorio Llavero ni se publicó trabajo ajeno.

## Análisis crítico y correcciones

| Hallazgo | Impacto | Corrección aplicada |
|---|---|---|
| README presentaba H25.1 en evaluación y D2a/D2b pendientes | Contradicción con aceptación/publicación registradas | Estado actualizado, sin convertirlo en cierre global H25 |
| Runtime, formatos y selectores poco visibles | Consumidor incorrecto o lectura vacía interpretada como ausencia | Referencia CLI con `--format`, `--kind` y vistas/selector |
| Guía arrancaba Mongo y lanzaba suite general | Riesgo de confundir desarrollo con instancia operativa | Arranque inicial sólo ayuda/gates; pruebas en replica set temporal explícito |
| README confundía archivo de entorno no cargado con modo local | Variables heredadas pueden seleccionar otro destino | Variables reales, protocolo frente a proveedor y autoridad remota separados |
| Tarifas/endpoints/rendimiento históricos parecían vigentes | Decisión basada en datos no revalidados | Remisión a expediente histórico; sin promesas comerciales actuales |
| Contrato conservaba ensayo desde nube como pendiente vigente | Invisibilidad del ensayo ya ejecutado | Distinción descarga con claves locales frente a pérdida del equipo |
| Faltaban efectos y errores por comando | Confundir lectura, escritura y resultado incierto | Tabla de efectos; receipt/not_found, exit 1/2 y respaldo post-ingesta exit 3 |
| Gate E1-E5 descrito como inactivo | Instrucción de verificación desactualizada | Plan H25 activo indicado |

Recomendación aplicada: una referencia operativa breve (`docs/cli.md`) enlazada
desde README y guía; contratos conservan semántica y expedientes conservan
historia. No retirar alias ni unificar flags mediante cambios incompatibles.

## Autorrevisión adversarial y refinamiento

1. Contraejemplo: un lector usa `source search` esperando ranking `$text` o
   aplica `--kind` al comando legado. Refinamiento: dos fronteras separadas;
   subcadena runtime no se describe como búsqueda semántica.
2. Contraejemplo: receipt duplicate con original borrado parece recuperación
   probada. Refinamiento: receipt no relee original; consulta/extracción sí tiene
   controles distintos. No se vuelve a borrar/mover corpus para esta revisión.
3. Contraejemplo: import aceptado y backup fallido se reintenta con revisión
   nueva. Refinamiento: código 3 del lanzador y reconciliación antes de repetir.
4. Contraejemplo: seguir la guía activa proveedor remoto o expone una URI con
   contraseña en argv. Refinamiento: entorno heredado advertido; ejemplos sin
   secretos y lanzador autenticado del perfil local explícitamente separado.
5. Contraejemplo: scripts locales equivalen a operación independiente OpenAI.
   Refinamiento: dependencia provisional real del programador y sustitución
   pendiente preservadas; no se instaló alternativa sin decisión.
6. Contraejemplo: comandos multi-CLI hacen que `index` sin argumentos busque
   todos los orígenes. Refinamiento: default de index Codex frente a watch con
   fuentes registradas, rutas explícitas y límites de archivo documentados.
7. Contraejemplo: exit 0 o ayuda correcta prueba funcionamiento end-to-end.
   Refinamiento: not_found puede ser respuesta exitosa; ayudas se reportan como
   verificación de interfaz, separadas de la suite con servicios temporales.
8. Segunda lectura: la introducción podía sugerir análisis LLM de fuentes v3
   y el bloque de sintaxis parecía copiable con corchetes. Se separaron los dos
   flujos y se marcó la notación como esquema, no comandos ejecutables literales.

Veredicto: **proceed para publicación documental**, con los límites siguientes.
No adjudica relevancia, multiusuario, SLA ni independencia operativa efectiva.

## Verificaciones realmente ejecutadas

- Suite completa: 475 tests OK sin omisiones, 128.234 s; Mongo temporal exclusivo
  37032 detenido al terminar. Log:
  `/private/tmp/skopos-maintenance.EEy0En/regression-doc-publication/suite.log`.
  No hubo cambios de código después; esta evidencia sigue aplicando al producto.
- 16 rutas de ayuda, incluidos tres alias y cinco subcomandos source: exit 0,
  sin conexión Mongo. Sonda de bloqueo con control positivo, no sólo ausencia
  de llamadas. Vista/selector inválidos rechazados con exit 2 antes de Mongo.
- 16 enlaces Markdown locales a archivos existentes en las páginas contrastadas;
  no se verificaron URLs remotas ni anchors Markdown. No afirmar cobertura de
  todos los enlaces del repositorio.
- Gates de tamaños/planes y diff sin whitespace erróneo. README bajo 300 líneas.
- Arnés y resultado de interfaz:
  `/private/tmp/skopos-maintenance.EEy0En/check_cli_docs.py` y `cli-docs-check.json`.

## Pendientes recomendados, no implementados

Prioridad operativa: verificar la primera ejecución programada y definir el
sustituto independiente del proveedor. No ocultar dependencia tras una guía.
Prioridad documental posterior: automatizar el contraste de opciones/ejemplos
con parsers para evitar deriva; hoy la comprobación quedó como arnés del encargo.
La ayuda de `query --no-evidence` conserva una cifra aproximada de ahorro y la
ayuda de reanalyze menciona Ollama aunque existe proveedor configurable; revisar
esas cadenas en un cambio de código con pruebas y contratos pertinentes.
No se afirma compatibilidad funcional universal con todos los proveedores por
compartir protocolo. No se revalidaron catálogos, planes comerciales o versiones
externas. No se reescribieron actas históricas ni se actualizó AN-KLA en esta ronda.
