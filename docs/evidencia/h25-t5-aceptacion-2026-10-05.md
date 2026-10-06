# H25.1 — piloto real y aceptación acotada

Código evaluado: `3c783562e63335023daf0e63590ed8dd3b553601`.
Ejecución T5: 2026-10-06T02:02:53Z (2026-10-05 local).
El Operador respondió «adelante» a aceptar el piloto literal, registrar evidencia
y preparar el cierre. D2b acepta ese resultado; no autoriza merge, migración ni
activación productiva. Este informe AMENDS el estado pendiente de T5/D2b en
`h25-t4-2026-10-05.md`; no sustituye sus pruebas ni cierra el hito 25 completo.

## Evidencia y alcance

Fuente real elegida por el Operador: 123087 bytes, 1186 segmentos. Identidad,
hashes, oráculo previo y ejecutor permanecen en el expediente local privado
`runs/h25-pilot.dQI7zG/`; no publicar transcripción ni derivados. Lectores
acordados: Operador y agente local; sin exportación de contenido a LLM, Ágora
o AN-KLA. Retención durante piloto/revisión; retirada sólo con confirmación,
sin borrar el original. No hay nueva ACL multiusuario ni cifrado acreditado.

Cinco consultas literales predefinidas: las cinco coincidieron con el oráculo;
45 resultados servidos (no necesariamente distintos), seis excluidos por límite.
Cada resultado comprobó hash, offsets y fetch de revisión explícita. Repetición
de importación deduplicada. Revisión 2 mediante sustitución sintética en copia:
el término retirado desaparece de la búsqueda vigente y sigue recuperable por
fetch histórico. No es corrección factual de una reunión.

Fuente ausente por renombrado real de la copia: no se sirve texto; restaurarla
permite fetch como control positivo. Permisos denegados y bytes alterados se
simularon con mocks: no acreditan ACL real ni resistencia a edición concurrente.
Otro project_id no obtiene resultados, pero ese selector no es autorización.
El original mantuvo su hash. Mongo temporal 37031 terminó con exit 0; producción
27017 no se modificó en el piloto. Dos revisiones y una cabeza al terminar.

Una ejecución: importación 83.944 ms, replay 30.235 ms, revisión 33.573 ms;
consultas entre 11.968 y 13.936 ms. No es benchmark ni evaluación semántica.
Completitud, audio e identidad humana no verificados. El oráculo no usa el
parser de producto, pero comparte la semántica literal del contrato.

## O1 — reconciliación operacional, no reparación de fuentes

El servicio productivo fue recuperado por reinicio autorizado de launchd tras
el fatal FTDC FileNotOpen. No se borraron archivos ni se adjudicó causa raíz.
La auditoría de lectura de 2026-10-06T01:37:42Z encontró 17849 turnos y 314
análisis vigentes de 332. Turnos: 1175 fuentes inaccesibles y 197 rangos fuera
de archivo. Muestra determinista de 300 rangos accesibles: 289 hashes correctos,
cinco discordantes, seis excluidos por tamaño. No extrapolar estadísticamente.
Los 4820 orígenes de filas requieren verificación interna separada. Consumidor:
cinco discordancias rechazadas sin texto y 110 controles positivos verificados.
No sumar discordancias de turnos y análisis como fuentes distintas.

Respaldo posterior autorizado en `runs/o1-backup.WPzdQE/`: archivo de
132436740 bytes; restauración en instancia exclusiva 37029, 44232 documentos,
cero fallos. Manifiestos de contenido BSON, conteos, opciones e índices iguales
entre los recorridos de origen y copia. Validate completo sólo en copia: cuatro
colecciones válidas sin reparación. No hubo bloqueo global de escritores;
el primer recorrido se solapó con el dump: no prueba snapshot atómico global.
Respaldo en mismo disco, sin originales externos; conserva referencias rotas.
No se afirma preservación previa al reinicio: el respaldo se hizo después.
Fuentes: README, manifiestos y validation-restored.json del expediente privado;
auditoría en `/private/tmp/skopos-o1-audit.g1wxqh/report.txt` (ruta efímera).

## Autorrevisión adversarial y continuación

Productor y revisor: misma instancia, sin revisión independiente.
Hallazgos documentales corregidos: aceptación no implica activación; respaldo
no implica fuentes sanas; selector no implica ACL; revisión sintética no implica
verdad; latencias no implican escala. Residuales explícitos arriba.
Disposición: PROCEED para registrar aceptación y publicar documentación en rama,
sujeto a suite y gates finales. No habilita merge ni operación v3 en producción.

Prioridades recomendadas:

1. Decidir merge de H25.1 separado de activación; Mongo productivo sigue
   standalone, incompatible con las transacciones requeridas por v3.
2. Diseñar segundo origen estructuralmente distinto: exportación de eventos
   de runtime con IDs y relaciones explícitas, no líneas diarizadas. Empezar
   con fixture sintético; definir localizadores, revisiones, completitud y
   pruebas de round-trip antes de elegir corpus real. Propuesta, no adaptador
   aprobado ni implementado; T6 permanece abierto por ese diseño y cierre.
3. Tratar referencias rotas del corpus legado con plan reversible separado;
   decidir ADR-019 y medir búsqueda léxica en copia antes de embeddings.

Verificación nueva: 354 tests OK sin skips en 97.618 s, harness
`scripts/run_isolated_tests.py` sobre replica set temporal exclusivo 37027,
fixtures sintéticos y Ollama local; log `/private/tmp/skopos-close.0h76oz/tests.log`.
Sin cambios de código de producto ni contratos en este pase.
El gate de tamaño detectó la copia privada de 1186 líneas y el log de
restauración de 1752 líneas. Exención explícita sólo de esas dos rutas en
skevi-gate.json: datos/log generados no son módulos de software; el resto de
runs sigue sujeto al gate. No se borraron artefactos para lograr verde.
AN-KLA rev11 verificada y recuperable sin contenido de la fuente. La memoria
precede a este commit documental, no acredita su publicación futura.
