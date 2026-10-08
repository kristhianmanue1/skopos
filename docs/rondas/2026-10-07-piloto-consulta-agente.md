# Autorrevisión adversarial del piloto de consulta — 2026-10-07

Alcance: documento experimental, sin ejecución de modelos, fixtures ni servicios.
Autor/revisor: misma instancia Codex. No hubo revisión independiente ni consenso.
Autorización: el Operador pidió revisar adversarialmente y editar con mejoras.
Objeto: `docs/planes/activos/piloto-consulta-agente-2026-10-07.md`.
Entrada: v0.1, SHA-256
`1a300046422fe71c82da1860dd46bea12e88fa9599012cd0eea2cfd56472c4bb`.
Salida: v0.2; digest final registrado al final del acta tras verificar.
Base Git: `fe1e8cbf6fe521c3e45fb87e76acf38c5f476084`.

## Método y frontera de evidencia

Lectura íntegra del documento y contraste con source_cli, runtime_store,
runtime_views, runtime_verification y README ya inspeccionados en la sesión.
Se intentó construir contraejemplos que cumplieran el protocolo y aun así
permitieran conclusiones falsas. Las observaciones siguientes son defectos de
diseño documental; no son fallos de producto reproducidos mediante ejecución.
Los gates estructurales no prueban causalidad, utilidad ni calidad de evidencia.

## Hallazgos y correcciones

| ID / impacto | Contraejemplo y evidencia en v0.1 | Corrección v0.2 | Riesgo residual |
|---|---|---|---|
| H01 alto: comparación sesgada | §4 enviaba pregunta completa a búsqueda de subcadenas; B podía elegir un término útil | search_term explícito e igual para A/B/C; alcance limitado a oportunidad de entrega | No valida extracción autónoma de consultas |
| H02 alto: baseline indefinido | §4 dejaba algoritmo/orden de A a elección; un A artificialmente malo aparentaría mejora | Referencia casefold y orden fijados; mismos sobres, herramientas y corpus; separar paridad de ventaja | Latencia de backend y verificación puede diferir; medir y declarar |
| H03 alto: falso conjunto ciego | §5 exigía reservar casos al mismo agente que los elaboraba | Casos de confirmación; ceguera sólo con separación acreditada | Autor conoce los casos: sesgo no eliminado |
| H04 alto: autoridad circular | Q05 podía adjudicarse por la propia afirmación de prioridad de una fuente | Política de tarea externa, igual para condiciones; señuelo sin autoridad | No demuestra autenticación de autorizaciones reales |
| H05 alto: recepción incompleta admitida | §6 aceptaba unknown, pero no impedía iniciar las 108 sin observar incorporación | Incorporación observable y controles positivo/omitido obligatorios antes de serie principal | Depende de instrumentación disponible en cliente real |
| H06 alto: verificador no probado | Un log productor y un marcador adivinado podían producir acuse aparente | Omitir bloque, ack antiguo, identidad/hash erróneos deben fallar; control sano pasa | Verificador aún no implementado ni probado |
| H07 medio: presupuesto ambiguo | 16 KiB podía contar contenido único y omitir reenvíos; 2048 tokens no acotaba llamadas | Bytes acumulados, 8 inferencias, techos stdout/stderr, conciliación de timeout remoto | Coste efectivo depende de telemetría y proveedor |
| H08 medio: orden y denominadores | Sólo ABC/BCA/CAB; interrupción podía desaparecer de métricas; recall vacío indefinido | Seis órdenes balanceados; slots no iniciados/fallidos explícitos; macro por familia y N/A | 12 familias siguen siendo muestra pequeña |
| H09 alto: victoria por ruido | §10 aceptaba cualquier mejora o reducción de tiempo, incluso mínima | Umbrales exploratorios explícitos, protección por familia, coste y pares; empate puede validar contrato | Umbrales son propuestas, sin potencia estadística |
| H10 medio: congelamiento prematuro | T0 congelaba antes de construir T1/T2 y corregir T3 | T0 provisional; congelamiento completo al cerrar T3 | Cambios posteriores requieren nueva serie |
| H11 medio: señales filtradas | Catálogo no acotado podía revelar proyecto señuelo; Q07 invitaba conclusión global desde vacío | Catálogo del proyecto/tarea; conclusión limitada; Q10 no infiere contenido excluido | El catálogo aún es una ayuda controlada, no descubrimiento autónomo |
| H12 medio: hashes y límites incompatibles | Hash de stdout y bloque sin representación definida; prueba de 20 resultados en adaptador limitado a 5 | Bytes sellados definidos; mapeo de transformación; límites backend/adaptador separados | Schema experimental y pruebas quedan por implementar |

Todos los hallazgos se corrigieron en el documento. No se atribuyen correcciones
de código ni resultados de ejecución. Los riesgos residuales permanecen visibles.

## Segunda pasada sobre el candidato

- Caso de igualdad A/B: ahora puede pasar contrato sin fingir utilidad superior.
- Caso de sólo log de título: no habilita T4 ni cierre de recepción.
- Caso de abortar tras resultados favorables: comparación incompleta; no promoción.
- Caso de autor que conoce referencias: no declara reserva ciega ni independencia.
- Caso de contexto reinsertado en varias llamadas: cuenta coste acumulado y
  distingue incorporación repetida legítima de acuse duplicado.
- Caso de inferencia que sigue tras timeout local: coste reservado e incertidumbre;
  no reintento automático ni declaración falsa de cancelación remota.
- Caso de respuesta vacía con fuente indisponible: la rúbrica exige limitar alcance.
- Caso de atribución de vigencia por fecha: política externa o conflicto explícito.

Estos son razonamientos contra el texto final, no pruebas ejecutadas del harness.
No se identificó otro bloqueo documental material dentro del alcance revisado.

## Verificación y dictamen

Verificaciones finales: check_sizes y check_plans, referencias locales del plan,
espacios finales y lectura del diff. Resultados concretos al final del acta.
No se ejecutó la suite de software: sólo se editaron documentos y la suite puede
crear datos/conectarse a servicios. No se acredita regresión de implementación.

Dictamen: PROCEED DOCUMENTAL para entregar v0.2 como protocolo afinado.
No autoriza ejecutar el piloto ni activar funcionalidades. T0 conserva selección
de cliente/version, presupuesto y entorno; T3 debe demostrar observabilidad
antes de iniciar T4. No hay aceptación productiva ni revisión independiente.
No se modificaron los cambios preexistentes del proyecto; sin commit/push.

Comprobación registrada a las 18:52:27 UTC del 2026-10-07:
- Plan v0.2, 476 líneas, SHA-256
  `896242b45d2b71a68915a3c96a142a0b34e24c766df31ed61a1ad47e1dec164e`.
- check_sizes: OK, 297 archivos dentro de límites.
- check_plans: OK, 2 planes, reglas E1–E5.
- 10 referencias locales backtickadas a archivos Markdown/Python comprobadas;
  ninguna ausente. Sin espacios finales en plan y acta.
- Diff v0.1→v0.2 leído completo. No se ejecutaron controles funcionales del
  piloto, mutaciones del verificador ni pruebas de software.
