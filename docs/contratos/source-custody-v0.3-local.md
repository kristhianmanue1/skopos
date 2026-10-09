# Custodia local de fuentes PDF/HTML v0.3

**Estado:** perfil implementado para laboratorio local de expertoGobernanza.
No sustituye `source-store-v3`, no admite documentos al corpus y no adjudica
vigencia jurídica. El perfil PDF v0.2 conserva contrato, colecciones y recibos.

## Frontera y autoridad

El host carga una política `skopos/source-custody-policy/v0.3` desde ruta
absoluta y atiende `expertogobernanza/skopos-source` `v0.3` por
`skopos/source-custody-host/v0.3`. La llamada al socket sólo entrega
`envelope_ref`; la política fija Mongo, raíces, materiales, bytes esperados,
formato, dueño atribuido, clasificación descriptiva, plazo y límites.
Una solicitud no añade raíces ni materiales. La política debe tener exactamente
un `provenance_root` existente y una lista exacta `allowed_materials`; cada
entrada incluye `material_id`, revisión, referencia relativa, SHA-256, tipo
`application/pdf` o `text/html`, referencia y SHA-256 de ficha.

El original se abre bajo `source_root`; la ficha atribuida se abre bajo
`provenance_root`. Ambos usan descriptor de directorio y rechazan componentes
`..`, rutas absolutas y enlaces simbólicos. `verified_external_reference`
verifica de nuevo bytes y ficha en cada recuperación. `provided_file` sólo es
transporte y exige una referencia persistente idéntica bajo `source_root`.
La política de este piloto termina el 2026-11-08T00:00:00Z; el agente eligió
ese límite acotado por continuidad con los pilotos PDF locales, dentro del
encargo de ampliación del Operador. No representa retención indefinida ni
aprobación institucional para otros despliegues.

El sobre y el recibo conservan correlación por `request_id` y
`request_sha256`. `admit_original`, `receipt`, `fetch_original` y
`describe_capabilities` son las operaciones. Los originales v0.3 se guardan
en `source_custody_revisions_v1` y cabezas en `source_custody_heads_v1`,
separadas de `pdf_custody_*`. Se exige Mongo con transacciones. Errores
tipados incluyen `material_not_allowed`, `hash_mismatch`,
`retention_policy_missing`, `policy_mismatch`, `path_outside_root` y
`permission_denied`. Un SHA identifica bytes observados; la URL de la ficha
es procedencia atribuida, no prueba de igualdad con el sitio remoto.

## Derivación y cobertura

Para PDF, una política `skopos/pdf-document-policy/v0.2` por material puede
usar el motor existente con `SourceDocumentStore`. Este adaptador verifica el
recibo v0.3, el SHA del original y el de la ficha bajo raíces distintas antes
de derivar o servir. No cambia el motor PDF fijado por hash ni sus políticas
anteriores. Texto nativo, OCR y grafo se limitan a páginas y modalidades que
la política declare; el manifiesto indica `fidelity_status=unreviewed` hasta
cotejo externo. El límite del perfil DA es 403 páginas físicas, pero la corrida
de este piloto sólo derivó p1 y p282. El perfil CTIM limita 91 páginas y la
corrida sólo derivó p3, p6, p15 y p20.

La política de custodia v0.3 puede listar varios materiales; el loader de
derivados v0.2 sigue exigiendo exactamente uno por política. El adaptador
selecciona por `material_id` y revisión y rechaza coincidencias ambiguas.
Lee el recibo en primario con read concern `majority`. Esto no habilita aún
una política de derivados multifuente ni demuestra aislamiento multiusuario.

Para HTML DOF, `html_derivative.py` produce un artefacto **local**, fuera
del contrato de host de derivados PDF. Acepta Latin-1 declarado o UTF-8
declarado/inferido tras decodificación estricta; rechaza otras codificaciones.
No ejecuta scripts ni CSS. Cada segmento lleva bytes
`[start_byte,end_byte)`, SHA-256 del fragmento crudo y del texto decodificado,
`item_id`, línea y texto. `parser_visible_text` describe el alcance; el
artefacto fija versión y SHA-256 del extractor, con estado `unreviewed`.
No certifica orden visual, visibilidad CSS, apartado
normativo, actualización posterior ni equivalencia con una vista imprimible.
La ancla reproducible es el offset y hash del fragmento original; el apartado
queda `unknown` hasta revisión del consumidor.

## Relación con la propuesta del consumidor

La propuesta `consulta-fuentes-aria-v0.1-propuesta.md` de expertoGobernanza
solicita un expediente bilateral con localizadores, relación entre fuentes y
prueba de reinicio. Este incremento entrega originales recuperables, dos
manifiestos PDF parciales iniciales, un tercero posterior y dos derivados HTML
locales. La composición mediante
Ágora, revisión visual de cada cita, evaluación de vigencia, admisión jurídica,
DOCX/conversaciones y prueba bilateral completa siguen fuera de este perfil.
No se declara adopción de aquella propuesta ni autonomía de los agentes.

Ejecución identificable, recibos, hashes y comandos:
`docs/evidencia/source-ctim-pilot-2026-10-09.md`.
