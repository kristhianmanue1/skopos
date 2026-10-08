# H25 — plan técnico de verificación y decisión de cierre

Fecha: 2026-10-06. Estado: PROPUESTO; entregable documental, no ejecución.
Ejecutor solicitado: GPT-6 Sol, mediante el agente que seleccione el Operador.
Repositorio: /Users/krisnova/www/aria/skopos.
Base inspeccionada: main, fe1e8cbf6fe521c3e45fb87e76acf38c5f476084;
árbol limpio antes de crear este documento. Remoto no consultado.
Modelo efectivo del futuro ejecutor: unknown hasta contar con evidencia.
No se creó otro chat, no se delegó ni se cambió el modelo de esta sesión.

## 1. Resultado buscado y corrección de contexto

Preparar evidencia suficiente para una decisión explícita sobre H25, con
aceptación separada de captura/conservación, utilidad y continuidad operativa.
El agente puede concluir verificaciones; la adjudicación pertenece al Operador.
El criterio nuclear pendiente es el segundo origen estructuralmente distinto:
el plan H25 original lo exige, mientras O2/ADR-019 evalúa el índice legado.
Sólo una decisión explícita puede añadir O2 o continuidad como puertas de H25.

La hoja de ruta resume pendientes que requieren leer sus enmiendas posteriores:

| Frente | Evidencia documental consultada | Pendiente real |
|---|---|---|
| H25.1 | Plan original y hoja de ruta: aceptado/publicado | Preservar alcance aceptado; no repetir su aceptación |
| H25.2 | Operación local: integrado y activado monousuario | Consolidar aceptación y límites del segundo origen |
| Descarga y restauración | Recuperación nube: PASS con datos descargados y Llavero local | No volver a presentar la descarga como nunca comprobada |
| Pérdida del equipo | Custodia independiente diferida al Operador | Recuperación sin claves locales no demostrada |
| Mantenimiento | Respaldo coordinado y restauración implementados para runtime v3 | Ejecución desatendida por verificar; periodicidad depende de Codex |
| Independencia de proveedor | Requisito explícito en mantenimiento | Elegir y verificar programador sustituible fuera de Codex |
| Relevancia | Ensayo documental con omisiones críticas | Juicios humanos y evaluación de utilidad aún pendientes |

El código actual confirma tres fronteras: `RuntimeSourceStore._search` recorre
cabezas y usa búsqueda verificada por subcadena; `buscar` y
`buscar_por_tema` usan `$text` del legado; `runtime_operations.py` fija raíz,
base y puerto privados para runtime, y `runtime_restore.py` obtiene sus claves
del lanzador/Llavero local. Su arnés no valida recuperación sin ese Llavero ni
cubre automáticamente otras bases v3 de H25.1. Una salida vacía de runtime
requiere revisar `unavailable_sources`, `excluded` y `excluded_source_kinds`.

Estos son hechos documentados, no una nueva inspección de servicios, informes
privados, nube o Keychain. Revalidar artefactos necesarios antes de operar.
La recuperación completa ante pérdida del equipo no se deduce de la restauración
de datos con Llavero local. El resguardo diferido tampoco equivale a riesgo aceptado.

## 2. Orden de lectura y fuentes de autoridad

1. AGENTS.md, docs/guia-rapida.md y README.md, especialmente pruebas aisladas.
2. docs/planes/activos/h25-fuentes-v1.md y docs/hoja-de-ruta.md.
3. docs/adr/adr-020-fuentes-diversas.md y docs/contratos/source-store-v3.md.
4. docs/propuestas/h25-dsh-session-v0-contract.md.
5. docs/evidencia/h252-operacion-local-2026-10-06.md.
6. docs/evidencia/h252-llavero-respaldo-2026-10-06.md.
7. docs/evidencia/h252-recuperacion-nube-2026-10-06.md.
8. docs/evidencia/h252-mantenimiento-2026-10-06.md.
9. docs/adr/adr-019-idioma-del-indice-de-texto.md y
   docs/evidencia/adr019-expansion-2026-10-05.md.
10. Antes de código: F0, specs F1, contratos F1 y ADR aplicables, incluido ADR-018.

Recuperación nube AMENDS el pendiente de descarga del expediente Llavero.
Mantenimiento AMENDS continuidad y transporte largo de claves. Este plan
INFORMS la continuación; no SUPERSEDES decisiones, contratos ni aceptación.
REQUIRES_DECISION: criterios de utilidad H25.2 y adjudicación de cierre;
relación de O2/continuidad con el hito; resguardo independiente y
elección/activación del sustituto del programador como decisiones propias.

## 3. Autoridad de ejecución

La petición actual autoriza crear este plan. No activa sus operaciones.
Al recibir un encargo de ejecución, el agente debe registrar su alcance y
reutilizar autorizaciones vigentes verificables, sin pedirlas repetidamente.
Un relato histórico no acredita por sí solo permiso actual para otro recurso.

Se pueden separar paquetes: diagnóstico documental; laboratorio y evaluación;
cambios de producto; ensayo de recuperación privada; programador operativo;
publicación; adjudicación. No es necesario bloquear paquetes independientes.
Commit/push tienen autorización permanente en AGENTS.md, condicionada a gates;
este entregable no exige publicarlos. Merge protegido, dependencias nuevas,
instalación/activación, escritura AN-KLA y memoria conservan su autoridad propia.

### CONTEXTO DE AUTORIZACIÓN para completar antes de pruebas sensibles

- Sistema: Skopos, SHA revalidado, runtime v3 y componente concreto del ensayo.
- Autoridad y alcance: citar instrucción del Operador; diferenciar laboratorio,
  lectura privada, restauración y operación. Recursos no confirmados: NO VERIFICADO.
- Objetivo: comprobar recuperación íntegra o rechazo visible sin datos falsos;
  comprobar coordinación y fallo cerrado sólo dentro de la frontera autorizada.
- Entorno: macOS local declarado; verificar procesos, puertos, rutas y datos.
  Mismo UID no implica aislamiento. No afirmar ausencia de credenciales reales.
- Acciones permitidas: sólo las aprobadas para el paquete; preparar controles
  sintéticos y restauración en copia cuando estén incluidos.
- Excluidas: legado, terceros, extracción/exposición de secretos, evasión,
  borrado de fuentes, poda y cambios de índices sin autorización correspondiente.
- Parada: recurso inesperado, puerto ocupado, falta de espacio, permisos nuevos,
  secreto en salida o divergencia de hashes. Continuar trabajo independiente.
- Resultado: informe reproducible, límites y correcciones sólo autorizadas.

## 4. Secuencia y dependencias

P0 → D0 → P2 → D1 → P3 → P6 → D3.
P1 (O2/ADR-019), P4 (recuperación) y P5 (continuidad) pueden prepararse
después de P0 y avanzar independientemente de la utilidad H25.2. Sólo entran
en el gate de H25 cuando D0 lo determine con alcance explícito.
No implica usar subagentes. D0/D1 son decisiones concretas, no aprobaciones vacías.

- D0: acordar matriz de cierre desde el criterio original de segundo origen,
  el contrato v3 y el perfil autorizado. Determinar qué pertenece a H25 y qué
  queda como O2/ADR-019 o continuidad operativa separada. No convertir un frente
  vecino en obligación de H25 ni excluir un requisito vigente para declarar éxito.
- D1: adjudicar tareas/objetivos de H25.2 y umbrales antes de medir; confirmar
  corpus permitido. El protocolo de doce consultas O2 tiene decisión separada.
- D2: seleccionar custodia/programador y su activación si esos paquetes se ejecutan.
- D3: aceptar, rechazar o aceptar un alcance explícitamente limitado. Una dispensa
  documentada no transforma una propiedad no probada en una propiedad demostrada.

## 5. Tareas ejecutables

```text
TAREA P0 — reconstruir línea base sin activar servicios
Consumes: AGENTS.md; fuentes del apartado 2; estado Git disponible.
Produce: expediente fechado con baseline y matriz de afirmaciones/decisiones.
Steps:
- [ ] Consultar rama, SHA, diff y cambios ajenos; identificar código y artefactos privados necesarios sin leer secretos.
  Verificación: observación fechada, autoría desconocida preservada y remoto separado de referencias locales.
- [ ] Contrastar hoja de ruta con enmiendas y existencia de informes citados.
  Verificación: cada propiedad tiene fuente, vigencia, limitación y estado demostrado/documentado/no verificado.
- [ ] Acordar D0 con alcance finito: formatos realmente implementados y perfiles probados.
  Verificación: segundo origen DSH frente al primero TXT/WhisperX, superficies y obligaciones separadas; no se promete cualquier runtime/sandbox.
- [ ] Trazar el camino de datos en source_cli, SourceStore, RuntimeSourceStore y scripts de mantenimiento.
  Verificación: matriz por base/colección/origen/custodia; confirmar que backup/restore actuales sólo cubren el runtime dedicado y usan claves locales.
- [ ] Identificar autorizaciones reutilizables y decisiones realmente pendientes.
  Verificación: no se inicia backup, Mongo, ingesta, Keychain ni reconstrucción por seguir el plan.

TAREA P1 — preservar y diagnosticar evaluación anterior
Consumes: evidencia ADR019; artefactos de evaluación documental y sonda de vecinos.
Produce: inventario reproducible de corpus, consultas, partición, variantes y fallos.
Steps:
- [ ] Localizar manifest/results/conclusion y context-results citados en evidencia; comprobar hashes/versiones.
  Verificación: archivo temporal ausente se declara ausente; reconstrucción nueva recibe otro identificador y no reemplaza evidencia.
- [ ] Clasificar las ocho consultas de desarrollo: candidato ausente, fragmentación, ranking, presupuesto, revisión o integridad.
  Verificación: cada clasificación apunta a consulta, objetivo y salida; causa incierta queda como hipótesis.
- [ ] Registrar exposición previa de las cuatro consultas reservadas.
  Verificación: no se afina contra ellas; si influyeron en el diseño, preparar nueva reserva antes de medir.
- [ ] Separar superficies runtime/source y search/query legado.
  Verificación: búsqueda literal sin ranking no se evalúa como si implementara semántica ni ADR-019; D0 decide si O2 afecta cierre H25.

TAREA P2 — construir protocolo de utilidad adjudicable
Consumes: D0; contrato source-store-v3; corpus autorizado y objetivos propuestos por el Operador.
Produce: protocolo H25.2 congelado; protocolo O2 separado si está en alcance.
Steps:
- [ ] Fijar corpus DSH autorizado, revisión/cabeza, proyecciones y hashes sin incluir texto privado en Git.
  Verificación: original presente y sellos legibles; ausencia/corrupción se contabiliza, no se inventa recuperación.
- [ ] Definir tareas reales de H25.2: localizar, abrir y verificar text_projection, original_jsonl y derived_event.
  Verificación: cada tarea identifica fuente/revisión/vista, selector y respuesta esperada; las doce consultas legado no certifican runtime.
- [ ] Definir criterios de ausencia y fallos: resultados, fuentes indisponibles y exclusiones.
  Verificación: respuesta vacía sólo cuenta como ausencia esperada si el corpus y los contadores permiten concluirlo.
- [ ] Si D0 incluye O2, preparar aparte doce consultas reales: cuatro españolas, cuatro técnicas/inglesas y cuatro de frase/negación/ausencia/paráfrasis.
  Verificación: ocho desarrollo y cuatro reserva, objetivos por referencia y expectativas humanas fijadas antes del resultado.
- [ ] Obtener D1 y congelar protocolo con digest y timestamp antes de ejecutar.
  Verificación: éxito absoluto por tarea H25.2 crítica y umbral agregado explícitos; O2 recibe digest/juicio propio si aplica.

TAREA P3 — medir y, si procede, corregir de forma acotada
Consumes: P2 adjudicado; copias aisladas; código de búsqueda y contratos aplicables.
Produce: resultados H25.2; resultados O2 y eventual parche sólo si D0 lo incluye.
Steps:
- [ ] Ejecutar tareas H25.2 sobre base autorizada o copia equivalente, sin cambiar revisión ni original.
  Verificación: usar lanzador privado o URI/base dedicadas comprobadas, nunca el default localhost:27017 de `source_cli`; identidad, hash, receipt, replay, tres vistas, resultados, indisponibles y exclusiones registrados por tarea.
- [ ] Diagnosticar cada fallo H25.2 por lectura, selector, integridad, presupuesto, cobertura o expectativa humana.
  Verificación: control positivo pertinente; no rebautizar búsqueda de subcadena como relevancia semántica.
- [ ] Si O2 entra en D0, comparar english, none, spanish y spanish con expansión sobre copias del legado.
  Verificación: índices explícitos por copia, mismo corpus/filtros/límites, versiones vigentes y ningún índice operativo alterado.
- [ ] Si O2 entra en D0, medir top20, posiciones, falsos positivos, redacción/presupuesto y negación/frases.
  Verificación: denominadores, ausencias y exclusiones explícitos; no llamar recall global a juicios incompletos.
- [ ] Si O2 entra en D0, evaluar vecinos sólo en desarrollo cuando el diagnóstico sustente fragmentación.
  Verificación: misma fuente/revisión, redacción y presupuesto; la reserva no se usa para ajustar.
- [ ] Implementar únicamente corrección autorizada y compatible, si el resultado la requiere.
  Verificación: fallo reproducible antes y comportamiento esperado después; invariantes de fuente/revisión sin regresión.
- [ ] Congelar cada candidato y evaluar su reserva propia una vez, cuando aplique.
  Verificación: si se vuelve a ajustar, renovar la reserva; no adjudicar H25 con una reserva de O2.
- [ ] Emitir resultado pass/fail/inconclusive por superficie y criterio.
  Verificación: cumplimiento absoluto acordado y comparación con base; diferencias no críticas adjudicadas, no promediadas para ocultarlas.

TAREA P4 — delimitar y comprobar recuperación externa
Consumes: expediente nube; mantenimiento; decisión del Operador sobre custodia independiente.
Produce: matriz de fallos cubiertos y evidencia de recuperación o pendiente explícito.
Steps:
- [ ] Reconocer restauración descargada ya documentada y distinguirla de la copia más reciente.
  Verificación: no generalizar un hash restaurado a todos los respaldos posteriores ni leer carpeta sincronizada como prueba de descarga.
- [ ] Delimitar qué fuentes cubren los scripts actuales antes de usar el término recuperación H25.
  Verificación: scripts fijados a runtime-v3 y `validate_restored` espera sobres runtime con `texts`; H25.1 y legado requieren prueba/contrato propios si D0 los incluye.
- [ ] Preparar mecanismo concreto de resguardo independiente sin pedir secretos en el chat.
  Verificación: el Operador decide su custodia; no exportar claves ni modificar Llavero por iniciativa del agente.
- [ ] Cuando esté autorizado, diseñar/ensayar arnés de recuperación independiente en entorno nuevo.
  Verificación: `runtime_restore.py` no sirve tal cual porque lee credenciales del Llavero local; documentar entrada segura de claves y no depender de originales operativos ni de ese Llavero.
- [ ] Validar colecciones, cabezas/revisiones, hashes, recibos, vistas, búsquedas, replay y rollback transaccional en copia.
  Verificación: comparar inventario esperado/observado completo; replay no añade revisión; sólo rutas y miembro de la copia se relocalizan.
- [ ] Ensayar corrupción/ausencia en copias sintéticas junto a controles válidos.
  Verificación: rechazo observable antes de servir evidencia falsa; no desactivar controles ni corromper respaldos reales.
- [ ] Registrar tiempos completos y limpieza del proceso propio.
  Verificación: descarga/preparación/restauración/verificación separados; no prometer RTO por tiempo interno del arnés; no borrar evidencia.

TAREA P5 — continuidad independiente de Codex
Consumes: mantenimiento; scripts/runtime_operations.py; decisión D2 sobre mecanismo.
Produce: diseño concreto de programador, eventual implementación y evidencia desatendida.
Steps:
- [ ] Proponer adaptador mínimo al programador del sistema, por ejemplo LaunchAgent en el perfil macOS actual.
  Verificación: elección justificada; hoy no hay programador en scripts, sólo backup/restore invocables; configuración, estado, logs y alertas fuera del chat.
- [ ] Mantener semántica diaria/post-ingesta/semanal/mensual y recuperación de horarios perdidos.
  Verificación: estados de éxito separados por operación; descarga mensual manual visible; sin poda ni política nueva por defecto.
- [ ] Probar entorno sin sesión interactiva, Keychain bloqueado, contención, fallo de copia y reinicio en laboratorio.
  Verificación: controles positivos, fallos comunicados y estado no avanzado falsamente; finalmente no se presenta como protección contra corte eléctrico.
- [ ] Preparar transición y reversión sin dos programadores simultáneos.
  Verificación: instalar/activar y pausar automatización existente sólo con autoridad; preservar su configuración y evitar carreras de mantenimiento.
- [ ] Observar corrida iniciada por horario con Codex y APIs OpenAI fuera del camino de ejecución.
  Verificación: timestamp, origen del disparo, recibo, servicio final y alerta; disparo manual no satisface este criterio.
- [ ] Validar diaria, semanal y mensual por separado, con reloj inyectado en laboratorio y evidencia real cuando corresponda.
  Verificación: simulación acredita lógica, no ejecución horaria real; no se exige esperar un mes para probar la lógica ni se inventa corrida mensual.

TAREA P6 — consolidación y decisión final
Consumes: resultados P0/P2/P3; P1/P4/P5 según alcance D0 y decisiones propias; diff final y gates.
Produce: expediente autocontenido y propuesta de adjudicación D3.
Steps:
- [ ] Hacer autorrevisión adversarial del artefacto final y resolver hallazgos materiales.
  Verificación: productor y revisor identificados; no afirmar revisión independiente sin separación comprobada.
- [ ] Ejecutar suite aislada completa y gates sobre el código final si se modificó código o se pretende publicar.
  Verificación: cero fallos/omisiones, logs y SHA asociados; servicios operativos y legado intactos. Para diagnóstico documental, verificar sus artefactos sin fingir regresión funcional.
- [ ] Reconciliar documentación vigente con evidencia sin borrar antecedentes.
  Verificación: estados de implementación, activación, recuperación, relevancia y aceptación separados; ADR-019 no activado por resultado favorable.
- [ ] Presentar matriz final para D3 y registrar únicamente la decisión recibida.
  Verificación: no marcar H25 cerrado si falta criterio obligatorio; aceptación limitada conserva pendientes y cambia alcance sólo por decisión explícita.
```

## 6. Protocolo de evidencia y comandos de arranque

Crear un directorio de ejecución nuevo con identificador no secreto. Artefactos
propuestos: baseline.json, scope-matrix.md, protocol.json, judgments.json,
results.jsonl, recovery-report.json, scheduler-report.json y decision.md.
Son formatos de trabajo propuestos, no contratos instalados. Cada informe lleva
SHA de código, hash de entradas, entorno, observed_at, comando reproducible,
salida/exit code, límites y ubicación del log redactado. Separar configuración
del modelo solicitado y evidencia del modelo efectivo; unknown si no existe.

Contenido privado, rutas sensibles detalladas y credenciales permanecen fuera
de Git; el expediente público conserva sólo metadatos suficientes y referencias.
No regenerar evidencias perdidas como si fueran ejecuciones históricas.

Arranque de lectura, desde la raíz:

```bash
git status --short --branch
git rev-parse HEAD
git diff --stat
.venv/bin/python -m skopos source --help
python3 scripts/check_sizes.py
python3 scripts/check_plans.py
python3 scripts/check_plans.py docs/propuestas/h25-cierre-plan-gpt6-sol.md
```

La suite completa requiere Mongo temporal exclusivo, primario replica set ya
iniciado, y Ollama local según README. Crear el laboratorio sólo bajo alcance
de pruebas autorizado; comprobar dbPath/PID/base, no sólo número de puerto.
Invocar scripts/run_isolated_tests.py con --mongo-uri apuntando a esa instancia.
No copiar a ciegas un puerto histórico ni ejecutar unittest contra producción.
Si falta servicio/dependencia, reportar gate pendiente; no instalar ni ocultar skips.
`git diff --stat` omite archivos sin seguimiento: leer el archivo propuesto
completo y consultar `git status --short` antes de atribuir alcance al diff.

## 7. Matriz de aceptación propuesta

| Propiedad | Condición de fallo | Evidencia para decisión |
|---|---|---|
| Captura/conservación H25.2 | Bytes o identidad distintos, replay duplica, vista sin procedencia | Recibos, hashes y vistas del segundo origen real autorizado |
| Utilidad literal | Tarea crítica no encuentra/abre evidencia disponible | Tareas adjudicadas y salida de source/runtime |
| Relevancia legado/O2 | Objetivo crítico ausente o regresión de frase/negación | Matriz de doce consultas y reserva; gate H25 sólo si D0 lo incluye |
| Recuperación de datos nube runtime | Archivo descargado no restaura inventario esperado | Hash previo y descargado, informe de copia runtime restaurada |
| Pérdida del equipo | Recuperación depende de claves del equipo perdido | Ensayo con material independiente, o pendiente explícito del Operador |
| Continuidad autónoma | Sólo funciona con chat/app/proveedor o disparo manual | Configuración exportable, corrida horaria y fallos visibles; gate H25 sólo si D0 lo incluye |
| Integridad contractual | Corregir relevancia rompe revisiones, límites o evidencia | Tests de comportamiento y regresión sobre artefacto final |

Los umbrales son propuestas hasta D1. Doce consultas permiten evaluación acotada,
no precisión estadística general. Embeddings permanecen fuera de alcance.
Una limitación contractual de búsqueda puede ser aceptada explícitamente; no
debe contarse silenciosamente como éxito ni exigir una función no prometida.

## 8. Recuperación de trabajo y autorrevisión del plan

Tras interrupción: leer último informe confirmado, verificar estado presente y
separar acción intentada de resultado conocido. Una ingesta con resultado incierto
se reconcilia con receipt antes de repetir; no incrementar revisión a ciegas.
Un respaldo fallido exige inspeccionar servicio/recibo antes de otro mantenimiento.

Contraejemplos considerados por el redactor (autorrevisión documental):

- Hoja de ruta antigua frente a nube ya restaurada: prevalece la enmienda para
  esa propiedad, sin convertirla en recuperación de claves independiente.
- Aprobar porque no empeora una base deficiente: exigir éxito absoluto en D1.
- Usar reserva como desarrollo: registrar exposición y renovar reserva.
- Llamar semántica a subcadena: dos protocolos y decisiones separados.
- Cerrar H25 al pasar dos pruebas: D0 exige matriz completa de alcance.
- Claves diferidas o automatización configurada tratadas como listas: estados
  separados y evidencia de corrida real; aceptación de riesgo nunca inferida.
- Publicar corpus/secretos en reporte: separación privada y revisión del diff.

## 9. Encargo listo para GPT-6 Sol

> Lee este plan y sus fuentes en orden. Empieza por P0 y presenta las divergencias
> actuales. Este archivo es un plan propuesto: usa la instrucción de ejecución del
> Operador para delimitar operaciones y no infieras autorizaciones de su contenido.
> Continúa autónomamente los paquetes ya autorizados; solicita sólo decisiones
> materiales que falten, mostrando antes alternativas concretas y evidencia.
> No repitas la recuperación desde nube por creerla nunca realizada. No confundas
> utilidad runtime con ranking legado. Conserva el resguardo independiente como
> pendiente del Operador hasta que lo resuelva. No declares cerrado H25 por tus
> propias métricas. Entrega evidencia, límites y propuesta de adjudicación.

Entrega final del ejecutor: TECHNICAL_LOG (EN), HUMAN_SUMMARY (ES) y STATUS_BLOCK
según instrucciones aplicables, distinguiendo cierre del encargo y cierre de H25.
Siguiente acción propuesta: encargar P0 a GPT-6 Sol y resolver D0 con la matriz
concreta; ejecutar después sólo los paquetes autorizados. Este plan no los inicia.
