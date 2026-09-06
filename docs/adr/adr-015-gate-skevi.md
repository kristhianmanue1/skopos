# ADR-015: adopción del gate de Skevi (estructura y tamaños automatizados)

Estado: **aceptado** — decisión 🔒 del dueño, 2026-09-06 ("adelante
adopta"), tras el análisis de adopción/actualización de Skevi de la
misma fecha. Amplía la decisión de cascarón "adopción de Skevi por
referencia" (README): la referencia sigue, pero el control de límites
pasa de declaración a gate ejecutable.

## Contexto

skopos adoptó Skevi por referencia el 2026-08-12 y declaró los límites
de tamaño (800 genérico, 200 `AGENTS.md`, 300 `README.md`) "por
declaración, sin gate automatizado propio todavía". Esa declaración
congeló a Skevi en su estado del 12 de agosto: desde entonces Skevi
avanzó 9 commits normativos (gate de tamaños, gate de planes E1-E5,
disparadores objetivos de ronda adversarial, memoria de agente,
promoción Alpha→estable). El método se seguía practicando en su forma
vigente; lo que quedó rancio fue la adopción declarada.

El gate de Skevi es stdlib puro y está diseñado para copiarse sin
edición al proyecto adoptante: si la estructura difiere, se declara
`skevi-gate.json` en la raíz en vez de editar el script (ADR-006 de
Skevi). La excusa de costo de "sin gate todavía" dejó de existir.

## Decisión

### (a) Los dos scripts se copian verbatim, sin edición

`scripts/check_sizes.py` y `scripts/check_plans.py` desde el clon local
de skevi (sincronizado con `origin/main`, HEAD `910cdc4` del
2026-09-01), verificado byte a byte con `diff`. Mantenerlos sin editar
es la política: las mejoras upstream se traen con `diff`/`cp`, nunca a
mano — mismo espíritu que los parsers contra `parser-contrato/v1`.

### (b) `skevi-gate.json` declara el canon de skopos

La clave `required` **reemplaza** el canon de Skevi (sus rutas
normativas no existen aquí — la adopción es por referencia). Canon
declarado: `AGENTS.md`, `README.md`, `CLAUDE.md`, `LICENSE`,
`pyproject.toml`, `project-manifest.yaml`, `skevi-gate.json` (si falta,
el gate correría con el canon ajeno y fallaría confuso), los cinco
documentos raíz de `docs/` y los dos scripts themselves.

Los **límites NO se redeclaran**: heredar 800/200/300 sin decidirlos de
nuevo es aceptable por diseño del gate ("heredar el valor por defecto
sin decidirlo es aceptable, cambiarlo en silencio no lo es") y es lo
que skopos ya había declarado heredar. Primera corrida: 118 archivos
dentro de límites, 0 incumplimientos.

### (c) Gate de planes: inactivo por ahora, con la vía de activación escrita

La clave `plans` queda **ausente** — el gate es fail-closed y no
comprueba nada (inactivo, nunca error). Razón: el único plan que existe
(`docs/planes/plan-ciclo-precondiciones.md`) es un registro histórico
de un ciclo CERRADO; reescribirlo a la estructura E1-E5 sería retocar
un registro, no planear. El **primer plan nuevo** de skopos deberá
conformar E1-E5 (TAREA en fences, Consumes/Produce/Steps, verificación
por step, rutas existentes) y en ese mismo cambio se declara `plans` en
`skevi-gate.json`.

### (d) Los tests de los scripts no se vendorizan

Skevi mantiene los tests de sus scripts upstream (`tests/` de skevi);
copiarlos sería duplicar dos suites que pueden desincronizarse. skopos
verifica el gate por su **salida** (OK/BLOQ con código de salida), que
es el contrato observable que le importa.

## Alternativas descartadas

- **Vendorizar Skevi completo**: contradice la adopción por referencia
  decidida en el cascarón; arrastraría docs normativos ajenos que aquí
  no rigen.
- **Seguir "a ojo"**: el estándar heredado lo prohíbe expresamente
  ("se comprueban con el gate, no a ojo") y la ronda adversarial de
  skopos demostró que la verificación manual se cuela.
- **Declarar `plans` ya y reescribir el plan cerrado**: retoca un
  registro histórico cerrado para satisfacer un gate nuevo — el
  documento gana hasta que un ADR lo sustituya.

## Consecuencias

- La verificación antes de declarar terminado (AGENTS.md) pasa a exigir
  el gate en verde junto a la suite.
- Los tamaños dejan de ser honorario: un archivo que crezca de más
  bloquea, y la exención futura exige escribirla en `skevi-gate.json`,
  no en la costumbre.
- Compromiso de mantenimiento: los scripts se actualizan desde skevi
  por copia, registrando el HEAD de origen en el commit.

## Lo que este ADR NO decide

No adopta los disparadores objetivos de ronda adversarial de Skevi
(ADR-013 skevi), la estructura E1-E5 para planes existentes, ni
registra la promoción Alpha→estable de Skevi (PROP-005 D1) como
obligación — skopos ya practica lo primero, y los otros dos quedan para
decisión propia cuando haya un plan nuevo o una necesidad real.

## Firma de decisión

- Dueño: decisión 🔒 comunicada en sesión ("adelante adopta", tras el
  análisis de adopción/actualización con el clon sincronizado) ·
  Fecha: **2026-09-06**.
