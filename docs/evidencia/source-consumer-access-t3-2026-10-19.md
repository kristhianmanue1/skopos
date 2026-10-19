# Ensayo T3 — acceso por consumidor con dos proyectos rehidratados — 2026-10-19

Tarea T3 del
[plan multiproyecto](../planes/activos/contrato-multiproyecto-2026-10-13.md):
corpus real del piloto rehidratado en instancia de laboratorio dedicada,
consumidor con política de un solo proyecto, ensayo espejo con recibo.

## Insumos y verificación

- Tarball `experiments/agent-query-pilot/artifacts/series-v0.4.tar.gz`,
  SHA-256 `02d8a0ac4ef2d7e6d200dbf0d4b7f30bde07ad1496b8bd10b496d5f31618352b`
  — idéntico al registrado en
  [T4/T5 del piloto](piloto-consulta-agente-t4-t5-2026-10-07.md).
- Manifiesto interno: 66 fuentes — 21 `pilot-cedro`, 21 `pilot-olmo`,
  21 `pilot-pino`, 3 decoys. Se importaron **sólo las 42 del plan**
  (cedro+olmo), con verificación de hash por archivo contra el manifiesto.
  Las rutas del manifiesto son absolutas del piloto original y se
  rebasaron a la extracción. El manifiesto retiene tres fuentes con
  `hold_after_import` — `s009-r1` de cada proyecto, que en el tarball viven
  como `.held` con bytes idénticos (hash verificado igual); las de cedro y
  olmo están entre las 42 y se importaron desde su `.held`.
- Resultado: **42 admisiones** `imported` con recibo de identidad y hash
  cotejados; `source_revisions_v3` = 42 documentos; cabezas por proyecto
  **19+19**, porque `s002` y `s019` tienen dos revisiones cada una en el
  manifiesto (21 entradas ≠ 19 `source_id` únicos).

## Instancia

mongod v8.3.7 dedicado, loopback `127.0.0.1:37036`, réplica set `rs036` de
un nodo, base `skopos_test_pilot_drill`. Creada para este ensayo y
**destruida al terminar** (puerto verificado cerrado); nunca la instancia
operativa H25.2 (37030) ni la 27017.

## Política del consumidor

`skopos/source-consumer-access-policy/v0.1`, `consumer_id:
t3-drill-consumer`, `allowed_projects: ["pilot-cedro"]`, uri/base apuntando
a la instancia del drill. SHA-256 canónico del archivo:
`f3e4d63798f46af9235b416662f7661cc3e67135b14195ea85cffc638dbdef6b`.

## Ensayo espejo — seis llamadas por la CLI real (`python -m skopos source`)

| # | Operación | Salida |
|---|---|---|
| 1 | `search umbral --kind runtime-events` cedro | exit 0; 1 resultado; `access` con `t3-drill-consumer` y el digest de la política |
| 2 | ídem `pilot-olmo` | exit 1; **stdout vacío**; stderr `project_not_allowed` |
| 3 | `receipt` olmo con identidad **real** (fuente existente) | exit 1; stdout vacío; `project_not_allowed` — no distingue existencia |
| 4 | `fetch-runtime` olmo | exit 1; stdout vacío; `project_not_allowed` |
| 5 | `fetch-runtime` cedro | exit 0; proyección verificada con `status`, `locator`, hashes y `access` |
| 6 | `import` bajo política (cedro) | exit 1; `operation_not_allowed` antes de conectar |

Término de búsqueda `umbral`, extraído del texto de mensaje de la fuente
`s001-r1` («umbral-cedro: el valor vigente autorizado es Azul-17.»).
Archivo de recibos completo en `t3-drill.json` del directorio transitorio
del drill; su contenido esencial está replicado en esta página porque la
ruta muere con la limpieza temporal.

**Fuga de contenido o existencia del proyecto ajeno: ninguna detectada.**
Los tres rechazos de olmo dejaron stdout vacío y el mismo código, con
identidad real registrada en la base (llamada 3).

## Derroteros del ensayo (transparencia)

Tres corridas fallidas antes de la buena, todas documentadas en su momento:

1. Rutas absolutas del manifiesto inexistentes → rebase a la extracción más
   manejo de `.held`.
2. Aserción de conteo equivocada: exigía 21 cabezas por proyecto cuando el
   manifiesto trae multirrevsión (19 `source_id` únicos, 42 admisiones).
3. El término de búsqueda salía de la fila de sesión (`"id":
   "synthetic-s001"`), metadato que no vive en las proyecciones de texto:
   la búsqueda devolvía cero con el guard funcionando. Se extrajo el
   término del texto de mensaje. La primera hipótesis (ventana de
   visibilidad de lecturas majority tras transacciones) quedó **refutada**
   al persistir el fallo; la espera acotada se conservó en el guion como
   defensa y resultó innecesaria (cero segundos).

## Límites

- El ensayo ejerce la frontera de consumidor contra datos reales del
  piloto, no multiusuario: monousuario vigente (decisión 2026-10-06).
- No cubre la pasarela CTIM (fuera de alcance por diseño del plan).
- La instancia efímera no replicó la autenticación del laboratorio original
  del piloto; el plan no la exige y el aislamiento probado es de política,
  no de red.
