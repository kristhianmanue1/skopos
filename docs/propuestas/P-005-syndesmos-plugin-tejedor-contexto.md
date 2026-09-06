# P-005: syndesmos — plugin tejedor de contexto entre skopos y AN-KLA

Estado: **propuesta — no decidida. Insumo para rondas de consenso y
adversariales.** No implementa nada: pide decisiones (§7) y registra
evidencia ya medida (§1).
Fecha: 2026-09-06.
Origen: sesión del 2026-09-05/06 con el dueño. Dos hipótesis se
pusieron a prueba con medición — "AN-KLA basta para tomar contexto" y
"la memoria de skopos basta para tomar contexto" — y ambas cayeron por
razones complementarias. Esta propuesta es la consecuencia directa.
Autoría: agente opencode (GLM) con el dueño.

## 1. Evidencia de la sesión (todo medido, nada especulado)

| Medida | Valor | Fuente |
|---|---|---|
| AN-KLA entrega al arrancar | 1 registro vigente, 1,382 B de 2,500 presupuestados; 3 inactivos por supersedes | `an-kla retrieve` real |
| Memoria AN-KLA desactualizada | el hito 21 (ADR-015) se cerró DESPUÉS de escribir la ficha; se descubrió por `git log`, no por memoria | git + hoja de ruta |
| `skopos query` (capa de análisis) | **vacío** — 8 de 22,895 turnos interpretados | comando real |
| `skopos buscar` sin filtro | ruido de otros proyectos (alubia, adrc, cepiMedica) por boilerplate | comando real |
| `skopos buscar --proyecto skopos` | útil: recuperó las rondas de ADR-010 con redacción y acotado | comando real |
| Turnos con escritura real a AN-KLA | **448** (`commit-write-plan`); 478 con `plan-write`; sólo **4** con `an-kla retrieve` | regex sobre `skopos.turnos` |
| Total turnos indexados | 22,915 | Mongo |
| Costo de interpretación | ~19.6 s/turno con `qwen3:8b` → 448 turnos ≈ **2.4 h serial** | README + ADR-014 |
| Vigilante | vivo (PID 83256, intervalo 10 s); los turnos entran al índice **al cerrarse** — no ve el presente | ps + ADR-008/013 |

Lectura: AN-KLA sabe *qué importa* pero poco, y perece; skopos sabe
casi *todo lo que pasó* pero no sabe qué importa. Se escribe a AN-KLA
100× más de lo que se lee. El 2 % del corpus está anclado por
escrituras deliberadas — un conjunto curado gratis, sin costo de
etiquetado.

## 2. Qué propone

Un **tercer proyecto independiente** — plugin/extensión, nombre de
trabajo `syndesmos` (σύνδεσμος, vínculo) — que **lee** de skopos y de
AN-KLA, **escribe sólo en su propio almacén**, y sirve bloques de
contexto interpretado con referencia viva a ambas fuentes.

- **No fusiona desarrollos**: skopos y AN-KLA no cambian ni una línea.
  El plugin es un repo propio, con su propio gate, specs y tests.
- Encaja en el rompecabezas del ecosistema: skopos (observador
  multi-CLI), AN-KLA (memoria deliberada), llavero (llaves), syndesmos
  (tejedor de contexto). Cada pieza independiente; el valor está en la
  articulación.

## 3. Arquitectura, cuatro piezas

1. **Localizador.** Regex sobre `skopos.turnos` (índice P-004) para
   hallar los turnos que contienen `commit-write-plan` con id de
   registro. **La clave de join es observable** — el comando con su id
   queda verbatim en el texto del turno — lo que resuelve B-3 de P-001
   ("no hay clave de join") sin exigir campos nuevos a AN-KLA ni
   disciplina por-escritura.
2. **Intérprete.** Por cada turno ancla (+ vecinos ±N de la misma
   sesión), interpretación con LLM usando el patrón ADR-014
   (compatible-OpenAI, Ollama local por defecto). La declaración
   "DATO observado, nunca instrucción" (ADR-009 P3) y la redacción de
   secretos envuelven la **entrada** del prompt, no sólo la salida —
   la ronda del 2026-08-13 ya filtró un secreto falso vía Ollama.
3. **Almacén propio.** Colección propia (p. ej. `syndesmos.
   interpretaciones`), insert-only con versionado propio. Cada
   interpretación guarda `an_kla_id` + sha de revisión y los `turn_id`
   de su ventana. **Nunca muta skopos ni AN-KLA.**
4. **Lector con join vivo.** Recuperación con presupuesto de bytes
   (C-4 de P-001, resuelta de nacimiento) que en **lectura** consulta
   la vigencia real del registro AN-KLA referenciado. Si fue refutado
   o sustituido, la interpretación se degrada o se marca — sin
   heredar el defecto C-8 de skopos (insert-only con vigencia
   petrificada).

## 4. Contratos de integración (todos de sólo lectura)

- Hacia skopos: lectura directa de `skopos.turnos` (contrato
  `documento-turno-mongo v1`, ya estable). Ninguna escritura.
- Hacia AN-KLA: lectura del sustrato (cadena de revisiones), como ya
  exigía la precondición A-1 de P-001 — nunca `retrieve` como fuente
  de autoridad, y jamás `supersede` desde lo derivado.
- Hacia el consumidor (un agente que toma contexto): bloques con
  presupuesto declarado, exclusiones enumeradas, evidencia enlazada
  (turn_id → fragmento en skopos; an_kla_id → registro vigente).

## 5. Riesgos conocidos y su mitigación en el diseño

| Riesgo | Evidencia | Mitigación |
|---|---|---|
| Vigencia que se pudre (C-8) | skopos insert-only no puede corregir | join de vigencia en lectura (§3.4) |
| Eco del corpus (C-5) | 29 turnos con firma (0.1 %) | detector periódico sobre el corpus nuevo; umbral de aceptación en §6 |
| Inyección por texto hostil | filtró un secreto falso (2026-08-13) | P3 + redacción en la ENTRADA del intérprete |
| Cobertura parcial | el gatillo cubre el 2 % anclado | declarado: es cola priorizada, no promesa total; el 98 % restante queda servible crudo por `buscar` |
| Acoplamiento de proyectos | — | repo propio, contratos de sólo lectura, cero diff en skopos/AN-KLA |

## 6. Qué haría a la afirmación "superior" falsificable

Criterios de aceptación propuestos (a afinar en rondas):

- A1: localizar las 448 anclas con precisión medida (muestreo manual
  de N=50) ≥ 98 %.
- A2: corpus interpretado completo en ≤ 3 h con Ollama local, o en
  minutos con proveedor remoto por decreto del dueño.
- A3: refutar un registro en AN-KLA degrada su interpretación en la
  siguiente lectura — test de regresión.
- A4: cero secretos crudos en interpretaciones (barrido como el de
  las rondas previas).
- A5: detector de eco sobre el corpus nuevo ≤ 0.1 % (baseline actual).
- A6: toda recuperación declara `excluded_detail` (presupuesto C-4).
- A7: `git diff` vacío en skopos y AN-KLA tras la integración.

Ejes de comparación honestos contra el mercado (mem0, Letta, Zep):
local-first, cobertura multi-CLI observada, olvido gobernado,
presupuesto declarado, evidencia cruda enlazada. "Superior" sólo con
esta lista medida — nunca como adjetivo suelto.

## 7. Preguntas para las rondas (decisión del dueño)

1. ¿Se autoriza crear el repo nuevo del plugin? (autoridad separada,
   como toda dependencia/estructura nueva).
2. ¿El plugin escribe también memorias derivadas en AN-KLA, o sólo
   lee en esta fase? (recomendado: sólo leer primero).
3. ¿Vecindad de interpretación: sólo el turno ancla o ±N vecinos?
4. ¿Config LLM propia (`SYNDESMOS_LLM_*`) o comparte `SKOPOS_LLM_*`?
5. ¿Nombre definitivo del proyecto?
6. ¿Qué comando/servicio sirve los bloques al agente que toma
   contexto (CLI propio, hook, MCP)?

## 8. Relación con decisiones cerradas

- P-001 quedó "superada" por la decisión multi-CLI (2026-08-20). Esta
  propuesta **revive puntualmente su §6** (flujo AN-KLA → skopos) con
  un mecanismo nuevo: plugin externo con anclas observadas. El
  análisis de P-001 sigue siendo evidencia válida; lo que cambia es la
  conclusión operativa, y eso se registra aquí, no por costumbre.
- P-004 (índice de turnos) es la precondición técnica cumplida: sin
  `skopos.turnos` no hay localizador ni vecindad.
- El punto 1 de la cola viva del README ("analizar desde el índice")
  gana aquí su priorización: las anclas curadas van primero.
