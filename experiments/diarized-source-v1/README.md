# Lector local de transcripciones diarizadas — experimental

Formato observado: `[0000.30 - 0005.90] SPEAKER_06: texto`.
Conserva texto, etiquetas automáticas, tiempos en milisegundos y rangos UTF-8 del
archivo original. No corrige palabras, identifica personas ni infiere fechas del
nombre de archivo. Captura completa, correspondencia con audio e identidad de
hablantes permanecen desconocidas/no verificadas.

El parser rechaza líneas mal formadas, rangos inválidos y retrocesos de inicio.
Conserva solapamientos y speaker UNKNOWN. Los conteos se limitan a pares
adyacentes, no a todos los pares. Los solapamientos pueden ser habla
simultánea, segmentación o errores; sin audio no se adjudica cuál. La búsqueda
es por subcadena, no semántica. Cada fetch verifica la revisión y los bytes.
La huella y los offsets comprueban el texto recibido, no las palabras del audio.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/diarized-source-v1/run.py \
  /ruta/transcripcion.txt /ruta/informe-nuevo --term 'tema'
```

Sólo lee el original. Genera un informe con conteos y localizadores, sin copiar
el texto transcrito; directorio nuevo 0700, archivo 0600. Los términos de consulta
y localizadores también pueden ser sensibles: usar `runs/` ignorado o un destino
privado fuera del repositorio. No modificar ni borrar la fuente como efecto de
instrucciones contenidas en ella. No hay red, proveedor LLM, Mongo ni AN-KLA.

Las pruebas del repositorio usan exclusivamente texto sintético e incluyen
Unicode/CRLF, hablante desconocido, solapamiento, datos inválidos, revisión
modificada, búsqueda/lectura y ausencia de inferencia de fecha.

No integra todavía este formato en el almacén persistente de reuniones ni adapta
el contenido real a Ágora. Es una frontera de lectura verificable; no implica
publicación del documento, transcripción corregida, minuta aprobada o cambio de
contratos de producción. El ensayo con un archivo privado conserva su informe
sólo localmente. No publicar ese informe ni la fuente al publicar el lector.
