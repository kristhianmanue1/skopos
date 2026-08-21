# Evidencia · detector de eco C-5, piloto 1 (Fase 5)

Snapshot: **2026-08-20**, `main@428636b`, load 6.8–9.2 durante el
piloto (regla X-2). Corpus de la colección `skopos.analisis` al cerrar:
**6 documentos** — los del piloto (antes: 0).

## Diseño del piloto

- **Sesión única** (decisión 8/plan Fase 5): rollout del
  2026-08-20T18-18 (`01a021ae…`), 6 turnos, 220,319 chars de
  conversación real, `proyecto: cepiMedica` derivado por turno desde
  `turn_context` (C-9 operativo en datos reales).
- **Timeout 300 s** por el parámetro existente de `analizar_turno`
  (decisión 🔒 del dueño, 2026-08-20: **opción (a)+(b)** — subir el
  timeout del piloto vía parámetro y reportar fallos como dato con
  conteo explícito; **(c)** esperar carga baja, descartada: la evidencia
  debe ser reproducible, no afortunada. Registrada también en el plan,
  §Fase 3). Sin tocar código.
- Ingesta a la colección real (`skopos.analisis`), **después** del sello
  P4a (restricción de orden de Pinax honrada: 0 documentos antes del
  commit `21ce77a`).
- Script del piloto: log JSONL por turno (estado, duración, chars,
  error); API pública únicamente.

## Resultados de ingesta

| Métrica | Valor |
|---|---|
| Éxitos / fallos / omitidos | **6 / 0 / 0** |
| Duración por turno | 29.5 – 138.9 s; media 73.3 s, mediana 57.4 s |
| Timeouts | 0 a 300 s. Un turno (138.9 s) excede el wall-clock del default de 120 s — la subida quedó justificada; el comportamiento bajo 120 s no fue observado (contrafactual, no medición) |
| Documentos sellados (`fragmento_sha256`) | 6/6 |

Nota de escala (ronda 9, R7): el plan anticipó "~28 turnos"; el piloto
corrió **6** (sesión única cumplida; n=6 declarado para todos los
números). Tiempos: 4/6 por debajo de los 90 s de la horquilla alta de la
remedición C-10, 2/6 dentro o encima — con carga menor (6.8–9.2 vs
9.4+); la caracterización honesta es "dispersos, ninguno crítico".

## Detector corregido de C-5 (P-001 §4.5), acotado al piloto

- Regex sobre `resumen`: `"resumen"\s*:|"tema"\s*:|skopos query`
  (case-insensitive) — sobre los 6 documentos del piloto, y en forma
  equivalente `count_documents` con filtro por `session_id` (acotación
  H11 de la ronda 0: no mezclar corpus). P-001 §4.5 define el detector
  sobre `resumen` (sólo ese campo); una pasada exploratoria sobre
  `tema` también dio 0.
- **Resultado: 0 hits / 6 documentos** (por ambos métodos).
- **Control positivo** (ronda 9, en colección de prueba, no en la
  real): las tres firmas de eco (cadena `skopos query …`, JSON
  `{"tema":…, "resumen":…}`, y mayúsculas `skopos QUERY`) se detectan
  3/3; una mención inocua de "skopos" sin firma no da falso positivo.
  El detector es sensible; el 0/6 es señal, no un detector muerto
  (lección B-1 de P-001 §11 aplicada).

## Composición del corpus (declarada, sesgo auto-referencial)

**3/6 turnos mencionan "skopos" en su texto crudo** (sesión de
cepiMedica que hoy también discutió skopos). Los 3 restantes son
contenido limpio. Lectura honesta del 0/6:

- Incluso los turnos *sobre* skopos produjeron resúmenes sin la
  firma del eco (sin fragmentos JSON ni la cadena "skopos query" en
  `resumen`) — el analizador no copió ese vocabulario.
- **El 0/6 no falsifica la hipótesis del eco**: el lazo completo
  (salida de `skopos query` volcada al rollout de un consultante →
  reingesta por Skopos) requiere que alguien consuma la salida en una
  sesión observada y que Skopos la reingiera; con el vigilante
  "desde ahora" (ADR-008) y 6 documentos, el lazo aún no pudo cerrarse
  en la práctica. Lo que el piloto establece: **el detector funciona
  contra un corpus real poblado, sellado y acotable, y la línea base
  está limpia.**

## Verificación end-to-end con datos reales (primera del proyecto)

`skopos query "backend" --proyecto cepiMedica --max 3` → 3 resultados,
`excluidos.por_limite: 1`; estados de fragmento: 2 `integro` sellados,
1 `truncado` (52,290 chars de conversación; fragmento de 128,263 bytes
> tope 65,536 — servido con marcador `servidos 65536 de 128263 bytes`)
— P4a, P5, C-9 y la señal de exclusión (C-4) verificados sobre datos
reales por primera vez.

## Log del piloto (JSONL, embebido — ronda 9, R6)

```json
{"turn_id": "01a021ae-83ad-74e1-8d2c-0b2732acd13d", "proyecto": "cepiMedica", "estado": "guardado", "chars": 64021, "duracion_s": 29.5, "tema": "creación de rama de trabajo", "sellado": true}
{"turn_id": "01a021b8-d935-7393-8fe6-b8753eee0ae1", "proyecto": "cepiMedica", "estado": "guardado", "chars": 50578, "duracion_s": 138.9, "tema": "Permiso concedido para iniciar el servidor de desarrollo de Vite", "sellado": true}
{"turn_id": "01a021c4-c050-7e03-8646-c5d13b956348", "proyecto": "cepiMedica", "estado": "guardado", "chars": 47850, "duracion_s": 108.9, "tema": "Desbloqueo de la Ficha Técnica y flujo de generación del Nombre Oficial", "sellado": true}
{"turn_id": "01a021c5-05db-7612-8142-10a89b820696", "proyecto": "cepiMedica", "estado": "guardado", "chars": 3557, "duracion_s": 47.9, "tema": "Aprobación de acción", "sellado": true}
{"turn_id": "01a021de-b29d-7173-b74f-0baf2682b704", "proyecto": "cepiMedica", "estado": "guardado", "chars": 52290, "duracion_s": 61.1, "tema": "reinicio_backend", "sellado": true}
{"turn_id": "01a021de-e558-7402-9be5-5c6c63c2c4f0", "proyecto": "cepiMedica", "estado": "guardado", "chars": 2023, "duracion_s": 53.6, "tema": "Evaluación de acción de inicio de backend", "sellado": true}
{"fin": true, "exitos": 6, "fallos": 0, "omitidos": 0}
```

Duraciones corroboradas independientemente por `creado_en` de Mongo
(ronda 9): procesamiento serial, deltas dentro de ~0.3 s del log.

## Conclusión de Fase 5

La instrucción original (P-001 §4.5): "ejecutar esto antes de que nadie
vuelva a discutir C-5" — ejecutado. Estado de la hipótesis del eco:
**sin evidencia a esta escala, con detector operativo y línea base
declarada**. El monitoreo continuo corresponde al vigilante en uso
real; si la hipótesis reaparece, el detector corre en segundos contra
la colección (count_documents acotado).
