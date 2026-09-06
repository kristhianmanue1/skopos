# ADR-014: análisis multi-proveedor — API compatible OpenAI, Ollama por defecto

Estado: **aceptado** — decisión 🔒 del dueño, 2026-09-06 ("adelante con tu
propuesta"). Enmienda parcial de ADR-001 y del manifest: la frontera
"modelo local, sin servicios externos" pasa a "proveedor local por
defecto; remoto sólo con decreto explícito". No revoca la validación
fail-closed del análisis ni la redacción de secretos (P3), que son de
skopos y no del proveedor.

## Contexto

El análisis (SPEC-002) habla una sola API: `_llamar_ollama` contra
`http://localhost:11434/api/generate`, con `format: json` (campo
específico de Ollama). El acoplamiento es innecesario: casi todo el
mercado de modelos — locales y remotos — expone hoy la misma superficie
`POST {base_url}/chat/completions` (compatible OpenAI): Ollama mismo
(`/v1`), llama-server, LM Studio, vLLM, LocalAI; OpenAI, Anthropic (capa
de compatibilidad), Groq, Mistral, DeepSeek, z.ai (`/api/paas/v4`), y
OpenRouter como puerta a 100+ modelos con una sola API.

Restricciones del proyecto que descartan atajos:

- **Cero dependencias especulativas**: LiteLLM (o cualquier SDK de
  proveedor) arrastra pydantic/httpx/openai por una sola llamada
  chat+JSON. Rechazado. skopos ya habla HTTP con `urllib` de la stdlib.
- **Seguridad de secretos**: la API key vive en variable de entorno,
  nunca en el repo ni en logs (regla dura §7).

## Decisión

### (a) Un solo adaptador: compatible-OpenAI

`_llamar_openai_compat(prompt, *, modelo, base_url, timeout, api_key)`:
`POST {base_url}/chat/completions`, `Authorization: Bearer` sólo si hay
key, y parseo tolerante de la respuesta (soporta contenido cercado con
\`\`\`json). Convención de URL: `base_url` es el prefijo ANTERIOR a
`/chat/completions` (p. ej. `http://localhost:11434/v1`,
`https://api.z.ai/api/paas/v4`).

### (b) El proveedor es configuración de entorno, no código

Variables leídas al invocar (sin dotenv, sin archivo nuevo):
`SKOPOS_LLM_API` (`ollama` | `openai`; defecto `ollama`),
`SKOPOS_LLM_BASE_URL`, `SKOPOS_LLM_MODELO`, `SKOPOS_LLM_API_KEY`.
Sin variables, el comportamiento es **byte-idéntico al actual**:
`_llamar_ollama` contra Ollama local con qwen3:8b. La inyección de
tests (`llamar_modelo=`) manda sobre todo lo anterior.

### (c) Frontera enmendada con dos niveles

- **Local** (Ollama, llama-server, LM Studio…): libre, es el default.
- **Remoto** (z.ai, OpenRouter, OpenAI…): permitido sólo por decreto
  del dueño, materializado en el entorno de quien ejecuta el watch. El
  contenido de los turnos sale de la máquina en ese caso — la primera
  vez que skopos cruza esa frontera. El manifest se enmienda en el
  mismo commit.

### (d) Lo que NO cambia

La validación del análisis (esquema tema/resumen/entidades, fail-closed),
la redacción de secretos, la metadata (`modelo_analisis` registra qué
modelo produjo cada análisis — ahora es dato interesante, no constante)
y el gancho de escrubery (ADR-004) son idénticos en todos los
proveedores. `format: json` de Ollama no tiene equivalente universal: el
prompt ya pide JSON y la validación de skopos respalda — el campo se
mantiene sólo en la rama Ollama.

## Alternativas descartadas

- **LiteLLM / SDKs por proveedor**: dependencias pesadas para una
  llamada; contra la política del proyecto.
- **Sistema de plugins `analisis-contrato/v1`** estilo parsers: para dos
  backends es sobreingeniería; el despacho por entorno cubre el caso sin
  contrato nuevo.
- **Multiplexor obligatorio** (OpenRouter/LM Studio como único camino):
  añade un servicio al camino crítico del análisis; aquí cada proveedor
  se elige por configuración, sin intermediario obligado.

## Consecuencias

- Cambiar de modelo = cambiar variables de entorno; sin tocar código.
- El análisis remoto (p. ej. z.ai GLM) abre la puerta a re-analizar el
  índice completo en horas y no años — la decisión de HACERLO sigue
  siendo del dueño (coste + privacidad).
- ADR-001 queda enmendado (el modelo ya no es necesariamente local);
  SPEC-002 sigue vigente en todo lo demás.

## Lo que este ADR NO decide

No decide usar un proveedor remoto concreto ni re-analizar el corpus
existente con él. No toca el índice P-004 ni el formato
`documento-analisis-mongo`.

## Firma de decisión

- Dueño: decisión 🔒 comunicada en sesión ("adelante con tu propuesta",
  tras confirmar que Ollama queda como default y que la API de z.ai
  Code Plan entra por la vía compatible-OpenAI) · Fecha: **2026-09-06**.
