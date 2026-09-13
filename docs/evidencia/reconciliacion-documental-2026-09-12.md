# Reconciliación documental — 2026-09-12

## Encargo y base

El humano autorizó verificar y actualizar la documentación después de
identificar divergencias entre Skopos y la recomendación de idioma de Skevi.
Base limpia: `main`, `acf6c359cbe89648db23ba5bbacbed40a8a79dc7`.
La revisión se preparó en una copia aislada de ese commit. No certifica
sincronización remota ni estado de servicios.

Alcance: AGENTS.md, README.md, project-manifest.yaml, guía rápida,
hoja de ruta, nota de sustitución parcial en ADR-016, ADR-018 y esta evidencia.
Objetivo: describir capacidades implementadas y límites observados, fijar
la regla prospectiva de idioma y conservar contratos e historia.
Cierre: documentos coherentes con el código, gates y ronda independiente;
parar ante cambios concurrentes en la base o necesidad de modificar datos.
Sin cambios de código, instalaciones, corridas, reparación, commit ni push.

## Resultado y límites

- Cinco orígenes implementados, `analyze` disponible y alias conservados.
- ADR-018 sustituye parcialmente ADR-016: identificadores nuevos en inglés;
  español elegido para producto/documentación/comentarios y conversación
  humana por defecto, con elección explícita para esta última.
- El legado no se migra. La procedencia de Skevi es un incremento local
  todavía sin commit, no una versión publicada ni adopción completa.
- `query` verifica longitud y sello cuando existe; acepta legado sin sello
  marcado `sellado:false`. `search` sirve texto indexado redactado y acotado
  sin releer el archivo de origen ni verificar su sello.
- P-007 continúa pendiente. Su §2 atribuye a `buscar` relectura y verificación
  que no aparecen en `busqueda.py`; se registra esta discrepancia sin
  modificar la propuesta ni inferir un diagnóstico o reparar offsets.
- Las cifras del piloto son históricas. El estimador usa 19.6 s/turno y
  no descuenta análisis existentes; no demuestra duración actual.
- MongoDB sirve a las operaciones con datos; sólo el análisis necesita
  proveedor LLM. Ollama es el predeterminado, sustituible según ADR-014.

## Verificación

- Comparación de todos los `.py` versionados: sin cambios frente a la base.
- Ayuda real de `analyze`: project, cli, anchor, since, until, limit, dry-run.
- Suite con Python 3.9.6 del entorno existente: 272 pruebas descubiertas,
  `OK (skipped=67)`: 205 ejecutadas correctamente y 67 omitidas.
  El arnés permite fixtures HTTP locales en puertos efímeros y bloquea
  conexiones externas, MongoDB (27017) y Ollama (11434). Se necesitó permiso
  del entorno para enlazar los servidores de prueba locales. El primer
  intento restringido falló en siete fixtures por ese bloqueo.
  Este resultado no acredita integraciones ni funcionamiento end-to-end.
- `python3 scripts/check_sizes.py`: OK; comprobación final tras incorporar
  este registro indicada en la entrega.
- `python3 scripts/check_plans.py`: OK, sin planes declarados porque falta
  la clave `plans`; no equivale a un gate de planes activo.
- AN-KLA existente beta.22: status y verify OK, revisión 6; no actualizado
  ni escrito por este encargo.

## Ronda adversarial

Una revisión independiente pidió corregir la garantía excesiva de integridad,
los requisitos universales de Ollama y la cita de autorización. Se corrigieron
los tres puntos; la discrepancia preexistente de P-007 se conserva arriba.
La ronda no repitió la suite: su resultado procede del ejecutor principal.
La conclusión final de la ronda y la aplicación se registran en la entrega.
