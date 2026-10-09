# Ensayo local de rótulos IMSS v0.4 — 2026-10-08

**Ámbito:** Skopos en este Mac; PDF IMSS SHA-256
`719d6da341bff3733750f05357de50ca09fabc7c31c4354186dae8a7a3a70323`.
Contrato y procedimiento en
[`pdf-graph-labels-v0.4-experimental.md`](../contratos/pdf-graph-labels-v0.4-experimental.md).

## Evidencia de extracción y linaje

El manifiesto v0.3 de 86 nodos permaneció intacto. Poppler `pdftotext
-bbox-layout` 26.05.0 extrajo palabras con centro dentro de cada caja
(margen 3 pt) en 78/78 nodos de p19–22 y 0/8 de p18. Una unión de
fragmentos con distancia <0.9 pt reconstruyó 78 cadenas; p21 n5 produjo
`COORDINACIÓN DE INFORMACIÓN E INTELIGENCIA EN SALUID`, mientras la imagen
de 2200 px muestra `SALUD`. El registro v0.4 conserva ambas y atribuye
la corrección visual. Las ocho etiquetas de p18 se transcribieron de la
imagen porque el texto nativo no cubre esas cajas. La lectura visual de
expertoGobernanza para p18 se recibió como declaración del consumidor;
coincide con las ocho candidatas locales, pero no sustituye un recibo
bilateral v0.4.

Las [anotaciones](pdf-imss-graph-label-annotations-v0.4-experimental.json)
SHA-256 `95dcb8d3cb40f5f06ec865712d5129d6f55c42ab495461c31bce53e638a94c46`
fijan método, página, caja, render e ítem padre por etiqueta. El
[manifiesto](pdf-imss-graph-labels-v0.4-experimental.json) tiene derivación
`54ef4a35842a22896b1f881eb9a1c4c6076ac80e469d83dcbafa81f32e6c7e45`
y SHA-256 `07018142b74249edf0bc056f3b10bee5d1d004e43e77f556b3ef745027efaa98`.
Todos los 86 rótulos tienen `candidate_unadjudicated`.

## Prueba bajo demanda

Se inició el Mongo dedicado y el host local con la configuración privada
`graph-labels-host.json` (0600), digest canónico
`1b21129583a5de8aac2938b00e594df36654452afc6e3c348983387ddd03803b`.
El smoke de Skopos recuperó cinco páginas (8, 32, 10, 19 y 17 rótulos) y
por ítem p18 n3, p21 n5 y p22 n10. Verificó correlación, fuente, estado,
identidad, cinco rechazos tipados y replay idéntico. Tras la ejecución,
host y Mongo del piloto se apagaron y el socket desapareció.

Las dos nuevas pruebas del proyector pasaron. La suite general terminó
`Ran 447 tests ... OK (skipped=6)`; esas seis omisiones limitan su
cobertura. El host se probó por separado con Mongo del piloto en el smoke.
`check_sizes.py` pasó para 470 archivos y `check_plans.py` para dos planes;
el diff se revisó antes de publicar.

## Límite

El host valida la cadena de bytes e identidades, pero no vuelve a extraer
texto nativo ni inspecciona visualmente el PDF en cada solicitud. La
transcripción p18 y la corrección p21 n5 son autorrevisión del productor.
No se ha medido exactitud visual independiente de los 86 rótulos ni se ha
ejecutado cliente bilateral v0.4 de expertoGobernanza. No hubo vectores,
corpus, nueva política ni servicio continuo.
