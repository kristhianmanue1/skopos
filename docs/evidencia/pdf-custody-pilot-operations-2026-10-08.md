# Operación bajo demanda del piloto PDF IMSS — 2026-10-08

**Alcance:** un solo PDF ya admitido, política
`expertogobernanza/imss-2000-002-001-reference@v0.2-2026-10-08`, modo
`verified_external_reference`, recuperación `while_reference_available`.
La vigencia termina `2026-11-08T00:00:00Z`. Este procedimiento no la renueva
ni crea otra revisión. No hay servicio continuo, respaldo independiente,
aislamiento entre usuarios de OS, OCR ni admisión al corpus.

## Comandos del host

Desde `/Users/krisnova/www/aria/skopos`, con la venv existente:

```bash
.venv/bin/python scripts/pdf_custody_pilot.py preflight
.venv/bin/python scripts/pdf_custody_pilot.py start
.venv/bin/python scripts/pdf_custody_pilot.py status
.venv/bin/python scripts/pdf_custody_pilot.py smoke \
  --capabilities-ref e94d1358d4d28a1c26f2dc91.envelope.json \
  --receipt-ref efaaabe0941e3b80892048f2.envelope.json \
  --fetch-ref bd6b79d385aee2d2cffc68aa.envelope.json
.venv/bin/python scripts/pdf_custody_pilot.py stop
```

Los tres sobres de la prueba están en el `requests_root` del consumidor y
pertenecen a expertoGobernanza. Si ese proyecto los retira, el consumidor
debe proporcionar sobres nuevos para `describe_capabilities`, `receipt` y
`fetch_original` bajo el mismo contrato; el script no los fabrica ni cambia
la política. `smoke` comprueba respuesta, digest anunciado de política,
recibo, identidad de revisión, SHA-256 e igualdad byte a byte con el original;
elimina sólo la salida cuyo `output_ref` indicó el sobre probado. Confirma
que las colecciones siguen en una revisión y una cabeza. No llama
`admit_original`.

`preflight` falla si cambian política/digest, configuración del host, raíz,
fecha, identidad del material, hashes del PDF/ficha, acceso o permisos de
archivos privados. `start` sólo inicia Mongo en `127.0.0.1:37034` con el
`dbpath` dedicado y el host con el `host.json` fijo. El controlador mantiene
los identificadores de ambos procesos; `stop` sólo les envía parada a esos
procesos y espera que desaparezcan los sockets propios. Si hay un socket
preexistente o un puerto ocupado, falla en vez de sustituir otro proceso.
Mongo conserva la base tras la parada. Los logs quedan bajo el directorio
privado del piloto. El controlador no es un supervisor: un fallo posterior
detiene el ciclo y requiere arranque manual. `status` y `smoke` exigen
procesos vivos; con el host apagado deben fallar. `status` comprueba conexión
al socket sin enviar un sobre u operación.

## Ejecución observada

En el primer ciclo, `start` devolvió `ready` en **0.972 s** y el digest
canónico `a92b9252cc27a5a0a421fa1422b583d61cafdb0026956794a302c09db3c52160`.
`status` devolvió `ready`. `smoke` recuperó el recibo
`expertogobernanza:imss-2000-002-001:1:4fbed2bd3d2633aa`, cotejó
1,311,822 bytes con SHA-256
`719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`,
retiró la salida temporal y observó una revisión/una cabeza.
La primera llamada a `stop` devolvió `stopping`. Tras añadir espera de
parada, cleanup acotado y sonda sin solicitud, tres ciclos más devolvieron
`stopped`: arranques de **0.939 s**, **1.041 s** y **0.957 s**,
`status=ready`, mismo recibo, bytes idénticos, una revisión/una cabeza y
salida retirada. Después del
último ciclo se verificaron ambos sockets ausentes, directorio de salidas
vacío y Mongo sin respuesta. La comprobación no cambió el PDF, la ficha ni
la política; el original y sus límites constan en
[el acta bilateral](pdf-custody-imss-pilot-2026-10-08.md).

La suite general corrió en un Mongo temporal exclusivo `127.0.0.1:37029`:
**497 pruebas OK, sin omisiones**, y ese proceso se detuvo. El primer intento
de suite directa en sandbox falló por bloqueo de sockets locales y ausencia
de su Mongo de prueba; no se contó como validación. El gate de Skevi pasó con
354 archivos y dos planes tras declarar una exención puntual para el log
creciente de Mongo del piloto en `skevi-gate.json`.

**Límite de disponibilidad:** después de `stop` no se puede consultar el
recibo ni recuperar bytes hasta otro `start`. El tiempo observado de
arranque no es un SLA. Los archivos de política y base son locales; la
recuperación depende de que expertoGobernanza conserve el PDF y la ficha
exactos. Una operación después del vencimiento necesita otra decisión de
política y prueba bilateral; no se extiende con una edición del JSON.
