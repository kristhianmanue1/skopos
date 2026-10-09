# Segundo manual IMSS — perfil local separado v0.2

**Estado:** implementación en rama `codex/skopos-imss-0500-pilot`, piloto
monousuario bajo demanda. No implica vigencia jurídica, admisión al corpus,
fidelidad del grafo ni despliegue general. La fuente DPM `2000-002-001`
permanece con su política y sus 188 páginas; este perfil no cambia sus bytes,
identidad, plazo o derivados.

## Identidad y contrato consumidor

| Campo | Valor |
| --- | --- |
| PDF | `0500-002-001_3.pdf`, 80 páginas físicas, SHA-256 `ce665959759f74331464471c71dc9cff107e061de09b8be5419a7cf1302e48b7` |
| `project_id` / `material_id` / revisión | `expertogobernanza` / `imss-0500-002-001-2022` / `1` |
| Custodia | `expertogobernanza/skopos-source` `v0.2`, `verified_external_reference`, política `expertogobernanza/imss-0500-002-001-2022-reference` `v0.2-2026-10-08`, SHA-256 canónico `6a339819659469decb56ec610792eca85a1ec78b927bb04e66c5d090c7048f91` |
| Recibo admitido | `expertogobernanza:imss-0500-002-001-2022:1:ba8eb8c2180d6cc9` |
| Derivados | `expertogobernanza/skopos-document-derivatives` `v0.1`, política `expertogobernanza/imss-0500-002-001-2022-derivatives` `v0.2-2026-10-08`, SHA-256 canónico `6ba80ec17b74325f121b59243e9593c12a5bb272d87f8e9e41a6907cd6f12afc` |
| Raíz de solicitudes | `/Users/krisnova/www/aria/skopos/runs/pdf-imss-0500-pilot-v1/requests` |
| Sockets bajo demanda | misma raíz: `custody.sock`, `document.sock` |
| Plazo de ambas políticas | `2026-11-08T00:00:00Z`; vencimiento bloquea nuevas operaciones, retiro explícito posterior |

La copia fuente y ficha están bajo la raíz ya existente de
`/Users/krisnova/www/expertoGobernanza`; Skopos no escribió allí.
La ficha se fijó por SHA-256
`04164dc8de865957e0c6ea3bce29f47bf2d742beacabe83bf7bfc647e380669a`.
Si cambian bytes o ficha, el host debe fallar cerrado. La clasificación
`consumer_declared_public` atribuye una declaración del consumidor; no
adjudica vigencia, licencia ni admisión normativa.

## Operaciones y límites

El sobre en `requests_root` mantiene `request_file_ref`, `request_sha256`,
`request_id`, `contract_id` y `contract_version`; el socket recibe sólo
`envelope_ref`. No se aceptan rutas, políticas o bases elegidas por solicitud.
`admit_original`, `receipt` y `fetch_original` conservan el contrato de
custodia v0.2. El host de derivados conserva
`describe_document_capabilities`, `derive_document`, `derivation_receipt`,
`fetch_derivative`, `fetch_evidence` y `search_document` v0.1. Las respuestas
correlacionan ID y SHA de solicitud y devuelven razones tipadas. Una respuesta
perdida se reconcilia con `receipt` o `derivation_receipt` usando los bytes
persistidos de la solicitud original; un nuevo ID no es un reintento idéntico.

La política nueva fija máximo 80 páginas; OCR sólo p1 y p37 (a lo sumo dos
por trabajo) y grafo sólo p37. PDFKit extrae texto y cajas; Vision OCR,
Poppler renderiza. Red y vectores deshabilitados. Los consumidores pueden
reducir límites, no ampliarlos. Cada línea/nodo expone `item_id` y `bbox`
normalizada; búsqueda literal informa cobertura y exclusiones. Para consulta
de funciones DPM usar el derivado nativo pp45–46, no inferir su vigencia.

### Fuente en solicitudes de derivados

```json
{
  "material_id": "imss-0500-002-001-2022",
  "source_revision": 1,
  "source_sha256": "ce665959759f74331464471c71dc9cff107e061de09b8be5419a7cf1302e48b7",
  "custody_receipt_id": "expertogobernanza:imss-0500-002-001-2022:1:ba8eb8c2180d6cc9",
  "custody_policy_sha256": "6a339819659469decb56ec610792eca85a1ec78b927bb04e66c5d090c7048f91"
}
```

Una solicitud `derive_document` agrega `pages`, `modalities`, `ocr_pages`,
`graph_pages` y `limits`. Ejemplo para funciones: `pages=[45,46]`,
`modalities=["native_text"]`, listas OCR/grafo vacías y límites dentro
de la política. Para p37 visual: `pages=[37]`,
`modalities=["native_text","selective_ocr","visual_graph"]`,
`ocr_pages=[37]`, `graph_pages=[37]`. El resultado remite al manifiesto;
`fidelity_status=unreviewed` no convierte la extracción en cita verificada.

## Recibos de esta ejecución

| Modalidad | `derivation_id` | `manifest_sha256` | Cobertura observada |
| --- | --- | --- | --- |
| Nativo 1–80 | `e86d5c6ab6d45d1143bc964fdcd4ecfeceda2c4a23965cc693655fd6b643eadd` | `d9eeacbeab511a831999540136c72cb37c62f9aacb859fa6b75389f83e8f1ab0` | 79 páginas `extracted`, p1 `no_text`, 2530 líneas |
| OCR p1/p37 | `6c05342bb617c0ce59a2346840b9a8e3c47eae14fa660703538731187526e433` | `f58f4143b395d222ec64f3472109af26474c9bb56aa0e4cf7000412f81a9b49c` | OCR `extracted` en ambas; p1 sin texto nativo |
| Grafo p37 | `2f6e9554c1f273485c4e06a65d3608072c614df601607d12d43335f2e52c1c82` | `9ed5ee6ddcbdcd679782e6899f672653cee3135eeaf7b3a68f1504aefe1e13e7` | `partial`; 52 nodos/39 aristas sin fidelidad completa |

El render de p37 permite ver «DIRECCIÓN DE PRESTACIONES MÉDICAS», pero el
grafo automático sólo etiquetó esa caja «MÉDICAS». La localización y lectura
visual de una instancia están en
`docs/evidencia/pdf-imss-0500-p37-visual-review-2026-10-08.json`:
la caja usa el `item_id` del nodo y un `bbox`; el trazo entrante se localiza
aproximadamente. No se adjudicó dirección jerárquica desde líneas sin flecha
ni se validaron las 39 aristas automáticas.

## Operación y recuperación

Los archivos privados `custody-policy.json`, `custody-host.json`,
`document-policy.json`, `document-host.json`, solicitudes y derivados viven
bajo `runs/pdf-imss-0500-pilot-v1/` (gitignorado, permisos 0700/0600). El
preparador `scripts/pdf_imss_0500_prepare.py` crea políticas nuevas sin
sobrescribir; `custody` exige PDF y ficha comprobables, `document` exige el
recibo admitido. No volver a ejecutar `admit` con un ID nuevo sobre la misma
revisión: recuperar el recibo persistido.

`scripts/pdf_imss_0500_session.sh comando [argumentos]` hace el preflight,
inicia controlador y tres hosts con sockets distintos (custodia nueva,
derivados nuevos y derivados DPM anteriores), ejecuta el comando y para
únicamente los procesos que inició. Falla si otro controlador ya ocupa el
piloto. Es una sesión de este checkout y no instala arranque automático.

Para servicio local, arrancar el controlador existente con
`scripts/pdf_custody_pilot.py start` sólo si `preflight` pasó y no hay otro
controlador. Con Mongo dedicado activo, iniciar ambos hosts nuevos con sus
configuraciones absolutas, y opcionalmente el host DPM anterior en su socket
propio. Al terminar, enviar `SIGTERM` a los procesos propios, esperar la
desaparición de sus sockets y ejecutar `scripts/pdf_custody_pilot.py stop`
únicamente si esta sesión lo arrancó. No borrar sockets de otro dueño.

Se observó un reinicio completo: Mongo y los hosts se apagaron; tras iniciar
Mongo y el host nuevo, `derivation_receipt` recuperó el manifiesto nativo,
`search_document` localizó nueve candidatos para «Dirección de Prestaciones
Médicas» (uno de p45 con `item_id`
`29e6012580daa92d2bcf9d738152c21a226fff2941a36835a49c78508ec60538`
y `bbox`), `fetch_evidence` devolvió ese ítem y `fetch_derivative` entregó
bytes con el SHA esperado; la copia temporal se retiró. El host DPM anterior
respondió por separado con política `4d09e940...` y límite de 188 páginas.
Su *smoke* de custodia pasó con el segundo registro presente: contó sólo la
identidad DPM, verificó 1,311,822 bytes y retiró su copia de entrega.
También se recuperó la solicitud original cuya respuesta había fallado tras
publicarse el manifiesto y antes de escribirse su recibo; al reenviar sus
**mismos bytes** devolvió `duplicate` y completó el recibo. `receipt` y
`fetch_original` recuperaron 831,726 bytes con el hash de fuente correcto;
se retiró esa copia temporal.
Esto prueba recuperación local observada, no restauración desde respaldo ni
aislamiento multiusuario.
