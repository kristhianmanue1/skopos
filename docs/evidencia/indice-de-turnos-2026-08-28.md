# Evidencia · índice de turnos lleno (P-004) con identidad corregida

**Fecha:** 2026-08-28. **Alcance:** implementación de P-004 (aceptada 🔒
2026-08-28) más la corrección de identidad de parser-codex que el piloto
obligó a hacer antes.

## 1 · Identidad calificada de Codex (corrección previa)

`turn_id` pasa de crudo a **`codex-cli:{session_id}:{turn_id}`**.
Verificado sobre el corpus real:

| Antes | Después |
|---|---|
| 16,301 turnos → **10,441 ids** | 16,301 turnos → **16,301 ids** |
| **5,860 turnos (35 %) descartados** por la dedup | **0 colisiones** |

`ADR-010 §7` y la ficha del `§8` quedan actualizados: la excepción de id
crudo se **revoca por contraejemplo**, que es exactamente lo que el
propio §7 dejaba previsto. Hoy **ningún adaptador usa id crudo**.

Los 8 documentos guardados antes del cambio conservan su id viejo: son
**legado y no se mutan** — ADR-007 es insert-only, y reescribir una
clave de identidad sería precisamente la mutación que ese ADR prohíbe.

## 2 · El índice, lleno

| CLI | Turnos |
|---|---|
| codex-cli | 16,301 |
| claude-code | 1,818 |
| kimi-code | 1,637 |
| cline | 70 |
| **Total** | **19,826** |

- **Tiempo de ingesta completa: 47.6 s** (1,737 archivos). Sin llamar al
  modelo ni una vez.
- **Tamaño en Mongo**: 174 MB de datos, **74 MB almacenados** (WiredTiger
  comprime), 171 MB de índices.
- Reingesta idempotente: la segunda pasada sobre claude-code y cline
  reportó `ya_estaba` en vez de duplicar.

Para dimensionarlo: analizar esos mismos turnos con Ollama serían
**500-690 horas**. Indexarlos costó **48 segundos**. Esa es la apuesta de
P-004 y queda confirmada.

## 3 · Búsqueda sobre el corpus completo

| Consulta | Resultados | Latencia |
|---|---|---|
| `adaptador parser` | 5 | 6 ms |
| `mongodb indice` | 5 | <1 ms |
| `escrubery` | 5 | <1 ms |
| `lectura incremental cursor` | 5 | <1 ms |
| filtro `proyecto = skopos` | 40 | 1 ms |

Y devuelve resultados **cruzados entre CLIs y proyectos** — una búsqueda
trae turnos de codex-cli en `epistates` junto a turnos de claude-code en
`memoria-agentica`. Eso es lo que el eje de C-9 prometía y hasta hoy no
se podía comprobar con datos.

## 4 · Riesgo de eco, medido

De los 19,826 turnos indexados, **252 (1.3 %) mencionan "skopos" en
crudo**, y 40 pertenecen al proyecto. El detector de eco de C-5 midió en
su día 0 hits sobre 6 turnos, y ese 0 no era informativo. Ahora hay
población real sobre la que el control positivo sí dice algo.

## 5 · Lo que queda declarado como pendiente

1. **Ninguna superficie sirve todavía el texto crudo.** `skopos query`
   sigue leyendo `skopos.analisis`. El día que exista un comando que
   devuelva `texto_usuario`/`texto_agente`, debe llevar **P3**
   (dato-nunca-instrucción en su contrato) y **P5** (presupuesto de
   salida), según la decisión 3 de P-004. Hasta entonces **no hay canal
   de eco nuevo**: el índice se llena, pero no se sirve.
2. **`watch` no indexa todavía.** La decisión 🔒 fue: histórico por
   comando, y lo nuevo en `watch` *después* de medir. Lo medido está
   arriba; activarlo es el paso siguiente.
3. **Control positivo del detector de eco** contra la colección nueva,
   antes de activar nada por defecto.

## Verificación

**205 tests OK.** Los tests que asumían identidad cruda de Codex se
actualizaron a la calificada — ninguna aserción se debilitó: se ajustó
lo que el parser produce ahora.
