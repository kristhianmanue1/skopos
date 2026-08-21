# Ronda 7 — adversarial sobre la evidencia del ensayo escrubery (2026-08-20)

**Objeto:** `docs/evidencia/ensayo-escrubery-2026-08-20.md` — acta del
ensayo del canal escrubery (Fase 6 / Hito 10, REQ-10, ADR-004).
**Método:** revisor con contexto fresco re-ejecutó todas las
mediciones contra el clon real (load 9.3–12.1, mayor que el del acta) y
verificó aritmética y coherencia contractual.
**Veredicto:** **APROBADO** — sin correcciones exigidas.

## Constancia

- Números reproducidos: tamaños byte-exactos (10,922 B la ficha, 77 B
  el error `sin_datos`, los 9 CLIs del `listar`); latencias del mismo
  orden (media caliente 0.56 s bajo carga ~1.5× la original —
  consistente con la advertencia de carga de la remedición C-10);
  proyección 0.2698 × 14,822 = 3,998.2 s exacta y correctamente
  etiquetada como aritmética.
- Camino adicional verificado por el revisor: script inexistente →
  `None` sin excepción (tercer camino de fallo del CONTRATO
  consulta-escrubery-cli v1) — incorporado al acta.
- La recomendación de memoización queda bien acotada como "no
  implementada aquí, como dispone el plan".
- Notas no bloqueantes para futuras actas: el claim "operador separado
  del implementador" no es verificable desde el repo (era cierto: el
  ensayo corrió en subagente paralelo); los tres caminos de fallo del
  contrato no siempre hará falta ejercitarlos todos — ADR-004 no lo
  exige.
