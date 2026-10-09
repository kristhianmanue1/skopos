# Candidatos de rótulo PDF y medición piloto — 2026-10-08

Estado: **proyección local experimental**, sin operación v0.2 por socket,
política de retención propia, admisión al corpus ni adjudicación jurídica.
El manifiesto v0.1, el original y la custodia v0.2 no se modificaron.

## Pregunta y unidad

En el organigrama de la página física 20, ¿qué rótulos de caja conserva cada
método y cuántos coinciden con una transcripción visual de esa página? La
unidad es una caja localizada en el render exacto. No se evalúan las 188
páginas del PDF ni todos los organigramas 18–22.

El módulo `src/skopos/pdf_label_evaluation.py` proyecta, para cada nodo v0.1,
dos candidatos separados: `native_text` y `selective_ocr`. Conserva texto,
`item_id` y caja de cada línea, método, estado `unreviewed|no_lines`, hash
del manifiesto padre, identidad del derivado, hash del original y política.
La proyección `skopos/pdf-label-candidates/v0.2-experimental` es calculada en
memoria: no elige un rótulo definitivo, no escribe un derivado persistente y
no cambia `fidelity_status=unreviewed`.

## Referencia y método congelado

Referencia: `pdf-imss-page20-visual-reference-2026-10-08.json`, con diez
cajas y nueve conexiones topológicas transcritas por el mismo productor desde
el PNG de página 20. El JSON fija SHA-256 del PDF y del PNG. Las cajas de
referencia se aproximaron a partir de las predicciones v0.1: **la geometría
no es independiente**. Los rótulos se contrastaron visualmente, pero no han
sido revisados por expertoGobernanza ni por un segundo anotador. El hash
canónico de esta referencia tras la última edición debe obtenerse del reporte
reproducido, no de una cifra histórica en esta nota.

Emparejamiento: uno a uno, IoU ≥ 0,50, seleccionando mayor IoU primero;
empates por índice. La normalización de rótulos usa `casefold`, NFKD, elimina
diacríticos y puntuación y colapsa espacios. Una caja sin texto cuenta como
error. `CER` es distancia de edición de caracteres / caracteres de verdad;
`WER`, distancia de edición de palabras / palabras de verdad. Ambos son tasas
de **error**, por lo que menor es mejor. Las aristas se comparan como pares
no dirigidos sólo después de emparejar nodos. Ninguna flecha visible permite
evaluar dirección jerárquica observada en esta página.

## Resultado local observado

| Señal p20 | Nativo | OCR |
| --- | ---: | ---: |
| Rótulo exacto normalizado | 7/10 = **70 %** | 1/10 = **10 %** |
| CER | 4/437 = 0,92 % de error | 269/437 = 61,56 % de error |
| WER | 8/64 = 12,50 % de error | 44/64 = 68,75 % de error |

En la misma referencia se emparejan 10/10 cajas y 9/9 conexiones. Esos
100 % **no son una medición válida de detección independiente** porque las
cajas de referencia nacieron de las predicciones. Dirección observada: 0;
no se calcula porcentaje de dirección con denominador cero. El rótulo nativo
es mejor en este caso, pero contiene cortes internos de palabras como
`M ÉDICAS`, `FORM ACIÓN` y `PERM ANENTE`; no se corrigen en el derivado.

La proyección preserva ejemplos adversos que v0.1 ocultaba: n3 tiene OCR
vacío frente a nativo `COORDINACIÓN DE EDUCACIÓN EN SALUD`; n4 tiene OCR
`COBRARON BE` frente a nativo `COORDINACIÓN DE INVESTIGACIÓN EN SALUD`.
Estos son candidatos y localizadores, no una certificación de contenido.

## Reproducción y controles

Con el manifiesto y render locales del piloto v0.1, ejecutar:

```bash
.venv/bin/python scripts/evaluate_pdf_labels.py \
  --manifest runs/pdf-document-imss-pilot-v1/derived/1ef12d5a480075214369e9d19dcb6949370119e212b84007ce1b1a5ef1b7b8cf/manifest.json \
  --reference docs/evidencia/pdf-imss-page20-visual-reference-2026-10-08.json \
  --render-root runs/pdf-document-imss-pilot-v1/derived/1ef12d5a480075214369e9d19dcb6949370119e212b84007ce1b1a5ef1b7b8cf/renders
```

`--show-candidates` añade los textos y `item_id` al stdout para revisión
local. El CLI lee bytes exactos del PNG y falla si su hash difiere de la
referencia; también falla si el manifiesto declara otro render o SHA del
original. Pruebas unitarias cubren la separación nativo/OCR, OCR equivocado,
render desacoplado y falso positivo geométrico. El algoritmo, por ser
proyección pura, no escribe en la raíz de custodia.

## Límite y siguiente gate

Antes de llamar a esto fidelidad de organigramas 18–22, se necesita una
referencia visual congelada de **todas** esas páginas, con cajas y aristas
anotadas sin usar las predicciones, revisión del consumidor o segundo
anotador, y evaluación de cobertura/exclusiones por página. Después habrá
que acordar con expertoGobernanza la versión de contrato y una política
preconfigurada de persistencia/retención de este nuevo derivado antes de
servirlo por socket. La política v0.1 no concede esa autoridad por sí sola.
