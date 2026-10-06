# H25.2 — activación local monousuario

## Alcance y autoridad

El Operador autorizó continuar la integración, confirmó uso local monousuario
y proporcionó el destino OneDrive. Su «adelante» autorizó la instancia dedicada,
pruebas y admisión del export previamente aprobado. No autoriza inferir aceptación
de relevancia, multiusuario, ADR-019 ni migración del Mongo legado.

Código observado: `801363166dfdb7315cef790a1050524eeda2f660`, con implementación
runtime de `d9abbc8`. Sin cambios de producto en esta activación.

## Estado observado

- Raíz privada: `/Users/krisnova/Skopos-private/runtime-v3`, modo 0700.
- Mongo: `127.0.0.1:37030`, replica set `skopos_runtime_v3_rs`, un nodo.
- Base: `skopos_runtime_v3`; autenticación habilitada mediante keyfile.
- Usuario de aplicación con `readWrite` sólo en esa base; administración separada.
- Credenciales y keyfile privados, fuera de Git y OneDrive. Fuentes operativas
  fuera de Git y OneDrive; su copia de respaldo sí está en OneDrive.
- Arranque manual bajo la cuenta del Operador; no launchd ni inicio automático.
- Mongo legado no modificado. Un nodo no proporciona alta disponibilidad.

Monousuario no impide varios procesos ni aísla agentes con acceso a la misma
cuenta. El usuario de aplicación puede modificar su base: no es un registro
inmutable ni una frontera de autorización por proyecto.

## Operación

Usar el Python del proyecto y el lanzador privado; éste carga credenciales
internamente, sin incluirlas en argumentos visibles del proceso:

```bash
.venv/bin/python /Users/krisnova/Skopos-private/runtime-v3/operate.py status
.venv/bin/python /Users/krisnova/Skopos-private/runtime-v3/operate.py stop
.venv/bin/python /Users/krisnova/Skopos-private/runtime-v3/operate.py start
.venv/bin/python /Users/krisnova/Skopos-private/runtime-v3/operate.py source --help
```

Ejecutar desde la raíz de Skopos. `start` solicita arranque: comprobar `status`
después. No repetir si ya está activo. No usar el URI por defecto de `skopos
source`, que apunta al Mongo legado. El lanzador fija base y conexión dedicada.
El lanzador es un artefacto operativo privado, no una nueva interfaz publicada
del paquete. Su dependencia del checkout y del entorno virtual es explícita.

Reversión: `stop`, conservar fuentes/base/respaldo, dejar de invocar runtime.
No convertir ni borrar registros; el consumidor TXT anterior no lee runtime.

## Verificaciones efectivas

Informe privado: `runtime-v3/validation.json`. Controles negativos con positivo:
lectura anónima rechazada, cuenta de aplicación rechazada en otra base y lectura
permitida en su base. No es una prueba contra procesos con acceso a credenciales.

Fuente sintética conservada bajo proyecto `operational-smoke`; fuente autorizada
bajo `skopos-local`, source ID `dsh-export-28eff1a5`, revisión 1. Ambas pasaron
importación, replay sin duplicados, receipt, búsqueda literal y vistas
text_projection, original_jsonl y derived_event. Dos proyecciones por fuente.
Hash del export antes/después:
`6fe02ace6d9e31233e18b920796a539c362637733f7efb2881595c90994dfcb2`.
Estas pruebas no establecen relevancia semántica, autoría ni completitud del export.

El primer arranque falló porque Mongo instalado no admite fork en macOS;
se corrigió el lanzador antes de admitir datos. El primer ensayo de restauración
falló en el script de verificación al buscar source_sha256 fuera del sobre;
se corrigió el script y se repitió, sin modificar la base operativa.

## Respaldo y recuperación

Mongo detenido y puerto cerrado antes de copiar; respaldo local restaurado en
`/private/tmp/skopos-operational.sFDvDD/restored`, Mongo autenticado aislado 37031.
Reconfiguración y relocalización de rutas sólo en esa copia. Validación completa
de ambas colecciones, hashes, recibos y todas las proyecciones de las dos
revisiones correctos. Instancia de restauración detenida; operativa reiniciada y
observada como primario. No se ensayó pérdida de energía ni recuperación remota.

Destino bajo el directorio OneDrive autorizado:
`runtime-v3-backup-20261006T112547Z/runtime-v3-data.tar.gz`.
SHA-256: `833d22dfaec636d26bd58fa1ba1d93d50975acbe9ee9e05f0dd61450922202c0`.
Incluye base fría, fuentes e informe; excluye contraseñas y keyfile. La base
contiene verificadores de contraseña Mongo. No se añadió cifrado al archivo.
Manifest en el mismo directorio; reporte privado en `runtime-v3/backup-report.json`.

La copia en la carpeta sincronizada tiene hash comprobado; sincronización y
descarga desde nube NO verificadas. La restauración probada utilizó las claves
locales: falta custodia independiente segura de claves y ensayo desde nube para
afirmar recuperación ante pérdida del equipo. No es respaldo del corpus legado.
No hay programación automática ni eliminación por retención.

## Límites y siguiente paso

H25.2 tiene operación local comprobada para captura y conservación, no cierre
global de H25 ni aceptación de relevancia. Persisten las limitaciones documentadas
del ensayo de doce consultas; embeddings y ADR-019 siguen diferidos.
Prioridad: custodia independiente de claves sin publicarlas, confirmar recuperación
desde OneDrive y acordar periodicidad del respaldo. Autorrevisión del productor,
no auditoría independiente. No se ejecutaron agentes revisores.

## Regresión y memoria

462 pruebas OK, sin omisiones, en 83.303 s, ejecutadas en replica set temporal
exclusivo 37032, detenido al finalizar. Log:
`/private/tmp/skopos-operational.sFDvDD/regression/suite.log`.
Gates de tamaños y planes correctos: 282 archivos y un plan. Diff documental
revisado; no se cambió código del paquete ni se instalaron dependencias.

AN-KLA actualizada mediante plan-write y commit-write-plan, representación
summary/model_derived, verificación correcta. Revisión 16:
`sha256:9d7404aae10c6b83e0b8ebe93d7b7b2ee9007eef6fbbd1c632fd25aba7e85e73`.
Registro `f-skopos-h252-local-operation-2026-10-06`, que enmienda el estado de
despliegue de los registros anteriores, sin sustituir decisiones de relevancia.
