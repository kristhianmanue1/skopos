# ADR-021 — JSON ASR con evidencia original y texto derivado

Estado: implementación y piloto local autorizados por «adelante» del Operador
tras ofrecer adaptar la ingesta JSON. No aceptación productiva ni merge.
AMENDS: ADR-020/SPEC-007 sólo para formato optativo whisperx-json.
TXT/v0, corpus v2 y custodia externa permanecen intactos. No es el origen
runtime de H25: es otra representación de transcripción ASR.

## Instancia y decisión

JSON indicado por el Operador: 4710469 bytes, 1186 segmentos y 15011 palabras.
Tres segmentos y 59 palabras carecen de speaker; no imputar identidades.
No presumir igualdad con TXT: 251 textos difieren literalmente por posición.
El nombre del archivo no acredita versión de WhisperX, modelo ni fecha real.

Import exige source_format='whisperx-json' / --format whisperx-json; default
diarized-text. Sin autodetección ni conversión a TXT. source-envelope/v1 sólo
en JSON; source-record/v3 acepta v0 y v1 explícitamente, sin migración.
Un consumidor viejo rechaza v1: actualizar lector antes de admitir JSON.

Perfil observado: objeto con segments no vacío, hasta 10000 elementos. Cada
segmento requiere start/end numéricos finitos no negativos, end>start, text
no vacío y words lista. Speaker ausente/null se deriva como null. Etiquetas
presentes: string no vacío. Words requiere word no vacío; start/end ambos
ausentes o ambos numéricos no negativos con end>=start; score opcional finito
entre 0 y 1. No inferir alineación ni identidad desde tiempos/confianza.
word_segments opcional: si existe debe coincidir con concatenar words, sin
corregir discordancias. Máximo 200000 palabras anidadas y 64 niveles JSON.
Límite de entrada 16 MiB, BSON y salida siguen acotados por contrato T4.
Campos extra preservados en bytes originales, no indexados ni ejecutados.
UTF-8 estricto sin BOM, sin claves repetidas, NaN/Infinity, números no finitos
ni sustitutos Unicode aislados. Rechazo completo, nunca ingesta parcial.
Enteros de cualquier campo limitados a rango signed int64; floats finitos.
No se promete soporte universal de todos los exports WhisperX ni orden temporal
monótono: se conserva orden de la lista sin inferir causalidad/alineación.

## Evidencia y salida

Cada segmento v1 conserva ID ordinal, texto derivado, tiempos en segundos,
speaker nullable y word_count. Locator json-value: JSON Pointer /segments/N,
start_byte/end_byte del objeto JSON original y sha256 de ese slice. No son
offsets del texto decodificado. derived_text_sha256 sella sólo texto UTF-8.
source_sha256 sella archivo entero. Ordinal no acredita identidad entre revisiones.

Fetch/search v1: status json_bytes_verified, segment y original_json (string
que al recodificar UTF-8 reproduce el slice exacto, incluidos escapes/espacios).
Antes de servir verifica fuente, slice y texto derivado. Mantiene declaración
dato/no instrucción y audio_alignment/speaker_identity not_verified. Resultado
JSON completo <=64KiB; exceso excluido contado en search, error en fetch.
No se sirve original_json sin límites ni como texto conversacional equivalente.

Replay, CAS, recibos, vigencia y referencias externas mantienen T4. Importación
debe usar identidad nueva para este JSON: no reparar hashes de otras fuentes.
Pruebas: escapes/CRLF/Unicode, duplicados/NaN/profundidad, campos ausentes,
límites, reordenación de claves, fuente alterada, replay/revisión y regresión TXT.
JSONTestSuite sirve para sintaxis, no para calidad ASR; duplicados y_ de esa
suite se rechazan deliberadamente en el contrato de ingesta.

## Evidencia local del incremento

Piloto 2026-10-06T03:39:59Z, instancia temporal exclusiva 37027, base
skopos_test_json_pilot, identidad json-asr-pilot/meeting-json-new/revisión 1.
Fuente de 4710469 bytes, SHA-256
3496e8784cafa764bcf339d90a806c47ef0b8fa6f534d0deba608c81b43aad12,
idéntico antes/después. Se verificaron 1186 slices de objeto frente a su valor
JSON; import imported, replay duplicate; tres fetch coinciden con objetos
originales completos (posiciones 0,100,1185). Tres búsquedas literales con
términos fijados desde esas posiciones antes de importar: esperados 63/85/54,
servidos 20/20/20, excluidos por límite 43/65/34. Cero fuentes indisponibles o
fragmentos excesivos en esas consultas. No es evaluación de relevancia ni ASR.
No se imprimió contenido privado en evidencia versionada; no hay envío remoto.
Retención del piloto temporal hasta revisión del Operador; lectores: Operador
y proceso local autorizado, no ACL implementada. Sin copia privada en Git.

Diez fixtures públicos de JSONTestSuite (MIT), revisión
1ef36fa01286573e846ac449e8683f8833c5b26a, directorio local gitignorado
runs/public-fixtures.j9bxbd/JSONTestSuite. Sonda load_json: cuatro y_ aceptados,
un y_ duplicado rechazado deliberadamente; tres n_ rechazados (incluido NaN);
dos i_ rechazados (BOM/sustituto aislado), política permitida por esa suite.
No se ejecutó código externo ni se instalaron dependencias. Fuente:
https://github.com/nst/JSONTestSuite/tree/1ef36fa01286573e846ac449e8683f8833c5b26a

Autorrevisión adversarial de la misma instancia, no revisión independiente:
corregida equivalencia Python true==1 al cotejar listas de palabras; añadida
prueba de regresión. Errores numéricos se normalizan sin texto privado.
TXT/v0 probado por suite existente; JSON requiere formato explícito probado
en CLI. Primera sonda directa omitió integración y no se contó como evidencia
de integración. Suite temporal posterior: 376 OK en 74.127 s, antes de añadir
el test CLI; ejecución final con ese test se registra abajo al cierre.
No se rehicieron pruebas SIGKILL para este incremento; se reutiliza mecanismo
transaccional T4 sin cambios. No acredita privacidad multiusuario, exactitud
de diarización, totalidad de captura ni el segundo origen runtime de H25.

Suite final: 377 tests OK sin skips, 78.528 s, mediante
scripts/run_isolated_tests.py en Mongo temporal y Ollama local. Código sin
cambios posteriores; sólo cierre documental. Log:
/private/tmp/skopos-json.cxzP5k/final-tests.log. Gates: 216 archivos dentro de
límites, un plan válido, git diff --check limpio. Base temporal se conserva
en /private/tmp/skopos-json.cxzP5k/db, no en producción ni Git.
