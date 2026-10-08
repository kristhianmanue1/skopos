# Piloto de consulta desde agente — T0, preflight provisional

Estado: HISTÓRICO de T0 provisional; supersedido por la ejecución documentada en
`docs/evidencia/piloto-consulta-agente-t3-2026-10-07.md`. Observación inicial:
2026-10-07 18:59 UTC.
Actualización de decisión del Operador: 2026-10-07 19:11 UTC.
Comprobación de configuración OpenCode: 2026-10-07, posterior a esa decisión.
Plan: `docs/planes/activos/piloto-consulta-agente-2026-10-07.md`, v0.2,
SHA-256 `896242b45d2b71a68915a3c96a142a0b34e24c766df31ed61a1ad47e1dec164e`.
La autorrevisión documental está en `docs/rondas/2026-10-07-piloto-consulta-agente.md`;
su PROCEED documental no acredita el piloto.

## CONTEXTO DE AUTORIZACIÓN

- Sistema analizado: Skopos `main@fe1e8cbf6fe521c3e45fb87e76acf38c5f476084`;
  superficie `source` v3. Cliente principal provisional: OpenCode `1.18.35`.
- Autoridad y alcance: el Operador pidió el 2026-10-07 analizar, tomar contexto,
  guardar estado en AN-KLA e iniciar el plan. Posteriormente fijó GLM mediante
  z.ai Coding Plan, declaró la llave custodiada en `/Users/krisnova/www/aria/llavero`
  y decidió no imponer tope de uso. Esta declaración no prueba acceso efectivo,
  modelo exacto ni condiciones del plan contratado.
- Objetivo: preparar una comparación acotada A/B/C y comprobar que la llamada
  principal recibe el contexto antes de la serie de 108 ejecuciones.
- Entorno: checkout local; laboratorio exclusivo aún no creado ni comprobado.
  La instancia privada operativa y Mongo legado quedan fuera del piloto.
- Acciones permitidas en este pase: lecturas, este manifiesto y escritura
  gobernada en AN-KLA. La ejecución con modelo, ingesta y ensayos con estado
  quedan supeditados a configuración completa y controles del plan.
- Acciones excluidas: fuentes privadas, credenciales, terceros, exposición de
  red, cambio productivo, hooks globales y ampliación de permisos del agente.
- Condición de parada: no iniciar T1 con un destino de ingesta ambiguo; no
  iniciar llamadas al modelo sin cliente, identificador exacto y perfil de
  acceso comprobados; no iniciar T4 sin observación positiva de incorporación
  y control de bloque omitido.
- Resultado solicitado: estado recuperable de T0, faltantes precisos y siguiente
  operación comprobable.

## Identidad y fuentes consultadas

Git: rama `main`, HEAD arriba. El árbol ya contenía `project-manifest.yaml`
modificado y cinco documentos sin seguimiento: dos evidencias H25, una propuesta
de cierre H25, el plan y su acta. No se atribuyen a este pase. Remoto no
consultado; el HEAD local no prueba sincronización ni despliegue.

Se leyeron `AGENTS.md`, guía rápida, hoja de ruta, CLI, contrato source-store-v3,
ADR-018, plan y acta; se inspeccionaron las fronteras `source_cli.py` y
`runtime_views.py`. Hashes SHA-256 de fuentes relevantes:

| Fuente | SHA-256 |
|---|---|
| `docs/cli.md` | `826c4da72649299fe510ff2f95d3b84940c35b2a40b6b0362f8e3ea5e9f1ca19` |
| `docs/contratos/source-store-v3.md` | `e9ce851ce87734dc968a4e24345b00b13b91023cfeb25da754ee607d065a7e6d` |
| `src/skopos/source_cli.py` | `fe083cf00c4d49e473b26d00fb8613d651bb089df01de8beb2c27c082018efd9` |
| `src/skopos/runtime_views.py` | `9973adbcec8845620d81b3c57710cdff8f30d60de0c3141c6cfd864126b356cf` |
| `src/skopos/runtime_store.py` | `fd0482d993ca9e3f942a3a7adfe978471e544e8aa3c689435cbdf9f83cff7c29` |
| `src/skopos/runtime_reader.py` | `f26637957f0245c1731b3fe32173854ff9bc81f03a4bfb068e0c65ff9557c8f8` |

AN-KLA local `0.1.0b22`: `status` y `verify` OK en revisión 19,
`sha256:33ef48172aae84e4007b5ccc47fcbde7099d4f582b50c4fadca36cd7bf91cfd4`.
La recuperación de 8000 bytes excluyó cinco registros por presupuesto; repetida
con 16000 bytes recuperó los registros H25.2 pertinentes sin exclusión por
presupuesto. Es contexto histórico, contrastable con código y documentos.

## Configuración provisional

| Elemento | Estado T0 |
|---|---|
| Cliente principal provisional | OpenCode `1.18.35`; `opencode run --format json` declara eventos JSON. El Operador confirmó que ya está configurado con GLM. No se ha comprobado que exponga la petición efectiva al modelo ni permita el aislamiento requerido. Codex CLI `0.146.0` con GPT queda como serie opcional separada, no mezclada en A/B/C. |
| Modelo solicitado / efectivo | `~/.config/opencode/opencode.json` declara como predeterminado `zai-coding-plan/glm-5.3-flash`; el catálogo local también lista ese identificador. Es configuración observada, no telemetría de una ejecución. Modelo efectivo `unknown`. |
| Proveedor y coste | Decisión del Operador: z.ai Coding Plan, sin tope de uso. La llave se declara en el proyecto Llavero; no se leyó ni copió. `opencode providers list` reconoce Z.AI Coding Plan, pero no prueba autenticación funcional ni modalidad de facturación. Cero llamadas de inferencia de este pase. El plan v0.2 aún exige un tope monetario antes de llamadas de pago; esa cláusula necesita reconciliación documental con la decisión posterior. |
| Laboratorio | No existe destino exclusivo comprobado para este piloto. Preparar Mongo temporal nuevo, corpus sintético, procesos y directorio separados; no reutilizar la instancia operativa. |
| Condiciones y corpus | A/B/C, 12 familias × 3 variantes y hasta 24 fuentes/2 MiB por variante, según plan v0.2. Son parámetros propuestos, sin fixtures construidos. |
| Presupuestos técnicos | 3 search, 3 fetch, 5 resultados, 16 KiB acumulados, 10 s por consulta, 120 s por ejecución, 8 inferencias, stdout 1 MiB y stderr 64 KiB; arnés aún no implementado. |
| Rúbrica y observabilidad | Criterios en el plan; sin esquema, oráculo ni traza de llamada principal implementados. `--json` por sí solo no acredita incorporación. |
| Congelamiento | Pendiente hasta cerrar T3; toda configuración aquí es provisional. |

## Siguiente acción de T0

Comprobar el acceso funcional de OpenCode con
`zai-coding-plan/glm-5.3-flash` en un perfil aislado, sin exponer la llave.
Demostrar que permite
conservar la petición efectiva de la llamada principal y probar bloque
entregado/omitido. Reconciliar el requisito monetario del plan v0.2 con la
decisión posterior de no tener tope, conservando límites técnicos y registro de
consumo observado. Crear y verificar un Mongo temporal exclusivo antes de T1.
No se han iniciado T1–T5 ni las 108 ejecuciones.
