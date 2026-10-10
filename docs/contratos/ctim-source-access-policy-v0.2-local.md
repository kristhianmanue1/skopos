# Perfil CTIM extensible v0.2 — registro explícito de fuentes

**Estado:** implementado en el lector local; sin perfil v0.2 activado ni
fuente nueva admitida. La política `skopos/ctim-source-access-policy/v0.1`
conserva exactamente siete fuentes. Esta versión de **política** no cambia
las respuestas `skopos/ctim-source-access/v0.1` y `/v0.2`.

El host selecciona un archivo de política absoluto al arrancar. v0.2 usa
los mismos campos superiores cerrados de v0.1: `schema`, `inventory_root`,
`inventory_ref`, `inventory_sha256`, `mongo_uri`, `database`, `socket_path` y
`sources`. El inventario atribuido conserva su esquema
`expertogobernanza/source-inventory/v1`. La lista `sources` de la política
es el registro de acceso autorizado por el host: debe ser no vacía, sin IDs
duplicados y corresponder exactamente al conjunto del inventario fijado por
SHA-256. Ningún `source_id` fuera de ese conjunto se puede consultar. Cada
entrada conserva la política de custodia y, según el tipo, política/derivado
PDF o derivado HTML fijado por hash. En v0.2, cada entrada PDF declara además
`custody_material_id`, que debe coincidir con `material_id` de su política
documental. Esa relación explícita conserva los alias históricos entre IDs
del inventario CTIM y de custodia sin permitir una sustitución implícita.
Sólo `application/pdf` y `text/html`
pertenecen a este lector documental.

Para incorporar otra fuente se prepara **otro perfil host** con inventario
actualizado y hash nuevo, entrada explícita, políticas y derivados propios,
y socket local elegido por plataforma. El preparador
`scripts/source_ctim_access_prepare.py` sigue generando únicamente el piloto
de siete; no añade fuentes automáticamente. El proceso ya abierto rechaza un
cambio del archivo de perfil mediante `policy_mismatch`; se requiere cierre
y arranque controlado con el nuevo perfil. Una solicitud de agente sólo lleva
operación e identidad: no puede crear raíces, entradas, retención ni copias.

Al leer, el gateway verifica perfil/inventario y, antes de entregar contenido,
recibo de custodia, bytes y SHA del original, procedencia y derivado según
su contrato. Un inventario ampliado sin entrada de política, una entrada
sin inventario, un tipo de conversación o una identidad desconocida fallan
cerrados. El perfil v0.2 no otorga acceso a conversaciones ni reutiliza sus
índices, políticas o memoria. Los comandos `source`, `query` y `search`
mantienen sus fronteras existentes; no hay migración de datos.

Esta versión permite registrar un octavo PDF sintético en pruebas del loader
y rechaza un noveno no registrado. Eso demuestra selección por registro,
no custodia real del futuro procedimiento CTIM. Ese documento sigue sin bytes,
ficha, clasificación comprobada, política aceptada ni admisión. Su preparación
documental está en `docs/propuestas/ctim-proposed-procedure-intake-v0.1.md`.
