# Revisión de fidelidad RS1 CTIM — 13 de octubre de 2026

Estado: cotejo visual no ciego ejecutado sobre los derivados de la
[renovación RS1](ctim-rs1-retention-renewal-2026-10-10.md). Anotación
estructural: `rs1-fidelity-review-2026-10-13.json` (mismo directorio). Los
manifiestos de derivación **no se mutan**: conservan
`fidelity_status=unreviewed`; esta revisión vive como anotación externa,
igual que el precedente de etiquetas IMSS v0.5. No admite material a
custodia persistente ni al corpus; esa decisión sigue siendo del Operador.

## Integridad previa (precondición del cotejo)

- Original `/Users/krisnova/Downloads/2900-003-001_RS1.pdf`: SHA-256
  `1f8ad5e506b21cbf6b568b68790d2a757ba870524a6ba341f2dff3637d2494f2` —
  idéntico al registrado por la renovación.
- Manifiesto nativo `a302f49f…`: SHA-256 `7e0b4ba0…` verificado contra sus
  bytes; manifiesto OCR `834ccd87…`: `bf564fb4…` verificado.
- Los cuatro renders OCR (p22–p25) coinciden con los `sha256` de artefactos
  del manifiesto.

## Alcance y método

- **OCR (cobertura completa)**: las 228 líneas OCR de las páginas 22–25,
  cotejadas línea a línea contra los renders del propio manifiesto
  (revisión visual no ciega).
- **Nativo (muestra dirigida)**: páginas 18 y 21 —las citadas por las
  consultas previas (Ágora p21, evaluación p18)— cotejadas contra renders
  frescos del original con SHA verificado. Herramienta: PDFKit vía
  `swift` a 2,400 px, porque `pdftoppm` ya no está en PATH en esta fecha;
  renders de revisión: `00a84754…` (p18) y `73e7b449…` (p21).
- **Cotejo cruzado**: `native_text` de p18 y p21 idéntico línea a línea
  entre el manifiesto nativo y el manifiesto OCR (60 y 17 líneas).

## Veredicto

| Página | Modalidad | Resultado |
|---|---|---|
| 18 | nativo | Fiel; 0 discrepancias (incluye globos de comentario) |
| 21 | nativo | Fiel; 0 discrepancias |
| 22 | OCR | Sustancialmente fiel; 4 líneas defectuosas + omisión de numeradores |
| 23 | OCR | Sustancialmente fiel; 4 líneas defectuosas + conectores A/B ausentes |
| 24 | OCR | Fiel; 1 artefacto ("-" por flecha) + conectores B/C ausentes |
| 25 | OCR | Fiel en todo el texto capturado; conector C ausente |

Defectos OCR confirmados (detalle y bbox en la anotación JSON):
"ase a anass tecnico" → "base a análisis técnico"; "Etapa 1"/"Etapa ||"
→ "Etapa I"/"Etapa II"; "revision" → "revisión"; "reene de" → "reenvío
de"; "rovectos de obra avalado" → "proyectos de obra avalados";
"LINF"/"CEPi" → "LNIF"/"CEPI" en el paso 10; y el bloque de pie de p22
"salvaquardando… iqualdad… honradez. lealtad" → "salvaguardando…
igualdad… honradez, lealtad". El texto nativo preserva sin alterarlas las
peculiaridades del propio documento ("correciones", "unicamente",
"plataforma de para", "DEPI médica").

## Hallazgos transversales

1. **La confianza no filtra todo**: la mayoría de defectos coincide con
   confianza 0.30–0.50, pero los del pie de p22 traen confianza **1.00**.
   Citar texto OCR verbatim sin render de apoyo sigue sin estar admitido.
2. **Marcadores gráficos**: los conectores pentagonales (A, B, C) y casi
   todos los numeradores circulares de pasos quedan fuera del OCR; las
   citas que dependan del número de paso deben apoyarse en renders.
3. **Texto nativo apto para cita** en las páginas muestreadas:
   transcripción exacta, incluidos comentarios de revisión del borrador.

## Límites

Revisión acotada: 100 % de la cobertura OCR (22–25) y muestra nativa de
dos páginas; las otras 62 páginas nativas no se revisaron visualmente.
Prueba integridad, cobertura estructural y acceso local; no fidelidad de
las páginas no muestreadas, no continuidad si desaparece el archivo
externo, no oficialidad ni vigencia jurídica. La verificación de descarga
remota del referente sigue pendiente, y la retención vence el
2026-10-19T16:00:00Z con `block_then_explicit_retirement`.
