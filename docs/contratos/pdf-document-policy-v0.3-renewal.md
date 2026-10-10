# Perfil documental PDF v0.3 — revisión de custodia renovada

Estado: implementado para el laboratorio local RS1 CTIM. Este perfil añade
`skopos/pdf-document-policy/v0.3` y
`skopos/pdf-document-host-config/v0.3`; conserva v0.2 y sus políticas
inmutables. La diferencia contractual de v0.3 es que `source_revision` acepta
un entero positivo menor que `2**63`, en vez de estar fijado en 1. La revisión
debe coincidir con la política de custodia que fija el host. Identidad, hash
original, procedencia, retención y hashes de motores se verifican como en v0.2.

La renovación de RS1 usa revisión 2 del mismo material y SHA-256 original.
La política de custodia y la documental vencen el 19 de octubre de 2026 a las
16:00 UTC. El nuevo recibo y cada manifiesto se correlacionan con esa revisión;
los recibos y manifiestos de revisión 1 permanecen históricos. La ampliación
de retención no adjudica procedencia, fidelidad, vigencia jurídica ni admisión
al corpus. El original sigue bajo referencia externa verificada: la lectura
posterior depende de que el archivo permanezca accesible y conserve sus bytes.

Ninguna solicitud puede escoger raíces, política, revisión alternativa o
motor. La falta de política vigente, discrepancia de revisión, cambio de hash
o pérdida de referencia produce fallo cerrado. La retirada posterior al plazo
requiere la operación explícita del responsable conforme al perfil; este
cambio no ejecuta una retirada automática.
