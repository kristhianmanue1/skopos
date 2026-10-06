# Revisión de publicación de fuentes — 2026-10-05

## Alcance y autoridad

El Operador autorizó analizar el trabajo local, commit, push y merge, dejar
el árbol limpio, actualizar AN-KLA y evaluar prioridades hacia el hito 25.
Base local: `5773dbd8b6440f8ddb44d334f56f7fb98fa91ad0`, rama
`codex/meeting-source-currency`; base remota consultada: `main` en `9aa9eb7`.
Se revisaron código, tests y documentación de los tres commits pendientes
de integración y los archivos locales de transcripciones diarizadas.

La revisión fue una autorrevisión adversarial de Codex, sin revisor independiente.
No incluye despliegue, ingesta privada, reconstrucción de índices ni adopción
de ADR-019 (continúa propuesto).

## Cambios y hallazgos

- Se conserva la corrección de vigencia de búsqueda y el piloto de reuniones
  persistente/exportable de `5773dbd`, con los límites de concurrencia ya
  documentados en `docs/vigencia-y-fuentes-diversas.md`.
- Se incorpora el lector local de transcripciones diarizadas y sus pruebas.
  La duración de solapamiento adyacente se corrige a la intersección real:
  `[0,10]` y `[1,2]` producen 1 segundo, no 9. Regresión incluida.
- Se comprueban permisos 0700/0600 del informe, conservación de la fuente,
  ausencia de transcripción completa y rechazo de sobrescritura mediante CLI.
- El experimento ya ignoraba su `runs/`; también se ignora `/runs/` en la raíz.
  No se incluyen fuentes privadas ni informes locales en la publicación.
- El manifiesto reconoce la reparación histórica de P-007 y conserva el
  límite: esas mediciones no certifican el corpus actual.

## Verificación

El Python del sistema no tenía el paquete ni pymongo disponibles. La ejecución
con `.venv/bin/python` dentro del sandbox encontró restricciones de conexión;
fuera del sandbox, Mongo en localhost:27017 devolvió connection refused.
No se arrancó el servicio de producción ni se modificó su directorio de datos.

Se inició el binario instalado `/opt/homebrew/bin/mongod` en 127.0.0.1:37027,
con directorio temporal `/private/tmp/skopos-verification.nS2dwL/db`.
El ejecutor `/private/tmp/skopos-verification.nS2dwL/run_tests.py` redirige los
clientes de localhost:27017 a esa instancia y rechaza bases ajenas a `admin`
o `skopos_test*`. Elimina las variables SKOPOS_LLM del proceso de pruebas para
no seleccionar un proveedor remoto. No se instalaron dependencias.

Comando: `.venv/bin/python /private/tmp/skopos-verification.nS2dwL/run_tests.py`.
Resultado: **311 pruebas, 37.659 s, OK, sin skips**. Incluye el control positivo
de vigencia y las regresiones contra Mongo real temporal. La integración
Ollama fue ejecutada según su prueba existente; no acredita calidad general
del modelo. El ejecutor y los datos temporales son evidencia local, no producto.

`python3 scripts/check_sizes.py`: OK, 150 archivos antes de este documento.
`python3 scripts/check_plans.py`: OK, sin planes declarados; no valida un plan
del hito 25. `git diff --check`: OK. Los cambios posteriores a la suite son
documentales; no cambian el código probado.

## Límites del resultado

El lector verifica bytes de texto y localizadores. No verifica audio, identidad
de hablantes ni completitud de captura. No está conectado al almacén persistente
del piloto ni al pipeline de producción. SQLite sigue siendo experimental.
No se comprobó cobertura, índices ni integridad del corpus vivo de Mongo.
La publicación de estos artefactos no cierra el hito 25.
