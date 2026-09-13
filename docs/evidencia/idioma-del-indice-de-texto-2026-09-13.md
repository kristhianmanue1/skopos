# El índice de texto está en inglés sobre un corpus en español — 2026-09-13

> Medición hecha para responder la pregunta del hito 11: ¿`$text` alcanza,
> o hacen falta embeddings? La respuesta corta es que la pregunta no se
> podía contestar, porque lo que se estaba midiendo era una configuración
> equivocada.

## Hallazgo

Los dos índices de texto se crean sin declarar idioma, así que Mongo usa
su default:

```
skopos.analisis  tema_text_resumen_text            default_language: "english"
skopos.turnos    texto_usuario_text_texto_agente_text  default_language: "english"
```

El corpus es español. `almacenamiento.py` los crea con
`create_index([("tema","text"),("resumen","text")])`, sin el parámetro.
ADR-006 ya había anticipado que el idioma importa —"coincidencia por
palabra, con stemming y stopwords **según el idioma configurado en
Mongo**"— pero nadie lo configuró.

## Consecuencia 1: las stopwords españolas son términos buscables

Sobre los 332 análisis del corpus al momento de medir:

| Término | `english` | `spanish` |
|---|---|---|
| `de` | **331 de 332** | 0 |
| `del` | 248 | 0 |
| `la` | 260 | 0 |
| `que` | 195 | 0 |
| `con` | 252 | 0 |
| `para` | 178 | 0 |

Con el índice inglés, `de` recupera el corpus entero. La consulta
`"reconstruccion del indice offsets"` devolvía 127 resultados **por el
`del`**; sin esa palabra devuelve 1. El ruido que parecía falta de
semántica era una palabra vacía arrastrando todo el corpus.

## Consecuencia 2: el ranking, no sólo el conteo

`textScore` pondera frecuencia, y una stopword aparece muchas veces por
documento, así que domina el puntaje. Top-3 real:

```
consulta: "donde vive la llave del proveedor"
  english:  Sistema de dietas para pacientes (eduEMD) || Cierre de F0-A en EKTEL || Push y deuda técnica
  spanish:  Fallo de autenticación de la llave ZAI_API_KEY || Resiliencia tras caída de Docker || Migración multi-LLM
```

Seis preguntas de arranque de sesión, con índice español: **top-1
correcto en las seis**. Con índice inglés devuelven entre 229 y 332
resultados de 332 — el corpus completo.

| Consulta | `english` | `spanish` |
|---|---|---|
| por que se reconstruyo el indice | 331 resultados | 36, top-1 correcto |
| que decidimos sobre el idioma del codigo | 331 | 56, top-1 correcto |
| esta prendido el vigilante | 332 (objetivo en #4) | 16, **#1** |
| donde vive la llave del proveedor | 316 (objetivo en #6) | 17, **#1** |

## Consecuencia 3: la morfología española no colapsa

El stemmer inglés no sabe reducir verbos españoles:

| Grupo | `english` | `spanish` |
|---|---|---|
| analizar / analizado | 5 / **0** | 11 / 11 |
| indexar / indexado | **0** / 3 | 5 / 5 |
| reparar / reparado | 2 / **0** | 4 / 4 |

## Lo que `$text` NO está perdiendo

Comparé presencia real (regex sobre los documentos) contra lo que halla
la búsqueda, en 8 palabras del corpus: **8 de 8, recall exacto, 0
pérdidas** (`índice` 5/5, `análisis` 16/16, `turno` 26/26, `vigilante`
6/6…). El motor no pierde lo que está escrito. El problema era el idioma
del análisis léxico, no la capacidad de recuperar.

## Defecto del cambio, medido y no escondido

Con el stemmer español, los términos en `-ción` **escritos sin tilde**
fallan:

| Término | `english` | `spanish` |
|---|---|---|
| `reparación` | 2 | 4 |
| `reparacion` (sin tilde) | 2 | **0** |
| `interpretación` | 0 | 1 |
| `interpretacion` | 0 | **0** |
| `índice` / `indice` | 5 / **0** | 5 / 5 |

Es mixto —`indice` sin tilde mejora, `reparacion` empeora— pero la clase
`-ción` sin tilde es justo la que uno teclea. Mitigación propuesta en
ADR-019: expandir el término en el CLI (`-cion` → `-ción`) al armar la
consulta, cinco líneas y un test.

## El test decisivo para el hito 11

Cuatro consultas escritas a mano como paráfrasis del documento objetivo.
Sólo una logró **cero palabras en común** con él (las otras tres
compartieron una: `rechaza`, `aislar`, `trabajo` — dato en sí mismo: el
vocabulario del corpus es difícil de esquivar):

```
objetivo: "Ensayo de medición de latencia Skopos ↔ escrubery (REQ-10)"
consulta: "demora del canal hacia el repositorio ajeno"   (solape léxico: NINGUNO)
  english:  posición #274 de 331  -> fuera de --max 20, no lo encuentra en la práctica
  spanish:  no lo encuentra
```

**Ningún índice léxico recupera una paráfrasis sin palabras en común.**
Eso, y sólo eso, es lo que comprarían los embeddings. Las tres consultas
donde sí había una palabra compartida se recuperaron con el índice
español en el top-10.

## Conclusión

1. La condición que ADR-006 puso al hito 11 —"que `$text` resulte
   insuficiente en uso real"— **no está satisfecha**, y hasta hoy no se
   podía evaluar: el ruido observado venía del idioma del índice.
2. Corregir el idioma es un parámetro. Adoptar embeddings es una
   dependencia nueva, un almacén de vectores y re-indexar 17,417 turnos.
   Hacerlo primero habría resuelto un defecto de stopwords con un modelo.
3. El hito 11 se reabre con la pregunta correcta, que no es "¿hay
   ruido?" sino "¿cuántas de mis consultas reales no comparten ninguna
   palabra con lo que busco?". Hoy no existe una sola medición de eso.

Reproducible: el experimento copia `skopos.analisis` a una colección
aparte con `default_language="spanish"`, mide, y borra la copia. No se
tocó ningún índice de producción.
