# Evidencia · la ingesta pasa por la frontera de SPEC-006

**Fecha:** 2026-08-28. **Alcance:** paso siguiente a la fase A de P-003,
declarado como pendiente en
`docs/evidencia/fase-a-adaptador-codex-2026-08-28.md`: `orquestador.py`
y `cli.py` dejan de llamar al parser de Codex directamente y pasan por
`parseo.parsear()`. Sin esto, la detección del contrato existía pero no
gobernaba nada — el pipeline seguía parseando por defecto, que es
justo lo que ADR-010 §4 prohíbe.

## Qué cambia

- **`procesar_rollout`** llama a `parsear(path)`; si el diagnóstico no
  es `ok`, no procesa ningún turno del archivo. Gana el parámetro
  opcional `on_diagnostico(ruta, ResultadoParseo)`, que recibe **siempre**
  el resultado —incluido el `ok`— para que todo descarte sea
  contabilizable y atribuible (ADR-010 §3).
- **`vigilante`** cuenta los diagnósticos de cada ciclo y los reporta a
  stderr (`ciclo: archivos descartados — formato_desconocido: 2`). Los
  `ok` no se imprimen: son el caso normal y serían ruido en cada barrido.
- **`skopos reanalizar`** (modo completo) re-lee por la frontera: si el
  archivo de origen ya no se identifica —rotado, sustituido, corrupto—
  el comando falla con el diagnóstico a la vista y **no supersede**
  (lección Y-5 de ADR-009 + §4 de ADR-010). Cabe dentro del error ya
  prometido por `cli-skopos-reanalizar v1` ("rollout de origen ilegible
  o sin el turno"): la superficie del contrato no cambia.

## Impacto medido sobre el corpus real

La pregunta que decide si el cambio es seguro: **¿qué dejaría de
ingerirse?**

| Medición | Resultado |
|---|---|
| Archivos que el vigilante descubre en `~/.codex/sessions` | 643 |
| Diagnóstico de la frontera | **643/643 `ok`** |
| Turnos que siguen entrando | 16,223 |
| **Archivos que dejarían de entrar** | **0** |

Es decir: la ingesta real no pierde nada. El cambio no es una poda, es
una puerta — lo que hoy entra seguía entrando, y lo que no se identifique
en el futuro (otro CLI escribiendo `.jsonl` en ese árbol, un archivo
rotado a medias) se descartará **con diagnóstico** en vez de parsearse
como si fuera Codex.

## Verificación

- Suite completa: **137 tests OK** (131 previos + 6 nuevos).
- Tests nuevos: archivo sin identidad no se procesa ni llama al modelo;
  el descarte se notifica con su diagnóstico; el `ok` también se
  notifica; los descartes se reportan agregados por diagnóstico y los
  `ok` no; `reanalizar` sobre un rollout que ya no se identifica sale con
  código 1, imprime el diagnóstico y **deja intacta** la versión guardada.
- Fixtures actualizadas: los rollouts sintéticos de `test_orquestador`,
  `test_vigilante` y el de `reanalizar` en `test_cli` ahora declaran
  `session_meta`, porque son rollouts de Codex y la frontera exige
  identidad. No se debilitó ninguna aserción: sólo se completó el dato
  que el formato real siempre trae (616/616 en el corpus del 2026-08-20,
  643/643 hoy).

## Nota de método

Una corrida intermedia de la suite reportó `OK (skipped=5)` y ocultó un
fallo real: MongoDB no respondió en ese instante y las clases que
dependen de él se saltaron, incluida la de `reanalizar`, que estaba en
rojo por una fixture sin identidad. **Un `OK` con saltos no es un `OK`**
— las corridas que respaldan este documento tienen los 137 ejecutados,
verificado dos veces seguidas.
