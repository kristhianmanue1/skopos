# Ronda adversarial final: custodia base y primer perfil PDF

Fecha: 2026-10-08. Alcance: propuesta documental, no fase implementada.
Artefactos finales revisados:
`docs/propuestas/2026-10-08-contrato-base-custodia-fuentes.md` y
`docs/propuestas/2026-10-08-perfil-pdf-solicitud-b-expertogobernanza.md`.
La revisión de `2026-10-08-perfil-pdf-solicitud-b.md` cubrió v0.1 antes de
estas correcciones; esta acta la complementa, no reescribe su cronología.
Revisor: misma instancia redactora. Es **autorrevisión adversarial**, sin
revisor de contexto fresco ni quórum de cierre de fase según
`docs/planes/plan-ciclo-precondiciones.md`.

## Refutaciones y disposición

| ID y severidad | Contraejemplo e impacto | Corrección incorporada | Residual |
|---|---|---|---|
| B1 · ALTO | Un `.py` aislado se presenta como repositorio completo; un Excel no incluye vínculos externos. | v0.1 admite sólo `single_object` y rechaza conjuntos con `unsupported_scope`; exige decisión y manifiesto futuros para conjuntos. | Semántica y límites de manifiesto pendientes de decisión. |
| B2 · ALTO | Todos los bytes de un PDF se custodian, pero portada y organigrama no se extrajeron fielmente. | `capture_coverage` y `extraction_coverage` separados; correspondencia de contenido distinta de hashes mecánicos. | Evaluación visual/humana de OCR y diagramas pendiente. |
| B3 · ALTO | Una promesa genérica abre Word/Excel/video sin límites y ejecuta contenido activo. | Custodia de bytes separada de parsers; perfiles explícitos, límites, sin red ni ejecución por defecto; `unsupported_format` para extracción sin perfil. | Aislamiento de parsers y presupuestos numéricos por definir/probar. |
| B4 · ALTO | Mongo confirma una revisión mientras el archivo original no quedó durable o se pierde en respaldo. | Protocolo recuperable candidato, reconciliación y ensayo de cortes; respaldo/restauración conjunta de objeto, manifiesto y metadatos. | Atomicidad entre sistemas no demostrada; elegir almacén y probar corte real antes de admisión. |
| B5 · MEDIO | Mismo hash entre proyectos causa acceso cruzado o borrado prematuro. | Identidad lógica y referencia opaca distintas del hash; sin deduplicación entre ámbitos en primer incremento. | Política multiusuario futura no cubierta. |
| B6 · ALTO | Recibo PDF nombra versión del perfil pero no contrato bilateral ni política concreta. | Recibo liga contrato/versión, solicitud/digest, perfil, política/versión, material/revisión y hash; el consumidor conserva `disposicion_id` y gate. | Campos, transporte y aceptación bilateral pendientes; esquemas productores/consumidor no homologados aún. |

## Nueva falsación del texto corregido

1. **Objeto sin perfil:** se admite una copia bajo política de custodia, pero
   el consumidor solicita cita. La respuesta prevista es `unsupported_format`
   para esa operación; recuperar bytes no se etiqueta como cita. No hay
   implementación que demuestre el rechazo.
2. **Recibo viejo, objeto retirado:** el recibo puede ser auténtico como
   historial de admisión sin probar disponibilidad actual. El contrato exige
   lectura y hash al recuperar; el ensayo de retiro sigue pendiente.
3. **Dos copias iguales con retenciones distintas:** mismo SHA-256 no autoriza
   un único objeto físico ni iguala permisos. El contrato separa identidad y
   política. Falta comprobarlo con dos ámbitos en fixtures.
4. **Corte entre archivo y Mongo:** el texto deja una estrategia recuperable,
   no afirma transacción conjunta. Hasta probar estados de corte y limpieza
   de huérfanos, no se puede llamar conforme al almacén.
5. **Contrato consumidor no aceptado:** sus campos son una solicitud; que
   ambos borradores digan v0.1/v0.2 no establece compatibilidad. La puerta
   bilateral permanece explícita.

Veredicto documental: **fix-and-retry** para aceptación o implementación.
Los hallazgos B1–B6 quedaron incorporados al candidato; la fidelidad de la
redacción se revisó en esta instancia, no por un tercero. El siguiente paso
es decisión bilateral sobre contrato base, custodia, primer perfil y fixtures;
luego revisión de contexto fresco, implementación y conformidad por separado.
No se modificaron ADR aceptados, contratos vigentes, runtime, PDF ni corpus.
