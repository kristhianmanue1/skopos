# Auditoría de publicación de trabajos pendientes — 2026-10-08

Estado: revisión local para commits separados; no aceptación de H25 ni del
piloto. Base observada antes de esta revisión: `main@6413dc380e1cf7a500cfa72639ab9b91155a385c`.
Autor y autorrevisor: Codex en el checkout Skopos. El Operador autorizó
revisar el contenido restante y usar commit/push para preservar trazabilidad
y limpiar el árbol. No hubo revisor independiente.

## Conjuntos revisados

| Conjunto | Contenido y alcance de publicación | Límite |
|---|---|---|
| H25 documental | Propuesta de cierre, línea base P0 e inventario P1. Se conservan como lectura histórica y propuesta, sin convertirlos en decisión D0 ni aceptación. | No se repitieron Mongo, respaldo, restauración ni consultas de relevancia. Las rutas temporales de P1 son evidencia histórica, no custodia duradera. |
| Manifest | Ajuste descriptivo de `source-store-v3` y runtime. Se precisó que el legado usa `$text` y la fuente runtime usa subcadena verificada. | No declara búsqueda semántica ni ACL multiusuario. |
| Piloto desde agente | Plan v0.5, T0 histórico, controles T1–T3, serie T4–T5, ronda, código experimental y tres paquetes congelados. Se mantiene el denominador v0.4 de 108 slots; v0.5 es sólo corrección separada. | No se adjudicó la rúbrica semántica ni el modelo efectivo o coste facturado. No se activaron hooks globales. |

## Comprobaciones propias antes de publicar

- Los SHA-256 de los paquetes coincidieron con T4–T5: v0.3
  `01c69cdf43c8b1ec94f9a93501c98793a9701eafb0872999b7bb7541e2f10a6c`,
  v0.4 `02d8a0ac4ef2d7e6d200dbf0d4b7f30bde07ad1496b8bd10b496d5f31618352b`
  y correctivo v0.5
  `e75bc220162db97d8cd3be0c3a4345b92310a4f28fc7db9259792dd0324ce431`.
- `freeze-final.json` dentro de v0.3 y v0.4 coincidió con los digests
  documentados. `progress.jsonl` registra 28 inicios/27 cierres/1 fallo en
  v0.3 y 108 inicios/107 cierres/1 fallo en v0.4. La ejecución de
  `verify_delivery.verify` sobre las trazas archivadas devolvió 27 pases y
  `context_budget_exceeded` en v0.3; 107 pases y
  `model_call_budget_exceeded` en v0.4. Esto prueba coherencia del verificador
  actual con esas trazas, no recepción independiente del proveedor.
- Los 16 scripts Python se analizaron sintácticamente, tres JSON se parsearon
  y los dos scripts JS pasaron `node --check`. No se reejecutó el experimento.
- Se inspeccionaron nombres de miembros de los tres tarballs y se buscaron
  patrones de clave privada, encabezado Bearer y asignaciones evidentes de
  secretos en su contenido no perteneciente a `node_modules`; no hubo hits.
  El empaquetador también declara comprobar los valores de credenciales del
  laboratorio. Un barrido por patrones no certifica ausencia universal de
  información sensible. El paquete v0.5 incluye 3,652 miembros de
  dependencias/perfil temporal de OpenCode; se conserva intacto para mantener
  el hash de la evidencia.

- Gates de Skevi: `python3 scripts/check_sizes.py` verificó 328 archivos de
  texto y `python3 scripts/check_plans.py` verificó 2 planes, ambos OK.
  El manifest se parseó con Ruby `YAML.load_file`; el entorno Python del
  proyecto no tiene PyYAML instalado.
- Suite aislada con MongoDB temporal exclusivo en `127.0.0.1:37027`:
  `scripts/run_isolated_tests.py` ejecutó 475 pruebas, todas OK. La instancia
  temporal se detuvo al terminar. No se reejecutó el experimento del piloto.

Un gate verde no adjudica las métricas del piloto ni las decisiones H25.
