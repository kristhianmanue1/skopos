# Fuentes CTIM: tres originales iniciales y dos posteriores

**Observado:** 2026-10-09 UTC, checkout Skopos en rama
`codex/skopos-source-profile-v03`. Trabajo local monousuario. El controlador
Mongo del piloto en `127.0.0.1:37034` se inició para esta sesión, se detuvo,
se reinició para recuperación y se detuvo al cerrar. No hay servicio activado
de forma permanente, respaldo/restauración externa ni admisión al corpus.

## Origen y política

El inventario atribuido de expertoGobernanza que se leyó tenía SHA-256
`d86ea943e02506694ad4e33d749228712658367450a423ba362931c6c1303f71`
y corresponde a su commit `7e2c45e2e45aefe30402af8fd160b6968351a351`.
Durante la sesión el inventario de su árbol de trabajo cambió para añadir
otras fuentes; los tres registros de procedencia conservan el hash anterior.
Los originales de esta tabla mantuvieron sus bytes observados. Skopos no
modificó expertoGobernanza. Las URL son declaraciones del inventario; no se
comprobó igualdad byte a byte contra descargas remotas en esta corrida.

| Material | Tipo y bytes | SHA-256 original | Política canónica | Recibo admitido |
| --- | --- | --- | --- | --- |
| `imss-administration-1000-002-001-2025` | PDF, 3,130,438 | `2578bc3df7bafaefd250e971e0087f1b28dc5e9878ed343e8159a23e22d8de49` | `aca345e2ad12f7cef5223f81408c45c2691e84e5f5e770179f8e27c19d4751c3` | `expertogobernanza:imss-administration-1000-002-001-2025:1:2085f4786beebee9` |
| `imss-procedure-2900-003-001-2021` | PDF, 1,707,465 | `141d9b090efa4d70799ee1368350a5167347b4e8cd5f99912fb192ce6c704faa` | `e3e7f92378ca6e0f6085f963f5e83d02204716617f7a4699edd688efbd61df76` | `expertogobernanza:imss-procedure-2900-003-001-2021:1:215b44509c221a64` |
| `dof-pobalines-1000-001-029-2021` | HTML ISO-8859-1, 510,270 | `e088234e624a6172a7e85eb0aed5c338b55c84e399b6ea086cd326f85ddc580e` | `dfb67085a3eaaaaf4fa64e9e0dcdd0633c1fa43697e8d7896df08e12f7e6c6fe` | `expertogobernanza:dof-pobalines-1000-001-029-2021:1:c863ff3c91cb8dd2` |

Cada material tiene política, ficha atribuida, solicitudes, respuestas y
derivados privados bajo `runs/source-imss-ctim-pilot-v1/<material>/`.
La política fija `verified_external_reference`, fuente bajo la raíz local de
expertoGobernanza, ficha bajo la raíz del piloto, clasificación
`consumer_declared_public` y vencimiento `2026-11-08T00:00:00Z`. El agente
escogió ese límite de laboratorio a partir de los pilotos PDF vecinos; es una
elección operativa acotada, no aprobación institucional de retención.
Si se retira la referencia externa, Skopos no puede recuperar el original sin
restauración del consumidor. El original permanece propiedad del consumidor.

## Recuperación y controles

`source_ctim_pilot.py` admitió cada original en Mongo transaccional, cotejó
`receipt`, recuperó 3,130,438 / 1,707,465 / 510,270 bytes y comprobó su SHA.
Las copias de entrega se retiraron. Tras detener y reiniciar el controlador,
`source_ctim_verify.py` recuperó de nuevo los tres recibos y originales.
El control negativo cambió el SHA esperado en una solicitud nueva por material;
los tres devolvieron `material_not_allowed`, sin resultado de admisión.
Los tests de fixture comprobaron además rechazo por cambio de bytes, firma
HTML incorrecta, ficha ausente y host v0.2 con política v0.3. Estos controles
no prueban aislamiento entre usuarios ni restauración desde respaldo.

## Derivados y ejemplos recuperables

| Material | Política de derivado | Manifiesto SHA-256 | Cobertura ejecutada |
| --- | --- | --- | --- |
| DA 1000-002-001 | `ebd7d6f2c6a2375b4d387c08dcc75a3afc253921139aaf35ee9a531b62fdaf6e` | `84f5ef8ebd2934b4d1f3e6802cc2af7117ac85e9687fbd0da0faa7fc4f4a5530` | p1 `no_text`; p282 `native_text extracted`; 2/403 páginas |
| Procedimiento 2900-003-001 | `fbea60836b6f94445ac03da8f34bd675da6eea2ce1ff822c0de430be19540a15` | `773a2900597873c96488142a378b11b86b00bb58c07f3c06c26e98adff789b1b` | p3, p6, p15, p20 `native_text extracted`; 4/91 páginas |

Manifiesto DA: `runs/source-imss-ctim-pilot-v1/imss-administration-1000-002-001-2025/derived/5f1947ce0641ac8014417c8d062c8b38fc0f18c27fd244ee1758d6ee84d41c08/manifest.json`.
Manifiesto CTIM: `runs/source-imss-ctim-pilot-v1/imss-procedure-2900-003-001-2021/derived/863fe610c3543692632280386426193237175b59addd1463f041b268ea42588d/manifest.json`.
El host `search_document` devolvió en DA p282 el ítem
`e86dc026bdee131e9eb9858bfaa71801828583b523b31e5c1585aa1505107784`
para «Coordinación de Proyectos y Seguimiento Institucional», y en CTIM p6
el ítem `b77bca54b5e2727acfc8fc10341a844fc7791d45469d069d74ffc56d9f6d694f`
para «Coordinación Técnica de Infraestructura Médica». `fetch_evidence`
recuperó ambos ítems con `bbox` y `fidelity_status=unreviewed`.
En CTIM p15 el manifiesto contiene el ítem
`cb4169d6bc0d8167e16fa8f7ffeaf5bb2467e33bd36f0c780389c6c5b97d3d73`
para «solicitud de revisión del “Anteproyecto conceptual”».
Los requests/envelopes y respuestas `search-response.json` /
`evidence-response.json` quedan bajo el subdirectorio privado de cada
material (`requests/` y `queries/`).

El HTML produjo `derived/html-text.json`, SHA-256
`2d9812a3d6e15e9a98c8087c84384631a5c9faee64a8864a0d0e239f1f07fc6f`,
con 10,756 segmentos. Ambos derivados HTML fijan el extractor por SHA-256
`405c3acfa6679c124f519494393840ee4015f286f319bf86688eee691ae7fe06`.
Como ancla mínima, el apartado literal «5.1 » aparece
en bytes `[122642,122646)`, SHA-256 del fragmento
`b7d7079dac5d5468e55aa9d19b793f4359df83c6066a89e43af14a7f6fc426d0`,
ítem `e594a8d40939b7f09a288219c53e1f40b762a96f8264353a3e1f9366306cf4c4`.
El parser no interpreta qué abarca jurídicamente ese apartado, no evalúa CSS
ni asegura versión consolidada: el DOF 2021 es antecedente histórico.

## Incremento posterior: POBALINES y acuerdo

Tras los tres recibos iniciales, expertoGobernanza publicó en `main` el
inventario de siete fuentes en commit
`d6812889434b8597ce530fe64e448630d6c05e10`, SHA-256 del inventario
`1f2d218ed0b868ae6c2215a5288a2376435bae071e358edc9fbf1b89c7971c13`.
Dos políticas y dos fichas nuevas se prepararon con esa revisión, sin
modificar las tres políticas ni sus recibos anteriores.

| Material posterior | Tipo y bytes | SHA-256 original | Política canónica | Recibo |
| --- | --- | --- | --- | --- |
| `imss-pobalines-1000-001-029-2022` | PDF, 1,554,158, 78 páginas | `aae49eb2ed265e6379777287afff2f97b42a754aa20ea83acce642adde207843` | `d74c28efcc4ff320f6381d1266594583ce496987e8669ff0b7820bc566b75919` | `expertogobernanza:imss-pobalines-1000-001-029-2022:1:07bd67c2e3623095` |
| `dof-pobalines-1000-001-029-2022-agreement` | HTML UTF-8, 56,892 | `7818f222365e5ef02d1a20a85a0604568b3983e53be6ea8e14b6bee0a7a06532` | `b07dd8691896383f1fff2f9901fbd768e5eb584302bf1a75d02d6f3576b32143` | `expertogobernanza:dof-pobalines-1000-001-029-2022-agreement:1:6d68ab32bdbbc21c` |

Después de otro ciclo de apagado y reinicio, ambos `receipt` y
`fetch_original` devolvieron bytes con el hash esperado: 1,554,158 y 56,892.
Dos solicitudes con SHA falso devolvieron `material_not_allowed`. El
controlador se detuvo al terminar; una consulta posterior de `status` no
encontró socket. No se alteraron los tres registros iniciales.

La política de derivados PDF posterior tiene SHA-256
`e43ec4e686e8d37fa632ed69fe510ea8c185b1b2cb6690a7bfd72cbcf4348b4e`.
Su manifiesto está en
`runs/source-imss-ctim-pilot-v1/imss-pobalines-1000-001-029-2022/derived/4415fa0ec2c206efb829b8a310dfd3dba5ed7d934a4b67da80153de5054b4b5f/manifest.json`,
SHA-256 `9dd220c141bf660fdd251c556deeb7c2b7827f85a1a51bb6c80d3c691a2a67f1`.
Se derivaron p20 y p75: texto nativo en ambas y OCR sólo p75. El host
`search_document` devolvió dos candidatos para «A partir de la entrada en
vigor de las presentes POBALINES»; `fetch_evidence` recuperó el primero en
p75, ítem `a9edf0b2cf3aadca719cdd877beb518d530cbaeb0e0ad364c05b3e555f7aba67`,
con `bbox` y `fidelity_status=unreviewed`. P20 contiene el arranque de §5.1
con ítem `b0e8bfccad1542b1c96c01dab730a80952002d970e55ed020436949ced3dbf65`.
Las solicitudes/respuestas de búsqueda y evidencia quedaron bajo `requests/`
y `queries/` del material, como en los dos PDF anteriores.

El acuerdo HTML posterior produjo 507 segmentos; el derivado en
`runs/source-imss-ctim-pilot-v1/dof-pobalines-1000-001-029-2022-agreement/derived/html-text.json`
tiene SHA-256 `949a7db37ced1b87c484e2007a3c09850d475b9558375117eb54395d2321289a`.
Se decodificó como UTF-8 estricto sin charset declarado. Un fragmento del
acuerdo con «se dejan sin efectos» ocupa bytes `[7154,7259)` del original,
SHA-256 crudo `ababd569873b6204f53cf6b0a029fb1c9e8c371d2579c3f92bd950e563f358f2`,
ítem `2753eb895f2bbf1e362184963dbefd8a96740774e1967aa93337881a12de1eb8`.
Esto permite cotejar la relación temporal con el PDF p75. El dato literal
no constituye por sí solo una adjudicación jurídica de vigencia actual.

## Uso bajo demanda y límites

Desde `/Users/krisnova/www/aria/skopos`, iniciar el controlador con
`.venv/bin/python scripts/pdf_custody_pilot.py start` sólo si el preflight
está listo y no lo inició otra sesión. Para una consulta real al PDF DA,
usar en una terminal:

```bash
.venv/bin/python -m skopos document-host serve --config /Users/krisnova/www/aria/skopos/runs/source-imss-ctim-pilot-v1/imss-administration-1000-002-001-2025/document-host.json
```

En otra terminal del mismo checkout:

```bash
.venv/bin/python -m skopos document-host request --socket /Users/krisnova/www/aria/skopos/runs/source-imss-ctim-pilot-v1/imss-administration-1000-002-001-2025/document.sock --envelope-ref search-envelope.json
```

`evidence-envelope.json` pide el ítem exacto. Para CTIM o POBALINES, cambiar
el directorio de material en ambos comandos; sus solicitudes conservadas
usan los mismos nombres. Los archivos privados `queries/search-response.json`
y `queries/evidence-response.json` permiten revisar la ejecución registrada
sin arrancar un host. El HTML se coteja con offsets y hashes en su
`derived/html-text.json`; aún no tiene una operación `search_document` de host.
Al terminar, parar el host iniciado en esa terminal y detener sólo el
controlador que inició la sesión mediante
`.venv/bin/python scripts/pdf_custody_pilot.py stop`.

La propuesta del consumidor en expertoGobernanza pide también un puente con
Ágora, relaciones entre originales, revisión visual de cada cita, prueba
bilateral de localizadores alterados y evaluación de vigencia. Esos criterios
no fueron ejecutados aquí. Las páginas PDF son parciales; el HTML no tiene
contrato de búsqueda de host, sólo artefacto local. No se ensayó DOCX,
conversaciones ni admisión a AN-KLA. No se atribuye a esta corrida una
decisión de vigente para ninguna fuente.

## Autorrevisión posterior del PR #5

Una revisión externa preliminar señaló el uso de `allowed_materials[0]` en
`SourceDocumentStore._source()`. El loader de derivados v0.2 obliga a una
política por material, por lo que los cinco pilotos no dependían del orden,
pero el adaptador aceptaba una suposición innecesaria. Se corrigió para
seleccionar por `material_id` y revisión y fallar ante cero o varias
coincidencias; la consulta del recibo ahora usa primario y read concern
`majority`, como `PdfCustodyStore`. Un fixture coloca el PDF en segundo lugar
y otro exige rechazo de una coincidencia duplicada. Esta corrección no
cambia las políticas privadas ni los recibos ya admitidos.

Una revisión posterior señaló un registro con `policy_sha256` ausente pero
`record_sha256` recomputado. El adaptador ahora responde
`custody_receipt_mismatch` en vez de propagar `KeyError`; un fixture construye
ese registro y verifica el rechazo tipado. Tampoco modifica recibos existentes.
