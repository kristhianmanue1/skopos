# Evidencia: primera corrida de `skopos analyze` sobre anclas curadas

Fecha: 2026-09-12. Decisión que la ordena: **ADR-017** y su enmienda
(d'). Corpus: anclas `commit-write-plan` de la ventana de 7 días
(ADR-017 (c) acotado por decisión del dueño el mismo día).

## Resultado

| Medida | Valor |
|---|---|
| Anclas de la ventana | **135** |
| Con análisis al cierre | **135 (100 %)** |
| Fallos al cierre | 0 |
| `skopos.analisis` antes de la sesión | 8 |
| `skopos.analisis` al cierre | **151** |
| Reparto por proveedor | `glm-5.3-flash` 133, `qwen3:8b` 18 |

`modelo_analisis` distingue por turno qué proveedor lo produjo (ADR-014),
así que el corpus mixto es separable para siempre.

## Lo que costó llegar, y por qué se registra

La corrida no salió a la primera. Las tres causas son distintas y las
tres dejaron arreglo:

**1. Contexto insuficiente (local).** `llama-server` sirve con `-c 4096`
y `--context-shift`. Las anclas tienen mediana de 17,164 caracteres
contra 4,794 del turno típico: sólo el **42 %** cabía, y el resto se
habría analizado con el principio del prompt descartado en silencio —
primero las instrucciones, después `<texto_usuario>`. Motivó la enmienda
(d') de ADR-017. **El piloto habría medido el recorte, no la idea.**

**2. Endpoint equivocado (remoto).** Se configuró
`https://api.z.ai/api/paas/v4` — la API estándar, de pago por uso contra
el saldo de la cuenta. El **GLM Coding Plan no la cubre**: cubre
`https://api.z.ai/api/coding/paas/v4`. Las primeras 94 anclas pasaron
consumiendo saldo suelto; al agotarse, el resto falló con
`429 / code 1113 "Insufficient balance"`.

Diagnosticarlo costó de más porque `_llamar_openai_compat` descarta el
cuerpo de la respuesta al fallar y conserva sólo el status de urllib:
"429 Too Many Requests" se leyó como límite de tasa durante dos rondas,
cuando el cuerpo decía exactamente qué pasaba. **Pendiente: propagar el
mensaje del proveedor en la excepción.**

Comprobación que lo cerró, con la misma llave:

```
/api/coding/paas/v4  → 200 OK
/api/paas/v4         → 429 / 1113
```

**3. Reintento ausente.** `analisis.py` ya distinguía
`ErrorInfraestructura` (reintentable) de `ErrorModelo` (no), y `analyze`
trataba las dos igual: 37 anclas se dieron por perdidas sin estarlo.
Corregido con espera creciente (5 s, 15 s, 45 s) y conteos separados.

## Lo que la idempotencia de ADR-017 (b) demostró en la práctica

Hicieron falta **cuatro pases**. Ninguno duplicó un análisis ni gastó
cuota en lo ya hecho: cada uno saltó lo existente con una consulta a
Mongo y sólo mandó al modelo lo que faltaba. El último pase reporta
`analizado: 39, ya_analizado: 96`.

La regla se escribió para proteger la autoridad del supersede (ADR-007);
resultó ser también lo que hizo barato equivocarse tres veces.

## Defecto que el piloto destapó en `query`

Con análisis de opencode en la colección por primera vez, `skopos query`
reventaba con `TypeError: unsupported operand type(s) for -: 'NoneType'
and 'NoneType'`: `_servir_fragmento` asumía offsets enteros, y un origen
de filas no tiene rango de bytes (ADR-012). **Un solo resultado de
opencode dejaba la consulta inservible para todos los demás.**

Corregido con el estado `origen_de_filas` —que declara la ausencia en
vez de fingirla o morir— y test de regresión. No es fallo de integridad:
es una relectura que ese camino no ofrece.

## Verificación

`skopos query` sirve resultados por primera vez desde que existe.
Consultas reales sobre el corpus interpretado devuelven trabajo de esta
misma sesión —"Syndesmos como contrato en lugar de proyecto",
"Implementación del módulo analyze y hallazgo de offsets inválidos"—
junto a material de skevi, ektel y otros proyectos.

276 tests en verde; gate de Skevi verde (128 archivos).

## Lo que este piloto NO establece

- **No mide si el contexto interpretado sirve.** Produce el material
  para que el dueño lo juzgue; el juicio es suyo y está pendiente.
- No dice nada sobre el corpus completo (25,909 turnos): sigue sin
  autorizar, y la recomendación de que antes exista redacción sobre el
  prompt sigue en pie.
- No repara los offsets históricos de P-007.
