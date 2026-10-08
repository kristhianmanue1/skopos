# Perfil productor de derivados PDF v0.1 — propuesta bilateral

**Estado:** propuesta de Skopos para contraste con expertoGobernanza. La
implementación y el contrato no se congelan por este documento.
**Caso:** `expertogobernanza / imss-2000-002-001 / revisión 1`.
El original, ficha, recibo y política de custodia `v0.2` permanecen
inmutables. Derivar no equivale a admitir otra revisión ni al corpus.

## Autoridad y alcance

El host suministra una política **separada** de derivados con ID, versión,
digest, `requests_root`, `derived_root`, `delivery_root`, páginas permitidas,
modalidades, renderizador, OCR, presupuesto de CPU/tiempo/bytes, vigencia y
retención de salidas. Su vencimiento no excede el de custodia v0.2. Un
mensaje del consumidor sólo reduce límites. No se admite red, LLM,
embeddings, búsqueda vectorial, validación jurídica ni promoción al corpus.
La política debe citar el recibo y digest canónico de custodia ya aceptados.

El perfil ejecutable local candidato usa PDFKit para texto y cajas, Vision
`es-ES` para OCR selectivo y Poppler para renderizar páginas. Son mecanismos,
no requisitos del contrato neutral. En este host macOS se observó texto
nativo de 0 líneas en p1 y 7 en p18; OCR de p1 produjo 17 segmentos. Algunas
letras pequeñas fueron incorrectas con confianza reportada de 1.0. La
fidelidad requiere cotejo externo. En otra plataforma se anuncia
`unavailable` hasta probar un adaptador equivalente.

## Sobre y operaciones

Cada solicitud se guarda como JSON bajo `requests_root` con sobre que liga
`request_file_ref`, `request_sha256`, `request_id`, `contract_id` y versión,
igual que la frontera v0.2. El socket recibe sólo `envelope_ref`.
`contract_id=expertogobernanza/skopos-document-derivatives` y
`contract_version=v0.1`; la respuesta usa
`schema=skopos/pdf-document-host/v0.1` y repite identidad/digest de solicitud.

| Operación | Entrada adicional | Respuesta acotada |
| --- | --- | --- |
| `describe_document_capabilities` | `project_id` | ID/versión/digest de política, modalidades con `available|partial|unavailable`, herramienta/versiones realmente ejecutables, límites y errores tipados |
| `derive_document` | `source`, `pages`, `modalities`, `ocr_pages`, `graph_pages`, `limits` | `derivation_id`, estado `created|duplicate`, recibo de solicitud, `manifest_sha256`, resumen de páginas/estados; nunca todas las líneas en socket |
| `derivation_receipt` | identidad y SHA-256 de solicitud original | Mismo recibo tras respuesta perdida, sin reejecutar OCR |
| `fetch_derivative` | `derivation_id`, `artifact_id`, SHA-256 esperado | `bytes_ref`, longitud/SHA-256 y tipo de artefacto; revalida PDF/ficha antes de servir |
| `search_document` | `derivation_id`, término literal UTF-8, límite | Candidatos acotados con original, derivado, manifiesto, `item_id`, página, región, método y cobertura/exclusiones; búsqueda textual exacta, sin ranking nuevo |
| `fetch_evidence` | `derivation_id`, `item_id`, hash esperado | Registro exacto, región y render asociado cuando existe; revalida fuente, ficha, manifest y artefacto |

`source` incluye `material_id`, `source_revision`, `source_sha256`,
`custody_receipt_id` y `custody_policy_sha256`. El host consulta el recibo
v0.2 en la base dedicada y comprueba los bytes actuales del PDF y ficha.
El derivado nunca permite recuperar el original perdido: si éste falta o
cambia, `fetch_derivative`, búsqueda y evidencia fallan cerrados.

`pages` son números físicos 1-based sin duplicados. `modalities` son
`native_text`, `selective_ocr` o `visual_graph`. `limits` tiene
`max_pages`, `max_render_pixels`, `max_seconds`, `max_output_bytes` y
`allow_network=false`; ningún valor puede superar la política. El host
no acepta una página o motor no configurado. Para un inventario de 188
páginas se usa `native_text`; OCR se limita a páginas seleccionadas.
`ocr_pages` y `graph_pages` son listas explícitas, ordenadas y sin repetición,
subconjuntos de `pages` y de la política. Pedir `visual_graph` sin páginas
gráficas produce `invalid_graph_pages`.

## Identidad, páginas y evidencia

`derivation_id=sha256` de JSON canónico con original SHA, política de
derivados, motor/versiones/configuración, páginas, modalidades y parámetros
de render/OCR. Una repetición idéntica devuelve `duplicate`; igual
`request_id` con otros bytes devuelve `request_conflict`. Cambiar motor,
configuración o política produce otra identidad; no sobrescribe el derivado
previo. El manifiesto se publica de forma atómica bajo `derived_root` y
se verifica por SHA antes de recuperación. Salidas bajo `delivery_root`
son copias temporales retiradas después de cotejo.

Cada `page_result` declara página física, rotación, dimensiones/cropbox,
modalidades con `run_status` y `fidelity_status` separados, cobertura y
errores. `run_status=extracted` sólo prueba que el motor produjo salida;
`fidelity_status=unreviewed` evita presentarla como contenido correcto.
Texto nativo y OCR nunca se fusionan silenciosamente. Una página sin
texto nativo tiene `no_text`, aunque la imagen visible tenga palabras.

Cada línea o nodo usa `bbox=[x0,y0,x1,y1]` normalizada 0..1, origen arriba
a la izquierda respecto al cropbox; `page_rotation` viaja aparte. El
`render_sha256` hashea **bytes PNG exactos** del render identificado por
`renderer`, versión, escala, color y rotación; no es hash de una «página»
abstracta ni del original. Una página no renderizada lleva `render_sha256=null`.
`item_id` deriva de manifiesto, página, modalidad, índice y bytes/caja.

`visual_graph` separa `nodes` (caja/rótulo con fuente), `connectors`
(trayectoria visual localizable), `edges` (extremos, conector y
`observed|hypothesis`) y `unknown` (relación no resuelta). Proximidad o
orden de OCR no crean arista. En un organigrama sin flecha, dirección
jerárquica puede quedar `hypothesis` incluso con conexión visible; una
arista `observed` requiere dirección explícita en el render. La revisión
humana del consumidor no se guarda como certificación del productor.
En el piloto, `from_node`/`to_node` indican la hipótesis de lectura
topológica; `direction=unknown` prohíbe tratarlos como dirección observada.
Sólo una punta de flecha detectada en un flujo permite
`direction=observed`. `status=partial` señala que puede faltar nodos o
relaciones; no equivale a inventario completo del diagrama.
Hasta pasar los controles de nodos, conectores y dirección, la oferta de
`visual_graph` será `partial` o `unavailable` y `derive_document` no podrá
devolver una lista de aristas como si estuviera validada.

### Ejemplo de solicitud

```json
{
  "contract_id": "expertogobernanza/skopos-document-derivatives",
  "contract_version": "v0.1",
  "request_id": "eg-imss-derive-r1-native-cover-v1",
  "operation": "derive_document",
  "project_id": "expertogobernanza",
  "source": {
    "material_id": "imss-2000-002-001",
    "source_revision": 1,
    "source_sha256": "719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323",
    "custody_receipt_id": "expertogobernanza:imss-2000-002-001:1:4fbed2bd3d2633aa",
    "custody_policy_sha256": "a92b9252cc27a5a0a421fa1422b583d61cafdb0026956794a302c09db3c52160"
  },
  "pages": [1, 18],
  "modalities": ["native_text", "selective_ocr"],
  "ocr_pages": [1, 18],
  "graph_pages": [],
  "limits": {
    "max_pages": 2,
    "max_render_pixels": 4452000,
    "max_seconds": 60,
    "max_output_bytes": 5000000,
    "allow_network": false
  }
}
```

### Ejemplo de respuesta resumida

```json
{
  "schema": "skopos/pdf-document-host/v0.1",
  "status": "ok",
  "request_id": "eg-imss-derive-r1-native-cover-v1",
  "result": {
    "derivation_id": "sha256:<digest-canonico-del-trabajo>",
    "derivation_status": "created",
    "manifest_ref": "<id>/manifest.json",
    "manifest_sha256": "<sha256-de-bytes-manifiesto>",
    "page_summary": {"requested": 2, "native_extracted": 1,
                     "native_no_text": 1, "ocr_extracted": 2,
                     "visual_graph": "not_run"}
  }
}
```

Los valores entre `<>` del ejemplo son ilustrativos, no recibos emitidos.

## Gates falsables antes de anunciar servicio

1. Sintéticos fijados antes de ajustar: texto nativo, página imagen con
   transcripción, organigrama de dos niveles, flujo con flecha invertida,
   tabla, página rotada, PDF inválido y original mutado. Control positivo
   de OCR; un fallo negativo sin él no prueba ausencia de texto.
2. Manual IMSS: 188 páginas inventariadas; portada p1 OCR cotejado contra
   rótulos humanos; p18–22 con nodos, conectores y relaciones comparados a
   anotación visual previa; texto corriente y página/region recuperables.
   Informar cada `unknown`, error OCR o cobertura parcial.
3. Frontera: hash de original/ficha/política, página fuera de alcance,
   límite excedido, sobre alterado, digest falso de manifiesto, caja/arista
   cambiada, respuesta perdida y output preexistente reciben error tipado.
4. Reinicio: mismo derivado/recibo/manifiesto verificado; colección de
   custodia v0.2 sigue con una revisión/una cabeza. Consumidor repite
   cotejo de bytes, región y cita con cliente propio.
5. Autorrevisión adversarial del diff/artefacto final y gates de ambos
   repositorios. Las actas de productor y consumidor son separadas; esto
   no prueba revisión independiente.

**Puerta de congelación:** acordar esquema con el consumidor y observar
controles positivos/negativos y E2E. Antes, `available` sólo puede anunciarse
para la modalidad específicamente probada; una demostración de OCR no
promueve `visual_graph`.
