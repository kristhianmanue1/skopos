# ADR-012: orígenes de filas — cómo se sella un turno que no vive en un archivo de texto

Estado: **propuesto** — pendiente de decisión 🔒 del dueño. Habilitaría
el adaptador de **opencode**, último CLI de la fase B de P-003.
Extiende ADR-010; no lo revierte.

## Contexto

Los cuatro adaptadores existentes leen **archivos de texto**: una línea
por evento (codex, claude-code, kimi) o un objeto JSON por sesión
(cline). Sobre eso, ADR-010 §5 promete algo concreto — *"todo turno
normalizado es resoluble a bytes sellados de su archivo original"* — y lo
implementa con `offset_inicio`/`offset_fin` más `fragmento_sha256`.

**opencode no guarda archivos: guarda filas.** Medido el 2026-08-28 en
`~/.local/share/opencode/opencode.db` (SQLite, 4.4 GB, con WAL vivo):

| Tabla | Filas | Qué aporta |
|---|---|---|
| `session` | 879 | `directory` (⇒ `proyecto`), `title`, `version`, `model` |
| `message` | **52,741** (3,909 `user`, 48,832 `assistant`) | `id`, `session_id`, `time_created`, `data` con el rol |
| `part` | **227,875** | `data` con `type` y `text`; 32,915 partes de texto |

Volumen conversacional: **34.6 M caracteres**, ~22 % más de lo que suman
hoy los cuatro CLIs soportados. Turnos estimados: **~3,900** (uno por
mensaje de usuario).

### Con qué choca, exactamente

1. **Offsets y sello (§5)**: una fila no tiene rango de bytes estable en
   el `.db`; SQLite reorganiza páginas y el WAL las mueve. Un
   `offset_inicio` sería ficción.
2. **Protocolo de instantánea (§5)**: "abrir una vez, `fstat`, leer N
   bytes" no aplica a 4.4 GB que mutan mientras se leen.
3. **Cursor (ADR-011)**: valida por `sha256` del prefijo del archivo. No
   hay prefijo.

## Decisión propuesta

Introducir el **localizador de origen** como concepto explícito del
contrato, con dos formas, y declarar el equivalente honesto de cada
garantía del §5 para la forma nueva.

### (a) El origen se declara, no se supone

```
origen := {tipo: "archivo", ruta, offset_inicio, offset_fin}
        | {tipo: "filas",   ruta, tabla, ids}
```

Los cuatro adaptadores actuales siguen produciendo `tipo: "archivo"`
**sin cambio alguno**. opencode produce `tipo: "filas"` con los ids de
los `message` que componen el turno.

### (b) La instantánea de un origen de filas es una transacción de lectura

El §5 exige que *diagnóstico, turnos, offsets y sello correspondan
exactamente a los mismos bytes materializados*. En SQLite el equivalente
exacto existe: una **transacción de lectura** ve un snapshot consistente
aunque la base cambie por debajo. No es una analogía floja: es la misma
garantía, con el mecanismo del motor en vez del descriptor de archivo.

### (c) El fragmento es la serialización canónica de sus filas

`fragmento_sha256` se computa sobre la **serialización canónica**
(claves ordenadas, sin espacios, UTF-8 — el mismo `canonical-json/v1`
que ya usa AN-KLA) de las filas que componen el turno.

**El invariante del §5 sobrevive intacto**: todo turno sigue siendo
resoluble a bytes sellados y verificables. Lo que cambia es **cómo se
direcciona** ese contenido —por ids de fila en vez de por offsets—, no
si se puede verificar.

### (d) Sin cursor para orígenes de filas, porque no hace falta

Medido: **un barrido completo de la base cuesta 0.7 s** (52,742 mensajes
en 0.1 s, 227,881 partes en 0.6 s). El ciclo de archivos, con cursor,
cuesta 3.7 s. Añadir un cursor aquí sería optimizar lo que ya es lo más
barato del sistema. La ficha lo declara y ADR-011 lo tolera: el cursor
es caché, no obligación.

*(Si algún día hiciera falta, `time_created` es monótono y una consulta
acotada al último día responde en 4 ms — pero eso sería otro ADR, con su
propia evidencia.)*

## Alcance del cambio (lo que hay que tocar, sin adornos)

- `Turno`: los offsets pasan a ser **opcionales**, y aparece el
  localizador. Los adaptadores de archivo no cambian de comportamiento.
- **`documento-turno-mongo v2`** y **`documento-analisis-mongo v3`**:
  offsets obligatorios sólo cuando `origen.tipo = "archivo"`.
- **`cli-skopos-query`**: la recuperación del `fragmento_completo` pasa a
  despachar por tipo de origen (leer rango de bytes, o releer filas y
  re-serializar). Las mitigaciones P4a/P5/P3 de ADR-009 se aplican igual
  a ambas ramas.
- Documentos ya guardados: **no se tocan**. Todos son de origen archivo y
  su forma sigue siendo válida; el campo nuevo es aditivo.

## Alternativas descartadas

- **Espejo JSONL exportado** (Skopos escribe archivos normalizados desde
  la base y los trata como origen): no toca ningún contrato, pero el
  sello pasaría a probar *nuestra copia*, no la fuente — la promesa del
  §5 se volvería literalmente falsa. Además duplica 34.6 M de caracteres
  en disco y crea un problema de sincronización nuevo (la fuente cambia,
  el espejo envejece). **Rechazada por deshonesta con su propia
  garantía**, no por costosa.
- **Offsets sintéticos** (números que no apuntan a nada, o el rango de la
  fila dentro de un volcado imaginario): mentir en un campo que otros
  componentes usan para releer. Rechazada.
- **No soportar opencode**: defendible —es el único CLI que no encaja—,
  pero deja fuera el corpus más grande después de Codex y con más texto
  por turno. Se registra como opción viva si el dueño prefiere no mover
  contratos.

## Consecuencias (si se acepta)

- El contrato deja de asumir que "origen" significa "archivo de texto",
  que era un supuesto no declarado. Cualquier CLI futuro con almacén de
  base de datos entra por la misma puerta, sin otro ADR.
- Aparece una rama nueva en la recuperación de fragmentos, con su propio
  camino de fallo (fila borrada, base movida) que debe diagnosticarse
  igual que un archivo ausente.
- El adaptador de opencode queda escribible: identidad
  `opencode:{message_id}` (calificada, §7), `proyecto` de
  `session.directory` con la regla C-9, cierre derivado de usuario a
  usuario —como claude-code y cline—, y `ocurrido_en` de `time_created`
  (epoch en milisegundos, la misma conversión a ISO que ya hicieron
  cline y kimi).

## Lo que este ADR NO decide

No decide indexar ni analizar el contenido de opencode: eso lo gobierna
P-004 y sus decisiones. Tampoco toca ADR-001/REQ-9 ni la política de
arranque de ADR-008.

## Firma de decisión

- Dueño: **pendiente**. Evidencia medida el 2026-08-28 en esta sesión;
  no se implementa nada hasta la 🔒.
