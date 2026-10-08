# Ajuste focalizado: entrega opcional y antecedentes de procedencia

Fecha: 2026-10-08. Alcance: propuestas `skopos/source-custody/v0.1` y
`skopos/pdf-profile/v0.2` para Solicitud B de expertoGobernanza. Es una
autorrevisión documental del mismo redactor, sin aceptación bilateral ni
revisor independiente. No se ejecutó admisión ni recuperación PDF.

| Hallazgo adversarial | Impacto | Corrección aplicada | Riesgo residual |
|---|---|---|---|
| Un campo `source_ref` único mezclaba entrega del PDF con custodia futura. | Un archivo lateral temporal podía parecer recuperable después de su retirada. | `source_delivery` distingue referencia autorizada de archivo lateral; `custody_mode` fija aparte quién conserva bytes. Referencia verificada exige copia duradera del consumidor. | Transporte, raíces, retención y prueba de recuperación siguen sin acuerdo ni implementación. |
| Una ficha o URL podía confundirse con evidencia suficiente de la fuente. | Se aceptaría origen u oficialidad no comprobados. | `provenance` es opcional y atribuida; se distingue hash de la ficha, hash del PDF y comprobación externa específica. Ausencia queda `unknown`. | La veracidad de las afirmaciones y vigencia jurídica requieren evaluación del consumidor. |
| Los metadatos de origen podían permitir `ok` sin leer el PDF. | Solicitud B prometía bytes inexistentes o no recuperables. | Nueva admisión exige bytes legibles, verificación de longitud/hash y modo de custodia sostenible; fallo de entrada o recuperación queda tipado. | Hay que probar admisión, pérdida, alteración y entrega antes de conformidad. |
| Una ficha cambiada podía conservar un digest viejo en ejemplos. | El ejemplo no representaría los bytes actuales de la ficha. | El ejemplo marca `record_sha256` como observación local que se recalcula al usarlo. | Una nueva edición de la ficha invalida el digest ilustrativo. |

Resultado: propuestas documentales corregidas para revisión bilateral.
Ningún cambio en ADR, código, almacén, PDF, consumidor o memoria gobernada.
La opción de entregar el PDF no decide que Skopos guarde copia propia ni que
sus derivados sean útiles para el gate de expertoGobernanza.

## Enmienda documental posterior del 2026-10-08

La ficha actual de expertoGobernanza documenta un cotejo puntual de su PDF con
una descarga HTTPS de la URL IMSS mediante SHA-256, tamaño y `cmp`. Se atribuye
esa ejecución al consumidor; en Skopos se releyó la ficha y se recalcularon
los hashes locales del PDF y la ficha, sin repetir la descarga. Los borradores
ahora distinguen esas evidencias de autenticidad institucional y vigencia.

La autorrevisión del ejemplo final detectó que `fetch_original` aceptaba una
`source_ref` nueva, que podía sustituir la referencia fijada al admitir. Se
retiró ese campo de la solicitud de recuperación. La solicitud separada de
`admit_original` incluye todos los campos propuestos y un digest recalculado
sobre la línea JSON exacta; las dos respuestas hipotéticas de recuperación
correlacionan con su nuevo digest. Se añadieron casos falsables para ficha
ausente, hashes discordantes, bytes inaccesibles y referencia retirada.
Esto sigue siendo revisión del redactor, no conformidad de runtime.
