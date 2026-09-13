# ADR-018 — Código nuevo en inglés y comunicación humana elegida

Estado: aceptado por instrucción del humano «adelante converificaicon y actulizacion», 2026-09-12, tras la comparación con Skevi y la diferencia
explicada con ADR-016. Implementación documental local en AGENTS.md,
README y guía rápida; sin renombrado del código existente.

## Contexto y procedencia

ADR-016 separó inglés en la frontera y español en el interior. La revisión
actual pide coherencia con la convención de código nuevo en inglés y
comunicación humana elegida. Copiar esa norma sin sustituir la elección
local dejaría dos instrucciones contradictorias.

Referencia: Skevi §3.1 y ADR-029, incremento local del 2026-09-12 sobre
base `ffc72520be5ffc50142969f6dc2f614bddac598c`; todavía sin commit ni
release de ese incremento al consultarlo. Es transferencia selectiva por
instrucción humana, no instalación de una versión publicada. Este ADR es
la regla autocontenida de Skopos: no depende de leer otro repositorio.

## Decisión

Sustituye ADR-016 §(b) para módulos, funciones y variables **nuevos**:
identificadores estructurales propios en inglés, incluidos clases, ramas,
comandos, flags y claves. No se traduce todo el código existente.

Elecciones locales: comunicación humana predeterminada en español;
producto (ayuda y mensajes), documentación, comentarios/docstrings y
mensajes de commit en español. El humano puede elegir otro idioma para
la conversación. Esa preferencia no cambia la documentación o interfaz
persistente sin solicitud explícita. No inferir idioma de su nacionalidad.

Conservar nombres exactos de contratos externos, generadores, términos de
dominio y nombres propios con razón documentada. El código legado, incluidos
flags españoles y campos almacenados, sigue siendo compatible. ADR-016
§(c)/(d) continúa regulando la migración futura y convivencia de alias;
este cambio no activa v3, ni renombra datos, ni retira comandos.

La revisión comprueba identificadores nuevos y elección humana explícita.
No hay detector automático de inglés ni obligación de traducir comentarios.
Una revisión de prosa no prueba mejor rendimiento de un LLM.

## Alternativas

- Mantener español interno para código nuevo: contradice la convención que
  el humano pidió adoptar tras comparar ambos proyectos.
- Traducir legado y datos ahora: amplía alcance y arriesga compatibilidad
  sin necesidad para fijar la regla futura.
- Inglés en toda la comunicación: impone un idioma al humano y confunde
  contratos técnicos con explicaciones.

## Casos y consecuencias

- `appointment_not_found` puede explicarse en español sin cambiar el código.
- Una respuesta solicitada en inglés no cambia los mensajes de la CLI.
- `--solo-redaccion` y campos Mongo existentes conservan su escritura exacta.
- Nuevas funciones nacen en inglés aunque estén en un módulo legado español.
- Si una nueva audiencia o artefacto necesita otra elección persistente,
  se pregunta antes de fijarla; el resto del trabajo puede continuar.

La referencia de AGENTS.md apunta aquí; README y guía son explicaciones,
no nuevas fuentes de autoridad. Las decisiones anteriores se conservan con
la sustitución parcial señalada. No se actualizan los gates copiados de
Skevi ni se declara adopción completa de su versión local.
