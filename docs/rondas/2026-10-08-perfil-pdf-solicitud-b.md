# Autorrevisión adversarial del perfil PDF para Solicitud B

Fecha: 2026-10-08. Artefacto revisado:
`docs/propuestas/2026-10-08-perfil-pdf-solicitud-b-expertogobernanza.md`.
Alcance: propuesta documental; no implementación ni cierre de fase H25.
Revisor: el mismo agente redactor. No hubo contexto fresco, independencia
efectiva ni quórum para el protocolo de cierre de fase del
`docs/planes/plan-ciclo-precondiciones.md` §«Protocolo de cierre de fase».

| Hallazgo o intento de refutación | Evidencia, corrección y residual |
|---|---|
| **A1: el hash local se confunde con oficialidad.** Impacto: promover una copia posiblemente distinta como normativa vigente. | El hash se calculó sólo sobre `/Users/krisnova/Downloads/2000-002-001.pdf`; la ficha IMSS identifica homoclave y enlace. El texto declara explícitamente comparación de bytes y vigencia pendientes. Residual: consulta jurídica y comparación controlada del artefacto remoto antes de una afirmación oficial. |
| **A2: recuperar un derivado después de perder el original parece satisfacer B.** Impacto: cita verificable sólo contra OCR, no contra la copia preservada. | `SourceStore` actual almacena ruta, no copia. El candidato exige original recuperable, `bytes_unavailable` y control de pérdida; no acepta fallback. Residual: diseño transaccional y restauración todavía no probados. |
| **A3: las coordenadas de organigrama no acreditan una relación.** Impacto: inventar jerarquía a partir de posición o lectura lineal. | El contrato separa nodos, aristas, cajas y revisión humana; el piloto exige inversión de arista como control negativo. Residual: el criterio humano de revisión de diagramas debe acordarse con el consumidor. |
| **A4: `complete_for_declared_scope` puede esconder páginas no inspeccionadas.** Impacto: falsa cobertura total. | Se requieren inventario por página, modalidades y exclusiones; `unknown` ante fidelidad no demostrada. Residual: umbral y protocolo de muestreo por fijar antes del piloto. |
| **A5: prometer borrado o respaldo sin mecanismo.** Impacto: admisión de material con retención incompatible. | El candidato exige política previa, restore verificable y declarar borrado selectivo no soportado si no se demuestra. Residual: propietario, plazo, claves y soporte de respaldo pendientes. |
| **A6: un resultado vacío por presupuesto parece ausencia de contenido.** Impacto: falso negativo para el consumidor. | Error `budget_exceeded`, sin éxito vacío ni admisión parcial; control positivo con presupuesto suficiente. Residual: límites numéricos y formato de progreso requieren prueba y acuerdo. |
| **A7: la propuesta podría alterar ADR-020 por implicación.** Impacto: convertir la custodia por copia en decisión sin autoridad. | Estado PROPUESTA y puerta explícita a ADR nuevo que enmiende D1; sin modificar runtime, corpus ni contrato vigente. Residual: decisión de Skopos/Operador y aceptación bilateral pendientes. |

Resultado de esta autorrevisión: hallazgos A1–A7 tratados en el texto candidato;
no se afirma `proceed` de fase ni conformidad. La ronda exigida por el plan
de cierre requiere revisor de contexto fresco, ajuste, nueva verificación y
commit. El encargo actual excluye commit y no cierra una fase; por tanto ese
quórum y esa secuencia no se han alcanzado.
