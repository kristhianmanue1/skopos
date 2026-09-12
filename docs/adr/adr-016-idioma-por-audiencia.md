# ADR-016: idioma por audiencia (inglés en la frontera, español adentro)

Estado: **aceptado** — decisión 🔒 del dueño, 2026-09-12 ("ponlo como
aceptado"), tras el análisis de nomenclatura de la misma fecha.
Supersede la línea "Español" de la sección Convenciones de `AGENTS.md`
en lo que toca a identificadores; la conserva para la prosa.

**Precisión posterior:** ADR-018 sustituye la elección de español para
identificadores internos nuevos de §(b), y por tanto el alcance de la
alternativa «todo en inglés». El resto de este documento conserva su valor
histórico y sus reglas compatibles: alias y contratos legados no se migran.
Ver [ADR-018](adr-018-codigo-ingles-comunicacion-humana.md).

## Contexto

El dueño observó que el código y los comandos deberían estar en inglés.
El relevamiento del estado real mostró algo más preciso que "está en
español": **el proyecto ya es bilingüe y la costura pasa por dentro de
los identificadores**.

| Superficie | Inglés | Español |
|---|---|---|
| Comandos | `query`, `watch` | `reanalizar`, `indexar`, `buscar` |
| Campos de turno | `turn_id`, `session_id`, `cli` | `ruta_origen`, `origen_tipo`, `texto_usuario`, `texto_agente`, `indexado_en`, `ocurrido_en`, `proyecto` |
| Híbridos en una misma palabra | `offset_inicio`, `offset_fin`, `fragmento_sha256` | — |
| Ids de contrato | `cli-skopos-query` | `documento-turno-mongo`, `rollout-jsonl-de-codex` |

No había una regla que romper: nunca hubo regla. `AGENTS.md` declara
"Español" en Convenciones, pero se escribió pensando en la prosa (los
ADRs, las propuestas, los commits) y nadie la bajó nunca a los
identificadores. El resultado es una mezcla sin criterio, no una
decisión que se haya incumplido.

Lo que cambia el cálculo hoy es la **ampliación anunciada por el dueño
el 2026-09-12**: skopos dejará de observar sólo CLIs oficiales y
almacenará conversaciones de cualquier origen (prime, agentes en
runtimes y sandboxes). Con eso, los contratos publicados dejan de ser
nota personal y pasan a ser superficie de interoperación leída por
software y por gente que no conoce el proyecto.

## Decisión

El idioma se elige **por audiencia del identificador**, no por gusto ni
por uniformidad.

### (a) Inglés en la frontera

Lo que leen otros sistemas y terceros que no trabajan en este repo:

- nombres de **comandos** de la CLI y sus **flags**;
- nombres de **campos** de documento y de **esquemas** de contrato;
- **ids de contrato** publicados en `project-manifest.yaml`.

### (b) Español adentro

Lo que leen el dueño y los agentes que trabajan en este repo:

- nombres de **módulos**, **funciones**, **variables** y **comentarios**;
- `docs/` completo — ADRs, propuestas, especificaciones, contratos,
  evidencia, rondas;
- mensajes de commit.

El corpus de decisiones en español es el activo mejor conservado del
proyecto, y la regla de `AGENTS.md` existe para proteger **cómo se
piensa aquí**, no cómo se nombran las variables. Traducirlo no cambiaría
nada del comportamiento y costaría días.

### (c) Los campos existentes NO se migran todavía

`documento-turno-mongo v2` y `documento-analisis-mongo v2` conservan sus
nombres en español sobre los 25,909 documentos ya almacenados. El
renombrado se hace **dentro del `v3` que la ampliación va a exigir de
todos modos** — un esquema que acepte mensajes de runtimes sin archivo
ni offsets no cabe en v2.

Esta es la razón de decidir la regla hoy y no después: si el renombrado
se hiciera por separado, se pagarían dos migraciones sobre el mismo
corpus. Decidida ahora, **v3 nace en inglés y el renombrado viaja gratis
dentro de un supersede que ocurriría igual**.

### (d) Los comandos en español reciben alias en inglés

`reanalizar`→`reanalyze`, `indexar`→`index`, `buscar`→`search`. Ambos
nombres vivos; el español queda marcado como obsoleto en la ayuda y se
retira sólo con decisión explícita. Es un diccionario de despacho: el
alias no rompe a nadie ni invalida los contratos `cli-skopos-*` v1
publicados, que siguen describiendo la misma superficie.

Sin esta parte la decisión empeoraría el estado: quedarían `query`,
`watch`, `analyze` en inglés contra tres en español. **Una mezcla parcial
es peor que la mezcla actual, porque parece una regla y no lo es.**

### (e) Superficie nueva, en inglés desde el nacimiento

Todo comando, campo o contrato nuevo se nombra en inglés sin período de
gracia. Aplicación inmediata en P-006: `skopos analyze`,
`skopos/curated-anchor/v1`, `skopos/context-block/v1`,
`cli-skopos-analyze v1`.

## Alternativas descartadas

**Todo en inglés, incluidos módulos, funciones y `docs/`.** Coherencia
total, y defendible si se esperaran colaboradores externos leyendo el
código. Descartada por asimetría de costo: traduce 16 ADRs y 6
propuestas, renombra 17 módulos y toca los 253 tests, para que el
proyecto se comporte y se piense exactamente igual que hoy. Quienes leen
este repo son el dueño y agentes, y ambos leen español sin fricción. Si
se retomara, sería un hito de migración con su ronda propia, no una
convención — y así debe plantearse, nunca por goteo.

**Todo en español, migrando `turn_id` y `session_id`.** Coherente hacia
adentro y hostil hacia afuera justo cuando la ampliación abre la
frontera. Además rompe los contratos publicados sin ganancia.

**Dejarlo como está.** Es lo que produjo `offset_inicio` y
`fragmento_sha256`. Sin regla, cada identificador nuevo vuelve a
lanzar la moneda.

## Consecuencias

- `AGENTS.md` reemplaza "Español" por la regla partida, con puntero aquí.
- La ampliación (conversaciones de cualquier origen) queda con el idioma
  de su esquema ya resuelto antes de diseñarlo — que es el punto.
- Todo contrato nuevo publicado en el manifiesto lleva id en inglés,
  conviviendo con los 8 en español ya publicados, que no se renombran.
- Los ids de contrato viejos quedan como deuda declarada y visible: no
  se tocan porque renombrarlos rompería a sus consumidores sin ganancia.

## Lo que este ADR NO decide

- No decide el esquema `v3` ni la forma de la ampliación — sólo el
  idioma en que nacerá. El diseño es análisis aparte.
- No retira ningún comando en español: el alias convive, y el retiro
  exigiría decisión propia.
- No toca los 8 contratos ya publicados ni los campos almacenados.
- No cambia el idioma de la prosa: `docs/`, commits y ayuda de la CLI
  siguen en español.

## Firma de decisión

Dueño, 2026-09-12. Análisis de nomenclatura con relevamiento del estado
real (comandos, campos, ids de contrato) en la sesión de esa fecha;
recomendación del agente = opción "partir por audiencia", aceptada.
