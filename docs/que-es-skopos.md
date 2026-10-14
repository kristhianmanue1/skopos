# Qué es Skopos y cómo trabaja — contexto para quien revisa

Escrito el 2026-10-13 para dar contexto a revisores y consumidores potenciales
(proyectos ARIA, expertoGobernanza). Cada afirmación de este documento es
verifiable en el código, los contratos o la evidencia citada; nada aquí es
marketing. Punto de entrada alternativo: [guía rápida](guia-rapida.md).

## Qué es, en una frase

Skopos es la **capa de observación** del ecosistema ARIA: captura las
conversaciones que el Operador sostiene con sus CLIs de IA (Codex, Claude
Code, Cline, Kimi Code, OpenCode), las indexa con integridad verificable y
permite consultarlas — por tema, con análisis, o por texto literal — sin que
nada de eso reescriba el origen.

El principio rector: **el origen es de sólo-lectura y siempre citable por
bytes**. Cada turno guardado conserva la ruta, los offsets y el sello SHA-256
de su fragmento original; quien consulta puede volver a los bytes exactos.

## Cómo trabaja (pipeline real)

1. **Observación**: `watch` vigila los directorios de sesiones de los cinco
   CLIs con cursor incremental (ADR-011/013: 3.7–4.9 s por ciclo, nunca
   relee lo ya visto) y deduplicación por Mongo (ADR-005).
2. **Frontera de parseo**: cada CLI tiene un adaptador con ficha declarada
   bajo el contrato `parser-contrato/v1` (ADR-010) — identidad por predicado,
   versiones de formato diagnosticadas (nunca se parsea a ciegas), un módulo
   por CLI en `src/skopos/`.
3. **Índice sin modelo**: `index` guarda turnos observados en
   `skopos.turnos` sin llamar a ningún LLM (P-004).
4. **Análisis bajo demanda**: `analyze` interpreta turnos ya indexados que no
   tienen análisis, con proveedor local por defecto (Ollama) o cualquiera
   compatible-OpenAI por entorno, con el remoto siempre por decreto
   (ADR-014/017).
5. **Consulta con evidencia**: `query` sirve análisis por tema y relee el
   fragmento origen para verificar longitud y sello cuando existe; `search`
   sirve texto indexado redactado y acotado, sin releer el origen (ADR-009).

En paralelo, una **segunda línea de fuentes con procedencia** (ADR-020/021):
`source` admite transcripciones TXT/WhisperX JSON y exports runtime DSH JSONL
con identidad, revisión y hashes explícitos, sin LLM; `custody`/
`document-host`/`ctim-source-access` añaden la ruta de laboratorio local para
originales PDF/HTML por referencia bajo política por material — hoy siete
fuentes CTIM, con manifiestos por derivación y `fidelity_status` honesto
hasta cotejo.

## Funciones actuales (verificables con `python3 -m skopos --help`)

| Comando | Qué hace | Governa |
|---|---|---|
| `watch` | Vigila y procesa turnos nuevos de los 5 CLIs | SPEC-005, ADR-008/011/013 |
| `index` | Indexa turnos observados sin llamar al modelo | P-004 |
| `analyze` | Analiza turnos indexados aún sin análisis | ADR-017 |
| `reanalyze` | Supersede explícito de un análisis (versionado) | SPEC-003 v2, ADR-007 |
| `query` | Búsqueda temática sobre lo ya analizado, con sello | SPEC-004 |
| `search` | Búsqueda literal en turnos indexados, texto acotado | ADR-009 |
| `source` | Fuentes v3 con revisión/hash explícitos, sin LLM | ADR-020/021 |
| `custody` / `document-host` / `ctim-source-access` | Custodia PDF/HTML local por referencia; inventario, búsqueda literal y fragmento CTIM | contratos v0.2/v0.3 locales |

Suite: 483 pruebas (integración con servicios excluida en omisiones
declaradas); gate estructural de Skevi (límites por archivo y planes E1-E5)
en cada verificación.

## Fronteras declaradas — lo que Skopos NO es, por decisión

- **No es multiusuario** y no pretende serlo hoy: perfil local monousuario,
  agentes autorizados bajo la cuenta del Operador (decisión 2026-10-06). El
  multiusuario futuro exige contrato de acceso separado — no activación
  implícita.
- **No adjudica verdad ni vigencia jurídica**: los textos con hash son
  evidencia con procedencia, no autoridad. Los análisis son interpretación
  acotada, siempre recomputables.
- **No migra automáticamente** el índice legado ni mezcla las dos líneas de
  datos (conversaciones ↔ fuentes con procedencia): colecciones y contratos
  separados.
- **Consume bajo contrato, no por integración difusa**: los consumidores son
  proyectos de ARIA (Ágora, AN-KLA) y terceros como expertoGobernanza
  (decisión del Operador, 2026-10-13); la operación actual de respaldo
  migró a launchd local esa fecha, con su primera corrida desatendida en
  observación.

## Sobre la crítica «Skopos no es multiproyecto»

Quien revise merece el contexto completo, en tres partes:

1. **Lo que es cierto**: la superficie contractual de cara al consumidor
   (contrato CTIM v0.2 y puente MCP) **no tiene hoy eje de proyecto** — el
   acceso se acota por identidad de fuente/material. Un consumidor ve lo que
   la política lista, sin frontera por proyecto. Ese hueco es real y está
   registrado.
2. **Lo que es error de categoría**: la capa de datos **sí es
   multiproyecto** y está demostrado — eje `project_id` desde el
   hito 13 (índices por proyecto+CLI), y el piloto de consulta de agentes
   corrió **tres proyectos en una instancia** (pilot-cedro/olmo/pino) con
   búsquedas acotadas y 104/108 éxitos por rúbrica. Lo que falta no es
   capacidad: es contrato. Y «multiproyecto» no es «multiusuario»: exigir
   aislamiento entre usuarios a un sistema monousuario por decisión es pedir
   otra cosa.
3. **El camino registrado**: el plan activo
   `docs/planes/activos/contrato-multiproyecto-2026-10-13.md` crea el
   contrato `source-consumer-access-v0.1` con lista exacta `allowed_projects`
   por consumidor y error tipado `project_not_allowed` (fail-closed), sobre
   la superficie del almacén de fuentes — sin tocar la pasarela CTIM, donde
   la lista exacta de fuentes ya es más fina que cualquier eje proyecto. La
   distinción entre ambas pilas está documentada en la ronda adversarial del
   plan.

## Qué leer según lo que revise

- **Arquitectura y decisiones**: `docs/adr/` (23 ADRs con alternativas
  descartadas), `docs/specs/f1-specs.md`, `docs/contratos/`.
- **Estado honesto de lo hecho y lo pendiente**: `docs/hoja-de-ruta.md`
  (hitos con commit de cierre) y `docs/evidencia/` (actas por sesión).
- **Operación CLI**: `docs/cli.md`; arranque en 5 minutos: `docs/guia-rapida.md`.
- **Consumo por contrato**: contratos vigentes en `docs/contratos/`
  (`ctim-source-access-v0.2-local.md`, `source-custody-v0.3-local.md`,
  `source-store-v3.md`) y puente MCP en `docs/propuestas/ctim-mcp-consumer-bridge-v0.2.md`.
