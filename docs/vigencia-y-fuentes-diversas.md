# Vigencia y fuentes diversas — 2026-09-26

## Corrección aplicada al lector

ADR-007 exige servir sólo la versión vigente. La búsqueda aplicaba texto y
proyecto antes de elegir la mayor versión entre coincidencias. Si v1 contenía
«zeppelin» y v2 ya no, devolvía v1. También resucitaba v1 al filtrar un proyecto
que se había corregido en v2.

Se conserva el orden de relevancia y se contrasta cada candidato con todas sus
versiones, leyendo sólo identidad/versión en lotes de hasta 1000 identidades.
La nueva versión que no coincide no se devuelve en lugar de la vieja: el
resultado correcto es ninguna coincidencia para esa identidad. No se modifican
almacén, versiones, parser ni índices de producción.

Cinco regresiones contra Mongo real en bases efímeras exclusivas:
- antiguo coincidente / vigente no coincidente;
- vigente coincidente (control positivo);
- cambio de proyecto;
- legado sin versión y otra identidad no afectada;
- dos versiones coincidentes, sin duplicados.

Antes del parche: tres fallos y dos controles correctos. Después: cinco pruebas
correctas. El caso legado detectó además que una proyección de índice puede
representar la versión ausente como null; se normaliza a 0 en la lectura de
versiones, respetando ADR-007. No se han importado datos reales.

Límite: las lecturas no forman una transacción snapshot. Una inserción posterior
a la comprobación puede volver a cambiar la vigencia. La corrección acredita
el caso estable y descarta versiones reemplazadas visibles durante la segunda
lectura; no promete actualidad atómica ante escrituras concurrentes. El corpus
histórico sigue almacenado y puede afectar puntuaciones/latencia del índice.

## Dirección del Operador: Skopos admite fuentes diversas

Las sesiones CLI son los adaptadores actuales, no el límite conceptual del
producto. La ampliación comprende diálogos de reuniones, chats, mensajería,
código y otras fuentes con contratos propios. Esta dirección no significa que
ya estén implementados sus importadores.

Propuesta para el primer incremento: transcripción de reunión sintética o
anonimizada en archivo local, más una revisión correctiva. Conservar:

| Dato | Sentido |
|---|---|
| Identidad estable y tipo de fuente | Distinguir origen de su representación |
| Revisión y relación con la anterior | Saber qué cambió sin destruir historia |
| Localizador nativo | Tiempo/hablante en reunión, ID en chat, commit/ruta/líneas en código |
| Contenido recibido y huella | Volver exactamente a la copia observada |
| Fecha y alcance de captura | Separar evento de importación y declarar cobertura parcial |
| Integridad, acceso y redacción | Diferenciar verificación, falta de acceso y contenido retirado |

No forzar reuniones o código a tener usuario/agente ni inventar offsets en
orígenes de filas. No confundir editar la fuente con corregir el análisis:
ADR-007 resuelve lo segundo; el contrato futuro debe representar también lo
primero. Una huella no demuestra que una conversación esté completa.

Criterio del piloto: importar, deduplicar, aplicar revisión, buscar lo vigente y
recuperar el fragmento exacto; probar además captura incompleta y origen no
accesible. Ágora consume mediante contrato opcional; AN-KLA no recibe escrituras
automáticas. La selección, transformación y admisión son operaciones distintas.

P-007 pertenece a otra reparación: la hoja de ruta registra su cierre histórico.
Este cambio corrige las referencias atrasadas de README y guía rápida; no repite
reindexación ni certifica de nuevo aquellas cifras.

## Verificación adicional y límite observado

La suite completa inicial ejecutó 293 pruebas: OK, una omitida. Emitió avisos de
clientes Mongo sin cerrar. Uno identificó un defecto previo en el test del banner
`watch`: simulaba la colección de análisis, pero no `coleccion_turnos`, que usa
la base predeterminada y asegura índices. La ingesta estaba simulada y no se
llamó; no hay snapshot anterior que permita atribuir cambios de índices.
Se añade la simulación ausente y se comprueba el índice pasado al ejecutor.
No se declara que aquella corrida evitara toda operación sobre producción.
