# Protocolo de evaluación de extracción PDF — propuesta 2026-10-08

Estado: diseñado, no ejecutado como evaluación. No instala herramientas ni
habilita una ruta de ingestión semántica. La custodia del original se evalúa
por bytes y hash; esta evaluación trata derivados, localizadores y utilidad.

## Pregunta y unidad de comparación

Pregunta: ¿puede un agente recuperar texto y estructura visual del PDF con
localizadores suficientemente fieles para volver a la página original? La
unidad es **página + región**, no un texto completo sin procedencia. Cada
salida derivada debe conservar SHA del PDF, versión de herramienta,
configuración, página 1 basada, región o caja, método, hash del derivado y
advertencia de incertidumbre. Un resultado que no localiza su evidencia no
puede alimentar una cita verificable.

## Corpus de evaluación y controles

Usar primero PDFs sintéticos autorizados: texto nativo, página sólo imagen,
diagrama con cajas/flechas, tabla, página rotada, PDF cifrado y archivo
corrupto. Separar fixtures de desarrollo de un conjunto de evaluación fijado
antes de ajustar herramientas. Incluir una página nativa legible como control
positivo de extracción; una página imagen como control positivo de OCR sólo
cuando OCR esté autorizado e instalado. Una salida vacía sin control positivo
no demuestra que el PDF carezca de texto.

El PDF IMSS referido en la propuesta previa es un caso candidato de evaluación
posterior: 188 páginas según `pdfinfo` en la inspección fechada, texto
recuperable en 187 por el método ensayado, portada sin texto y organigramas
en páginas 18–22 que requieren examen visual. Esos datos son observaciones
locales previas, no un resultado de este protocolo ni admisión del archivo.
La procedencia remota y el cotejo reportados por expertoGobernanza quedan
atribuidos a ese consumidor; no se vuelven afirmaciones propias de Skopos.

## Rutas candidatas por tipo de página

| Ruta | Herramienta candidata | Qué se mide | Regla de fallo |
| --- | --- | --- | --- |
| Inventario y render | Poppler `pdfinfo`/`pdftoppm`, qpdf `--check` | Páginas, cifrado declarado, capacidad de render y error estructural | `--check` no prueba validez jurídica ni fidelidad visual |
| Texto nativo | `pdfplumber` o `pypdf` | Caracteres, orden, tablas, coordenadas y anclajes | Texto presente con lectura/orden incorrecto se marca parcial, no completo |
| OCR selectivo | Tesseract mediante OCRmyPDF o ejecución controlada por página | Páginas imagen o texto nativo insuficiente; exactitud y cajas | No aplicar OCR a todo el PDF sin evidencia de necesidad ni conservarlo como original |
| Diagramas | Render más anotación humana o extractor de layout a evaluar | Cajas, flechas, relaciones y localizador de región | Secuencia lineal de OCR no prueba relaciones entre nodos |

Estas son opciones de software libre investigadas, no dependencias adoptadas.
La versión exacta, licencia aplicable, disponibilidad local y configuración
deben registrarse en la corrida. Tesseract, OCRmyPDF y qpdf no estaban
instalados en el entorno inspeccionado; antes de instalar una dependencia
nueva hace falta autorización separada. Docling sólo entraría a una comparación
si su coste, modelos y descarga inicial están controlados. Ninguna herramienta
se convierte por esta lista en requisito arquitectónico.

## Métricas y umbrales antes de probar

Registrar por página: `render_ok`, `native_text_present`, longitud, cobertura
manual de bloques clave, orden de lectura, errores de tabla, páginas sin
texto, confianza OCR cuando exista, y localizadores que permiten reproducir
la región sobre el render. Para organigramas, evaluar manualmente pares
`origen → destino` y dirección de cada flecha; no inferir esas relaciones de
proximidad textual. Fijar umbrales de aceptación antes de comparar motores y
mostrar falsos positivos y falsos negativos, no sólo un porcentaje global.

Repetir extracción en el mismo PDF/hash y comparar derivados y localizadores.
Si cambian por versión o configuración, registrar ambas identidades y no
sobrescribir el derivado anterior. Contrastar una muestra de citas contra el
render y el original. El revisor semántico no debe usar la salida del productor
como único patrón de verdad.

## Criterio de salida

El informe debe separar: páginas aptas para texto nativo, páginas que requieren
OCR, regiones visuales no traducibles con fidelidad y páginas rechazadas.
Sólo un resultado con evidencia de reproducción de localizadores puede
proponer una ruta de consulta. Extraer texto no admite el documento al corpus,
no adjudica vigencia normativa y no habilita automáticamente citas jurídicas.
