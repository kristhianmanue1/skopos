# H25.2 — segundo origen: eventos de runtime

Estado: diseño propuesto por encargo del Operador, no implementación ni
aceptación de un nuevo contrato productivo. INFORMS: ADR-020 y SPEC-007.
La autorización de merge de H25.1 no activa este adaptador ni amplía permisos.

## Diferencia estructural y frontera

Entrada candidata: exportación local JSONL UTF-8, un objeto por línea, con
IDs nativos y relaciones entre eventos. No audio, intervalos diarizados ni
roles usuario/agente inventados. Primera versión manual, snapshot de archivo;
no suscripción al runtime, watcher, red ni LLM. Exportar no prueba completitud.
Elegir un runtime/export real sigue siendo una decisión pendiente: el formato
de abajo es fixture de diseño, no se atribuye a ningún proveedor.

Ejemplo sintético (cada objeto es una línea):

```json
{"event_id":"e1","event_type":"message","parent_ids":[],"occurred_at":null,"payload":{"text":"Solicitud sintética"}}
{"event_id":"e2","event_type":"tool_result","parent_ids":["e1"],"occurred_at":null,"payload":{"text":"Resultado sintético"}}
{"event_id":"e3","event_type":"message","parent_ids":["e2"],"occurred_at":null,"payload":{"text":"Respuesta sintética"}}
```

Proyecto, source_id, revisión, captured_at y procedencia del export se entregan
explícitamente. event_id sólo es único dentro de la fuente/revisión. El runtime
puede declarar IDs estables entre exports, pero el adaptador no lo presumirá.
No inferir secuencia causal desde timestamp o posición de línea. parent_ids
son declaraciones de relación; preservar padres fuera del recorte como
referencias no resueltas, nunca como ausencia de evento en el runtime.

## Localizadores y compatibilidad

Localizador por evento: rango de bytes de la línea original, event_id y
hash de esos bytes. JSON Pointer identifica el campo payload seleccionado.
El texto decodificado de JSON NO equivale al slice original (`\u00e9`, escapes,
espacios y orden de claves pueden diferir). Fetch deberá devolver evidencia
original y representación derivada diferenciadas, con sellos propios.
No reutilizar _fragment diarizado, que presupone texto == slice UTF-8.

Recomendación: sobre versionado nuevo con unión explícita de localizadores y
adaptador despachado por formato declarado. No ampliar silenciosamente v0 ni
reclasificar documentos existentes. Antes de implementar, ADR que precise
source-envelope/v1, compatibilidad del almacén v3 y formato de salida de fetch.
Los contadores de revisión de fuente siguen separados de los de análisis.

## Casos de aceptación propuestos

1. Bytes y hashes idénticos al export recibido; JSON equivalente con distinto
   whitespace es una revisión de bytes distinta, aunque su contenido coincida.
2. ID repetido dentro del export: rechazo explícito, incluso si el texto coincide;
   IDs distintos con mismo texto se conservan como eventos distintos.
3. Orden no causal permitido; ciclos declarados diagnosticados, sin repararlos
   ni producir una relación causal verificada. Fijar política en el nuevo ADR.
4. Claves JSON duplicadas, UTF-8 inválido, última línea incompleta y campos
   obligatorios ausentes: rechazo completo, sin importar parcialmente.
5. Evento desconocido: preservación como evidencia opaca con diagnóstico y
   sin ejecutarlo; salida acotada. Ninguna llamada de herramienta se reproduce.
6. Escapes, Unicode, CRLF y objetos anidados: cada fetch reconstruye el evento
   desde sus bytes; nunca usa offsets de una serialización derivada.
7. Replay/corrección/CAS/fallo de commit mantienen las propiedades H25.1;
   revisión nueva no resucita eventos retirados de la vista vigente.
8. Límites preliminares 16 MiB/10000 eventos y profundidad JSON acotada a decidir;
   BSON y salida tienen límites propios. Cero truncado silencioso.

## Secuencia y decisiones

Elegir export real y licencia/permisos → ficha de formato → ADR y fixtures →
constructor puro → integración y regresión diarizada → piloto autorizado →
adjudicación propia. Primer paso ejecutable: elegir runtime/export; no se
presenta este fixture inventado como evidencia de interoperabilidad real.
Hito 25 permanece abierto hasta cumplir esa aceptación. No es dependencia
para activar correcciones de H25.1, que conserva su alcance y decisión propios.

## Autorrevisión del diseño

Misma instancia autora/revisora. Correcciones incorporadas: no equiparar texto
JSON decodificado con bytes originales; no inferir causalidad por orden; no
confundir export completo con captura completa; no anunciar soporte de runtime
sin reconocer un formato real. Residuales: contrato de ciclos, profundidad,
eventos opacos y compatibilidad final requieren el ADR siguiente.

## Continuación autorizada y dependencia de entrada — 2026-10-05

El Operador autorizó implementar el segundo origen junto con las otras tres
acciones. La autorización de trabajo está resuelta; runtime/export concreto
sigue sin identificar. Se solicitó sistema y ruta: no se reemplaza esa decisión
con un formato inventado presentado como interoperable. No hay adaptador nuevo
implementado por este pase ni aceptación de source-envelope/v1.

Ficha mínima para destrabar: runtime y versión declarados, ruta de un export
local autorizado, formato/encoding observado, ejemplo saneado de mensaje y de
resultado de herramienta, campo ID nativo, relaciones, reloj y completitud
declarada, lectores/retención. No hace falta exportar credenciales ni ejecutar
las herramientas descritas. Conservar desconocidos donde el runtime no informe.

Orden de implementación autorizado una vez identificada la muestra:
reconocimiento read-only → ADR de localizadores y fetch → constructor puro con
fixtures derivados saneados → integración explícita SourceStore → regresión
diarizada completa → piloto temporal → revisión del artefacto final.
No migrar v0 silenciosamente ni activar producción; merge del adaptador y
aceptación de sus resultados se resuelven con su evidencia final.
