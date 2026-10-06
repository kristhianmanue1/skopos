# H25 — fuentes diversas, primer incremento verificable

Estado: plan de trabajo autorizado; revisión v1 refinada tras autorrevisión.
Fecha: 2026-10-05. Base: `2d7038f961a04b6790b35559e22c455039dbcfe1`.
Encargo: plan detallado, ronda adversarial, refinamiento e inicio de ejecución.
Autor: Codex. La revisión de la misma instancia es autorrevisión, no revisión
independiente. No se heredan cierres ni autorizaciones del ciclo multi-CLI.

## Objetivo y límites de aceptación

H25.1: una transcripción diarizada local entra por una frontera explícita;
conserva identidad, revisiones de fuente, bytes y localizadores; se recupera
su revisión vigente y se navega a las anteriores sin confundirlas con análisis.
H25.1 no equivale al hito 25 completo. La extensibilidad se comprobará después
con un segundo origen de estructura distinta (mensajes de runtime, por ejemplo).
No se afirmará soporte de orígenes sin adaptador y evidencia propios.

Reutilizar los experimentos existentes como evidencia, no promoverlos por nombre.
ADR-016 anticipa v3 en inglés; no define su esquema ni autoriza una migración.
ADR-018 rige identificadores nuevos. ADR-007 sigue gobernando análisis; no se
reutilizará su contador para revisiones de fuente. ADR-009 distingue bytes
verificados de afirmaciones sobre integridad, captura y contenido.

## Autoridad y operaciones

El encargo autoriza documentación, diagnóstico de lectura, fixtures sintéticos,
pruebas locales y un prototipo aislado para evaluar el contrato propuesto.
La decisión estratégica de contrato productivo, migración y aceptación sigue
perteneciendo al Operador. No se activan servicios de producción por este plan.
No incluye ingesta privada, endpoints remotos, instalación de dependencias,
escritura en repositorios ajenos ni admisión automática en AN-KLA o Ágora.
Commit/push según autorización permanente de AGENTS, después de gates; merge
a main, activación o migración de este incremento requieren su alcance aprobado.

CONTEXTO DE AUTORIZACIÓN: ingeniería defensiva en Skopos sobre la base citada;
laboratorio local con fixtures sintéticos y Mongo temporal exclusivo. Permitidos:
lectura diagnóstica y pruebas del contrato con controles positivos. Excluidos:
credenciales, datos privados, evasión, mutación de corpus y cambios de servicios.
Parar la operación afectada si necesita recursos fuera de alcance; continuar
documentación y pruebas independientes. No se presupone aislamiento del host.

## Secuencia y prioridades

T0 → T1 → T2 → T3 → decisión D1 → T4 → decisión D2a → T5 → D2b → T6.
O1 (operación Mongo) es independiente de T2/T3, pero precede a piloto productivo.
O2 (ADR-019) precede a evaluar ranking del corpus, no al contrato de fuentes.
Hito 24/P-005 no es dependencia demostrada de H25.1; reconciliarlo por separado.
Embeddings, read general, calibración y backfill quedan fuera del camino crítico.

Presupuesto inicial experimental: fuente hasta 16 MiB (límite existente del
lector), hasta 10.000 segmentos, IDs ASCII de 1–128 caracteres; rechazo explícito
sin truncar una fuente. Son límites de laboratorio, no capacidad productiva
validada. T4 definirá límites de consulta y exclusiones antes de implementar:
propuesta inicial 20 resultados y 64 KiB por fragmento, sujetos a medición.

Aceptación de T3: controles positivos y negativos para cada invariante; ninguna
prueba sólo negativa acredita un rechazo. La validez sintáctica del predecesor
no demuestra que existe ni que sigue vigente: esa comprobación CAS pertenece a
T4. Un hash del sobre derivado no sustituye al hash de los bytes originales.
El segmento se identifica dentro de proyecto/fuente/revisión, nunca globalmente
por su ordinal. La versión del parser se conserva separada de la de fuente.

## Tareas ejecutables

```text
TAREA T0 — plan, revisión y gate
Consumes: AGENTS.md; docs/adr/adr-015-gate-skevi.md; scripts/check_plans.py.
Produce: plan refinado, acta adversarial y gate de planes activo.
Steps:
- [x] Crear este plan v0 y registrar su digest antes de la revisión.
  Verificación: sha256 identificable del artefacto revisado.
- [x] Refutar alcance, presupuestos, autoridad, identidad y criterios de cierre.
  Verificación: acta con hallazgo, impacto, evidencia, disposición y residual.
- [x] Refinar el plan y declarar plans en skevi-gate.json apuntando a docs/planes/activos.
  Verificación: check_plans valida este plan; plan histórico no movido ni reescrito.

TAREA T1 — línea base y reconocimiento F0
Consumes: docs/hoja-de-ruta.md; experiments/meeting-source-v1/pilot.py; experiments/diarized-source-v1/source.py.
Produce: se crea docs/evidencia/h25-inicio-2026-10-05.md con hechos, brechas y requisitos.
Steps:
- [x] Confirmar Git, memoria recuperada y fronteras de ambos experimentos.
  Verificación: rama/SHA, revisión AN-KLA y matriz propiedad→código→brecha.
- [x] Reconocer formato y semántica de metadatos mediante fixtures sintéticos.
  Verificación: bytes/localizadores exactos; unknown no convertido a false o complete.
- [x] Separar diagnóstico operacional de pruebas del contrato.
  Verificación: observaciones de Mongo fechadas; cero reinicios o cambios de configuración.

TAREA T2 — contrato candidato y decisiones F1
Consumes: docs/contratos/f1-contratos.md; docs/adr/adr-016-idioma-por-audiencia.md; docs/adr/ADR-009-fragmento-completo-recuperacion.md.
Produce: se crea docs/adr/adr-020-fuentes-diversas.md como PROPUESTO con contrato experimental v0.
Steps:
- [x] Definir identidad estable, proyecto, revisión, predecesor, hash de origen y formato/parser.
  Verificación: matriz de identidad ante copia, renombre, corrección y cambio de parser.
- [x] Definir completitud trivalente, tiempos, etiquetas y procedencia de declaraciones.
  Verificación: sin inferencias de identidad humana, fecha por nombre o equivalencia con audio.
- [x] Definir errores, límites, compatibilidad, almacenamiento y criterios de admisión.
  Verificación: D1/D2 concretas; v2 sigue legible; ningún cambio del manifest productivo.

TAREA T3 — prototipo de frontera, sin admisión productiva
Consumes: contrato candidato T2; experiments/diarized-source-v1/source.py.
Produce: se crea experiments/diarized-source-v1/envelope.py y tests/test_source_envelope.py.
Steps:
- [x] Construir sobre una única instantánea un sobre fuente con identidad explícita.
  Verificación: mismo input produce mismo sobre; bytes derivados no se etiquetan como originales.
- [x] Probar casos positivos y negativos antes de persistir nada.
  Verificación: Unicode/CRLF, fuente inválida, revisión, metadatos desconocidos y texto hostil inerte.
- [x] Documentar qué demuestra y qué no demuestra la frontera.
  Verificación: no Mongo, red, LLM, archivos creados por el constructor ni cambios en v2.

TAREA T4 — persistencia y recuperación integrada, después de D1
Consumes: candidato T2 aprobado; prototipo T3; experiments/meeting-source-v1/persistent.py como referencia.
Produce: implementación del contrato productivo aprobado, specs y tests de su frontera.
Steps:
- [ ] Fijar backend y protocolo de revisión/idempotencia en ADR aceptado.
  Verificación: claves y CAS definidos; SQLite del experimento no se adopta por inercia.
- [ ] Integrar lector y almacén sin exigir análisis LLM para capturar o consultar.
  Verificación: importación, repetición, corrección y reapertura conservan identidad y bytes.
- [ ] Comprobar concurrencia y recuperación de interrupciones.
  Verificación: dos escritores del mismo predecesor no ganan ambos; reintento no duplica.
- [ ] Implementar consulta vigente y fetch de revisión explícita con límites.
  Verificación: término eliminado no reaparece; fuente ausente/alterada produce error visible sin texto falso.
- [ ] Probar compatibilidad y rollback sin tocar v2 real.
  Verificación: fixtures v2 dan la misma salida; retorno a versión anterior ensayado en copia.

TAREA T5 — piloto controlado y evaluación
Consumes: T4 verificado y autorización sobre una exportación concreta.
Produce: informe fechado con corpus, hashes, preguntas y resultados; contenido privado fuera de Git.
Steps:
- [ ] Fijar corpus y respuestas esperadas antes de ejecutar las consultas.
  Verificación: muestra sintética primero; muestra real autorizada separada; omisiones contadas.
- [ ] Medir recuperación y navegación con revisión correctiva.
  Verificación: cada resultado servido resuelve su fuente/revisión/localizador; cero versiones reemplazadas en casos estables.
- [ ] Medir coste de ingesta y consulta por separado.
  Verificación: bytes, segmentos, latencia y límites declarados; sin extrapolar una muestra a escala general.
- [ ] Comprobar acceso, retención y salida al consumidor.
  Verificación: denegación no sirve texto; selección incompleta señalada; sin admisión externa automática.

TAREA T6 — aceptación y cierre H25.1, después de D2b
Consumes: evidencia T4/T5, revisión adversarial final y decisión del Operador.
Produce: incremento aceptado o rechazo trazable; siguiente alcance de hito 25.
Steps:
- [ ] Revisar el artefacto final y resolver hallazgos materiales.
  Verificación: ningún blocker abierto; tests y gates pasan sobre código final.
- [ ] Obtener aceptación y realizar sólo publicación/activación autorizadas.
  Verificación: SHA remoto y estado del servicio se comprueban por separado.
- [ ] Diseñar el segundo adaptador de estructura distinta.
  Verificación: no se cierra hito 25 completo hasta fijar y cumplir su aceptación propia.

TAREA O1 — recuperación operacional de Mongo
Consumes: diagnóstico de lectura T1 y configuración de servicio vigente.
Produce: diagnóstico reproducible y propuesta concreta de recuperación.
Steps:
- [x] Consultar listener, launchd y eventos fatales recientes, sin contenido del corpus.
  Verificación: separar mensaje observado, causa inmediata e hipótesis causal pendiente.
- [ ] Preparar preservación y recuperación antes de operar sobre datos.
  Verificación: espacio, respaldo/restauración, concurrencia de watch y rollback definidos; ejecutar cambios sólo con alcance aprobado.
- [ ] Tras recuperación autorizada, comprobar índices y cobertura en lectura.
  Verificación: cifras nuevas fechadas; no asumir que el proceso activo implica corpus íntegro.

TAREA O2 — decidir ADR-019 y evaluar búsqueda
Consumes: docs/adr/adr-019-idioma-del-indice-de-texto.md; evidencia operacional O1.
Produce: decisión documentada y evaluación lexical antes de embeddings.
Steps:
- [ ] Contrastar índices vivos con la propuesta y preservar conteos.
  Verificación: idioma observado, diferencias de configuración y restricciones multilingües explícitas.
- [ ] Preparar ensayo comparativo en copia y decisión de reconstrucción.
  Verificación: consultas predefinidas, tildes, frases, recall/ranking y rollback; ningún drop en producción sin autorización.
```

## Decisiones y condiciones de parada

D1: aceptar contrato productivo, ubicación de almacenamiento, compatibilidad v2
y política de revisión. Recomendación inicial: importación manual de archivos
explícitos; nada de watcher o push remoto en H25.1. La propuesta será concreta
antes de pedir decisión. Un experimento v0 no constituye aprobación de v3.

D2a: autorizar corpus real específico, sus lectores y retención antes de T5.
No se exige entregar datos privados para avanzar T0–T3. Sin D2a, el piloto
sintético produce evidencia técnica pero no aceptación de un sistema real.

D2b: adjudicar los resultados de T5 y autorizar por separado activación y merge
del incremento. No convertir aprobación del corpus en aceptación del producto.

O1 tiene un riesgo observado de capacidad: al inicio el volumen de datos marcó
99 % y 8,2 GiB libres. No iniciar copias grandes, reconstrucciones o backfill
sin estimar espacio necesario y margen de operación. El log FTDC de 2026-10-03
no aporta un errno que permita adjudicar la causa raíz sólo con esa cifra.

Parada material: requisito de dependencia nueva, escritura sobre corpus vigente,
incompatibilidad con consumidores, pérdida de bytes/procedencia, necesidad de
acceso no concedido o riesgo no contemplado. No borrar fuentes, logs o respaldos
para recuperar espacio. Mantener los avances recuperables y continuar tareas
que no dependan de la decisión faltante.

## Registro de ejecución

Estado al 2026-10-05: T0–T3 ejecutadas dentro de su alcance experimental;
T2 es contrato candidato, no aceptación productiva. O1 tiene diagnóstico,
pero recuperación y comprobación del corpus pendientes. O2 sin ejecutar.
T4 espera D1; T5 espera T4 y D2a; T6 espera resultados y D2b.
Evidencia: `docs/evidencia/h25-inicio-2026-10-05.md`; ronda:
`docs/rondas/2026-10-05-h25-plan.md`. Suite 322 pruebas OK sin skips;
gate de planes activo, un plan verificado. No se cierra el hito 25.
La última medida de espacio es 6,0 GiB libres (99 %), posterior a los 8,2
iniciales; dbPath ocupa 1,1 GB según du. No adjudicar esa variación a esta tarea.
No se realizó recuperación productiva ni escritura nueva en AN-KLA.
