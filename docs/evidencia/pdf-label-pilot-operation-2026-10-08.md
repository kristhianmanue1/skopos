# Piloto bajo demanda de candidatos PDF — operación y recibo local

**Estado:** ensayo técnico de Skopos en el Mac del piloto, 2026-10-08.
Contrato: `docs/contratos/pdf-label-candidates-v0.2-experimental.md`.
El socket `label.sock` y Mongo se apagaron al terminar. No se ejecutó cliente
independiente de expertoGobernanza para este contrato v0.2; su cotejo visual
de p1 y p18–22 está en expediente separado.

## Configuración preexistente y preparada

El host usa `runs/pdf-document-imss-pilot-v1/label-host.json` y
`label-policy.json`, archivos locales privados `0600` ignorados por Git.
Ambos se prepararon una vez a partir de la política v0.1 aceptada y del
manifiesto gráfico exacto, sin crear raíces nuevas ni extender vigencia.
El digest canónico de política de rótulos es
`21540db84c1b6b10cdbd433392caa6ed66b26d9820814c227d2d08dec948be1d`;
el de la política v0.1 padre,
`4d09e940ea340ea686c77b4fab84dcf8bb05a371c2119434e60d8744227b3c6b`.
El manifiesto gráfico padre conserva SHA
`8a1880b84b0e52f934f09759f3a83efb5a3a752afda914d6c5cce9c7803aaaee`.
`label-policy.json` fija páginas 18–22, 1 por petición, máximo 40 nodos,
sin red ni persistencia de respuesta, y vence con v0.1 el
`2026-11-08T00:00:00Z`. El host verifica el digest de la política de
rótulos contra `label-host.json` en cada petición. La política v0.1 conserva
los JSON/sobres de solicitud bajo el `requests_root` preautorizado hasta
retiro explícito; **no** es una sesión sin persistencia.

## Ejecución reproducible

Desde `/Users/krisnova/www/aria/skopos`, con los archivos privados y la
venv existentes:

```bash
.venv/bin/python scripts/pdf_label_pilot_smoke.py
```

El script exige `preflight=ready_to_start` y digest exacto, inicia el Mongo
dedicado y el host hijo, crea solicitudes con `O_EXCL` y permisos `0600`,
consulta cada página, prueba cuatro rechazos, simula perder una respuesta,
repite el mismo sobre, reinicia sólo el host propio y repite. Su `finally`
apaga host y Mongo; comprueba ausencia de socket y cierre del puerto 37034.
No toma control de un socket preexistente. Las solicitudes permanecen bajo
la retención aceptada; no borrarlas para repetir el ensayo.

Para una sesión de consumidor, iniciar Mongo con
`.venv/bin/python scripts/pdf_custody_pilot.py start` sólo después del
preflight, luego iniciar el host en primer plano con:

```bash
.venv/bin/python -m skopos.pdf_label_host serve \
  --config /Users/krisnova/www/aria/skopos/runs/pdf-document-imss-pilot-v1/label-host.json
```

El consumidor coloca solicitud y sobre bajo el `requests_root` de la
política; fija `envelope_ref` a la ruta relativa del sobre y llama:

```bash
.venv/bin/python -m skopos.pdf_label_host request \
  --socket /Users/krisnova/www/aria/skopos/runs/pdf-document-imss-pilot-v1/label.sock \
  --envelope-ref "$envelope_ref"
```

Al salir debe detener su proceso de host y
usar `.venv/bin/python scripts/pdf_custody_pilot.py stop`. Para la prueba
completa de arranque y apagado, usar el script anterior. Un timeout exige
repetir **el mismo sobre** antes de crear una nueva solicitud.

## Recibo observado de integración

La última corrida identificada por prefijo de solicitud
`eg-imss-label-v02-f931835f` devolvió:

| Página | Nodos | Conectores detectados | Aristas derivadas | Conectores no resueltos | Sin nativo | Sin OCR |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 18 | 8 | 2 | 7 | 0 | 8 | 0 |
| 19 | 32 | 10 | 19 | 3 | 0 | 9 |
| 20 | 10 | 4 | 9 | 0 | 0 | 2 |
| 21 | 19 | 6 | 5 | 4 | 0 | 4 |
| 22 | 17 | 6 | 5 | 4 | 0 | 3 |

Todos los `graph_status` fueron `partial`; ninguna cuenta mide conectores
visibles omitidos. El mayor mensaje fue p19 con 39.621 bytes, menor que el
límite de 65.536 bytes. `describe_label_capabilities` declaró solicitudes
persistidas en raíz existente y respuestas no persistidas por este host.

Rechazos observados: p23→`page_out_of_scope`, SHA de manifiesto falso→
`manifest_mismatch`, digest de política falso→`label_policy_mismatch`,
identidad de fuente falsa→`source_mismatch`. En pruebas locales separadas,
bytes PNG cambiados→`render_integrity_failed`, sobre con hash cambiado→
`request_hash_mismatch` y retención posterior a la política padre→
`retention_policy_missing`. Un envío cuya respuesta se cerró sin leer
devolvió la misma respuesta al repetir el sobre; tras reiniciar el host,
volvió a ser idéntica. Al terminar: `label_socket_absent=true` y
`mongo_port_closed=true`. El script comparó el manifiesto y el inventario
de archivos de `derived_root` y `delivery_root` antes/después:
`parent_manifest_unchanged=true`, `derived_files_unchanged=true` y
`delivery_files_unchanged=true`. Los archivos nuevos son las solicitudes
y sobres persistidos en el `requests_root` preautorizado.

Estos controles verifican un intercambio acotado. No hubo mutación real del
PDF ni de los manifiestos para probar corrupción: la ruta de bytes alterados
se ensayó con fixtures y conserva el control positivo de lectura intacta.
Tampoco se midió fidelidad independiente de etiquetas o conectores, ni se
admitió el documento al corpus. P1 no aparece en este manifiesto; su OCR se
recupera del derivado v0.1 correspondiente para cotejo aparte.
