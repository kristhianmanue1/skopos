# Incorporación acotada de un procedimiento CTIM propuesto — borrador v0.1

**Estado: PROPUESTO, sin documento recibido ni operación activada.** Este
texto prepara un intercambio futuro entre expertoGobernanza como consumidor y
Skopos como custodio de fuentes. No registra una norma aprobada, vigente o
admitida al corpus. No modifica el perfil local de siete originales CTIM.

## Identidad y procedencia requeridas

Antes de solicitar custodia, el consumidor debe declarar una identidad de
material estable y revisión, tipo real del archivo, longitud y SHA-256 de los
bytes, título y emisor atribuidos, fecha/versiones que el propio documento
declare, medio de obtención y momento de observación. Debe aportar una ficha
de procedencia atribuida, con su propio SHA-256 y referencia recuperable.
`proposal_status: draft_unapproved` describe el estado conocido para este
ensayo; cualquier clasificación más específica exige evidencia del productor.
Los datos hoy desconocidos permanecen `unknown`, no se completan por
inferencia. Una URL o nombre de archivo no prueba identidad de bytes ni
vigencia jurídica.

## Intercambio y autoridad

1. El host anuncia un perfil aprobado: formatos, raíces, materiales, acceso
   efectivo, límite de tamaño, retención, recuperación y modalidad de custodia.
   El agente no crea esos permisos ni amplía el perfil en una solicitud.
2. El consumidor declara material, revisión, hash, ficha atribuida, alcance de
   lectura y necesidad de recuperación. `provided_file` puede transportar
   bytes; no autoriza `managed_copy`. `verified_external_reference` sólo puede
   usarse si ya existe una raíz preautorizada, lectura efectiva, referencia
   persistente y retención vigente.
3. Skopos acepta o rechaza con `request_id`, hash de solicitud, identidad de
   política y recibo correlacionado. Rechaza sin entregar contenido cuando
   falten bytes, hash, ficha, autorización de raíz/acceso o política de
   retención; cuando el material exceda límites; o cuando revisión e identidad
   entren en conflicto. No sustituye requisitos faltantes con defaults nuevos.
4. Tras aceptación, la recuperación por identidad vuelve a comprobar recibo,
   bytes originales, hash, ficha y política. La derivación PDF es opcional y
   requiere política propia; sus páginas, modalidades, `item_id`, `bbox` y
   cobertura quedan con `fidelity_status: unreviewed` hasta cotejo. Una
   respuesta de página no adjudica actores, semántica o vigencia.

Las decisiones rutinarias dentro de un perfil ya autorizado corresponden a
los agentes. Plataforma/responsable configura raíces, permisos, respaldo,
retención y cierre. El Operador decide cambios de política/ADR, nueva custodia
propia o acceso fuera de raíz, admisión jurídica/corpus, aceptación de riesgo
y promoción de fase. Ningún agente concede permisos de OS, retención indefinida
o copia permanente por sí mismo.

## Aislamiento del perfil actual

`skopos/ctim-source-access-policy/v0.1` fija exactamente siete identidades y
el hash de su inventario; el lector rechaza una octava fuente. El preparador
local también exige siete entradas conocidas. El procedimiento futuro debe
tener un perfil separado o una versión nueva de perfil/inventario aprobada y
probada. No se reescribe el perfil de siete fuentes ni se interpreta el
presente borrador como permiso para hacerlo. La fuente propuesta permanece
fuera de búsqueda, lectura y corpus actuales hasta completar ese proceso.

## Prueba mínima antes de usar el nuevo perfil

- Comprobar bytes y SHA-256 del original y de la ficha atribuida; registrar
  identidad, revisión, política y recibo sin exponer rutas al consumidor.
- Recuperar el original por identidad tras reinicio y comparar bytes/hash;
  probar rechazo con hash alterado, raíz ajena, política ausente o caducada,
  tipo/tamaño inválido y fuente no admitida.
- Si se deriva PDF, verificar manifiesto y cobertura de páginas físicas,
  preservar localizadores y rechazar páginas mayores que el límite sin
  truncarlas. Revisar visualmente las citas que dependan de maquetación.
- Confirmar que el perfil de siete fuentes conserva las siete identidades y
  rechaza la nueva, y que el nuevo perfil no activa corpus ni llamadas a modelo.

**Pendiente para este caso:** el documento aún no se entregó. Por ello no hay
bytes, SHA, `source_id`, clasificación comprobada, ficha, política aceptada ni
prueba de recuperación que permitan admitirlo. La preparación documental no
produce recibo de custodia ni disponibilidad operativa.
