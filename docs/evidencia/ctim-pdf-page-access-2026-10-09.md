# Lectura de página PDF CTIM v0.2 — 2026-10-09

## Resultado local observado

Se añadió `read_pdf_page` al acceso local de siete fuentes, bajo el contrato
`docs/contratos/ctim-source-access-v0.2-local.md`. Las tres operaciones previas
mantienen v0.1. El perfil privado y los originales no se modificaron. La
prueba de contrato pasó (6 casos); suite completa: 476 pruebas OK, 6 omitidas.
Gates Skevi: 712 archivos dentro de límites, 2 planes verificados. La suite
emitió advertencias de `MongoClient` sin cerrar en pruebas preexistentes;
ningún caso falló por ello.

En el socket Unix local, modo `0600`, la solicitud `read_pdf_page` para
`imss-procedure-2900-003-001-2021`, página física 15, devolvió `ok`,
`schema: skopos/ctim-source-access/v0.2`, SHA original
`141d9b090efa4d70799ee1368350a5167347b4e8cd5f99912fb192ce6c704faa`,
41 líneas nativas, OCR `not_run`, cobertura 91/91 páginas y
`fidelity_status: unreviewed`. La línea JSON completa midió 9,894 bytes en
el primer ciclo, bajo el límite de 65,536 bytes. La fuente fuera del perfil
dio `source_not_allowed`; página 92 dio `invalid_page`, ambos sin resultado.
`list_sources` siguió respondiendo con esquema v0.1 y siete fuentes.

Se cerró el host, se comprobó la desaparición del socket, se reinició el host
y la página 15 volvió a responder `ok` con 41 líneas (9,899 bytes, por costo
temporal variable). Tras el segundo cierre, el socket volvió a desaparecer.
Una copia temporal del perfil con hash de manifiesto alterado produjo
`coverage_mismatch`, etapa `retrieval` y `result: null` para la nueva operación;
la copia se eliminó. El controlador dedicado de Mongo se detuvo.

La primera tentativa de arranque del controlador devolvió
`control_disconnected` y su log indicó `mongo_identity_mismatch`; el proceso
y los sockets quedaron retirados. Un segundo arranque pasó sin alterar el
control de identidad. Es una incidencia observada del entorno, sin causa
definitiva atribuida.

## Lectura y límites

En el manifiesto de la página 15, `CPIM` aparece en línea 6 con bbox vertical
0.343–0.357 y la actividad 18 empieza en 0.339; `CTIM` aparece en línea 7
con bbox 0.552–0.567 y las actividades 19–22 comienzan en 0.552, 0.605,
0.722 y 0.779. Esto sustenta una revisión de maquetación; el orden lineal
del manifiesto, por sí solo, no atribuye actores. La observación visual del
render fue comunicada por el agente de expertoGobernanza; no se repitió aquí.
La respuesta conserva `bbox` y no produce campo `actor`.

No se ejecutó Spark, no se promovió una fase ni se adjudicó fidelidad,
vigencia o admisión jurídica. El `ok` de Skopos acredita entrega local bajo
el perfil y hashes observados, no una lectura semántica correcta por un agente.
