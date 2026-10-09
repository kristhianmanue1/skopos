# Endurecimiento del arnés de consulta agéntica — 2026-10-08

**Ámbito:** `experiments/agent-query-pilot/` y pruebas nuevas. Este cambio
prepara **series futuras**. No reabre los 108 slots v0.4, no altera la
corrección v0.5, no activa memoria automática ni modifica el motor de
recuperación de Skopos. La revisión fue de la misma instancia que produjo
el parche; no es independiente.

## Afirmaciones, controles y límites

1. **Congelación.** El freeze nuevo usa esquema
   `skopos/agent-query-freeze/v1`. `_check_frozen` comprueba antes de empezar
   y antes de cada slot: código del arnés, cuatro archivos de producto,
   plan, corpus, archivos fuente y perfil local de OpenCode. Rechaza
   inventarios incompletos y usa errores explícitos. Control negativo:
   un hash de producto o plan alterado debe detener el slot; se comprueba
   también bajo `python -O`. Esto no garantiza inmovilidad de archivos
   durante la ejecución ni identidad efectiva del modelo o proveedor.
   Un freeze v0 histórico sigue siendo legible, pero el código nuevo no
   cambia ni revalida sus resultados.

2. **Hash de mensajes.** `verify_delivery.py` informa cada llamada como
   `verified`, `not_recomputable` o `mismatch` en
   `messages_sha256_checks`. Los archivos v0.4 no contienen los bytes
   `JSON.stringify(output.messages)` y permanecen `not_recomputable`;
   `delivery_observation=hook_message_presence_only` precisa el límite
   de la correlación existente. No se atribuye a v0.4 una comprobación
   retroactiva del hash.

3. **Captura opcional y limitada.** Un freeze v1 declara
   `message_capture=none` por defecto. Sólo
   `freeze.py ... --capture-synthetic-messages` fija
   `synthetic_bounded_v1`. Para ese perfil, el hook escribe exactamente
   los bytes UTF-8 serializados en `messages/call-NNN.json`, directorio
   0700, archivos 0600 y máximo 512 KiB por llamada. Exceder el límite
   falla el intento. El verificador recalcula SHA-256, comprueba cantidad
   de mensajes y busca cada payload correlacionado en la instantánea.
   Ausencia, alteración o referencia distinta fallan cuando el perfil
   exige captura. Es sólo para el corpus sintético bajo política local;
   no usar el flag con datos privados sin política de retención, acceso
   y retiro adecuada. `archive_series.py` rechaza por defecto una serie
   con instantáneas; incluirlas exige
   `--include-synthetic-message-snapshots`, freeze v1 con captura declarada,
   archivos regulares 0600 y tamaño acotado. Ese flag no sustituye la
   revisión de contenido antes de compartir el archivo. La instantánea
   acredita el estado del hook, no recepción del proveedor, facturación
   ni uso semántico.

4. **Alcance de búsqueda.** Para búsquedas producidas, el adaptador
   agrega `search_scope` con `selection`, `result_limit`,
   `fragment_too_large`, `unavailable_sources` y la marca
   `literal_observed_heads_only_no_global_absence`. La herramienta y
   el prompt indican leer estas señales antes de afirmar ausencia o
   exhaustividad. La misma presentación se usa en A/B/C. Una respuesta
   de un futuro agente podría ignorar el aviso: el código no demuestra
   comprensión. El ejemplo histórico `029-Q10-v1-B` recibió
   `result_limit=1` y aun así dijo «las 5 únicas fuentes»; no se cambia
   ese juicio histórico.

## Verificación y siguiente uso

Los siete controles nuevos prueban una entrada válida y mutaciones de
hashes, incluido `python -O`; instantánea real del hook en dos llamadas;
hash alterado, ausencia en perfil obligatorio y estado histórico no
recomputable; aviso de alcance Q10; y archivo que rechaza instantáneas
sin flag explícito. La suite general ejecutó **454 pruebas, OK, seis
omitidas**. `check_sizes.py` pasó con 472 archivos, `check_plans.py` con
dos planes y `node --check` con ambos plugins. La verificación nueva se
aplicó también a los **108** expedientes archivados v0.4: preservó los
**107 `pass` y un `fail`** originales sin discrepancias; los **351**
hashes de llamada quedaron `not_recomputable`. Ningún test local
demuestra una mejora en respuestas de un agente real.

Para una serie nueva, crear un freeze nuevo, elegir expresamente si el
corpus sintético permite instantáneas, fijar oráculo y rúbrica antes de
observar respuestas y ejecutar por separado controles de Q10
(exclusión) y Q02 (relación entre clave y valor). Evaluar cita de clave,
revisión y fuente, abstención, latencia y coste frente a la búsqueda
literal. No reutilizar v0.4 como confirmación ni activar prefetch global
por este parche.
