# CTIM source access v0.3 — retención de pares servidos

Estado: implementado para el perfil local. Extiende
`ctim-source-access-v0.2-local.md` con retención duradera de pares servidos y
la especificación de la forma canónica de `request_sha256`; las operaciones,
límites y semántica de v0.1/v0.2 no cambian. No modifica la política de
acceso existente: la retención es **optativa por política**.

## Forma canónica de `request_sha256`

El campo de correlación `request_sha256` de toda respuesta es el SHA-256 de
la forma canónica de la solicitud:

```python
json.dumps(request, sort_keys=True, ensure_ascii=False,
           separators=(',', ':')).encode('utf-8')
```

Un consumidor que conserve los bytes de su solicitud puede reproducir la
huella con esa forma exacta y verificar que la respuesta recibida corresponde
a su solicitud, sin depender de la serialización de transporte.

## Retención de pares servidos

Cuando la política de acceso incluye `served_retention_dir` (ruta absoluta),
el canal de servicio retiene cada par petición/respuesta **antes de
responder**: un archivo `<request_id>.json` con esquema
`skopos/ctim-served-pair/v0.1`, ambos objetos en forma canónica y sus hashes
`request_sha256`/`response_sha256`. Escritura atómica sin sobreescritura.

- La retención cubre también las respuestas de error con `request_id` válido:
  la procedencia de un rechazo es parte del contrato.
- Colisión de `request_id` (mismo id servido dos veces): el servicio responde
  `execution_failed` con `error.code: retention_failed` y `stage: delivery`;
  no se sobrescribe el par previo. Reutilizar `request_id` es error del
  consumidor.
- Solicitudes sin `request_id` válido no se retienen ni se sirven como
  retenidas: siguen las reglas de v0.1.
- El consumidor recarga un par con `skopos.ctim_access_retention
  .load_served_pair(dir, request_id)`, que revalida ambos hashes y falla
  cerrado ante deriva (`retention_pair_drift`) o ausencia
  (`retention_pair_not_found`).

Sin `served_retention_dir` en la política, el comportamiento es exactamente
el de v0.2: nada se retiene y nada de lo anterior cambia.

## Límites

La retención acredita qué bytes sirvió Skopos ante qué solicitud; no acredita
fidelidad de extracción, orden visual, atribución jurídica ni vigencia del
original. El tamaño máximo por par retenido es 512 KiB; un par mayor responde
`retention_failed` sin servirse. La retención no sustituye la custodia del
original ni sus ventanas de renovación: la verificación de integridad contra
el original sigue requiriendo acceso a sus bytes por la vía de custodia.
