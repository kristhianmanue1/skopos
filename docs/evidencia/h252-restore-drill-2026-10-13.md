# H25.2 — ensayo de restauración y estado de periodicidad — 13 de octubre de 2026

Estado: ensayo local ejecutado por agente en sesión del Operador. No sustituye
la descarga web verificada ni la primera ejecución desatendida del horario;
tampoco adjudica relevancia ni cierre del hito 25.

## Ensayo de restauración (PASS)

`scripts/runtime_operations.py restore-latest` ejecutado con la venv del
proyecto, bajo el bloqueo cooperativo de
`/Users/krisnova/Skopos-private/runtime-v3`:

- Archivo: `runtime-v3-data.tar.gz` en la carpeta OneDrive sincronizada
  (`…/skopos_cloud/runtime-v3-backup-20261006T151151Z-c6d5f71e`), SHA-256
  `87cf1b5913ac6c91035d8c68c35ceaf5a6905583903562bd268f07220b1a169e` —
  idéntico al manifest del 2026-10-06.
- Resultado del reporte (`restore-drills/<id>/report.json` en la raíz
  privada): `status: pass`, `revisions: 2`, `projections: 4`,
  `transaction_rollback: true`, `process_stopped: true`,
  `temporary_key_removed: true`, puerto scratch 37033.
- El reporte mantiene `cloud_download_verified: false` por diseño: la copia
  usada es la sincronizada de OneDrive, **no** una descarga web presentada
  como tal.

## Periodicidad: observación del 6 al 13 de octubre

- `maintenance-state.json` sigue apuntando al respaldo del 2026-10-06T15:11Z;
  no hay directorios de respaldo nuevos ni en la raíz privada ni en la nube.
- Esta ausencia es **indistinguible** entre «la automatización corrió y no
  había cambios» (el respaldo diario es `--if-changed`) y «la automatización
  no corrió»: los registros de la tarea `skopos-respaldo-y-recuperaci-n`
  viven en el chat Codex, fuera del alcance de esta sesión. Sigue sin
  observarse la **primera ejecución desatendida** que el pendiente exige.
- La instancia operativa dedicada (puerto 37030) estaba **detenida** al
  iniciar esta sesión; el ensayo de restauración no la requiere ni la arranca.

## Pasos que siguen requiriendo al Operador

1. **Descarga web verificada** del archivo `…c6d5f71e` desde OneDrive (la
   mensual de octubre consta para el archivo anterior, no para éste).
2. **Primera ejecución desatendida** observable del horario nocturno
   (equipo encendido, app disponible, Keychain accesible) y su registro.
3. **Elección del mecanismo sustituto** del disparador en chat Codex —
   propuesta preparada en
   [2026-10-13-sustituto-periodicidad-respaldo](../propuestas/2026-10-13-sustituto-periodicidad-respaldo.md).
4. **Resguardo independiente de claves** (diferido por el Operador) y
   **adjudicación de relevancia/aceptación** de H25.2 para el cierre del
   hito 25.
