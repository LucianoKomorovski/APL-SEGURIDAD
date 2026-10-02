# Retirada selectiva — 2 de octubre de 2026

Se desactivaron presencia, permanencia máxima, entrega y reposición.
El control de accesos conserva credencial, edificio, zona, horario, entradas,
salidas, alertas, administración y filtros multiedificio.

- Las migraciones 0001–0006 y la base existente se conservan sin cambios.
- Presencia y MovimientoCredencial quedan como archivo histórico de consulta
  en administración. Las presencias abiertas ya no indican ocupación actual.
- Emitida y Repuesta conservan su estado y siguen denegando accesos. No se
  pueden crear ni reactivar mediante los formularios o la API operativa.
- Las nuevas llaves nacen activas; se recupera la edición básica de estado.
- El sembrado ya no crea escenarios retirados ni sobrescribe credenciales
  existentes. No se ejecutó sobre la base del proyecto.
- El brief, HTML y PDF anteriores se conservan como antecedentes de la
  iteración descartada. No describen el funcionamiento vigente.
- No se implementaron incidentes ni órdenes de intervención.

Respaldo previo: `_backups/20261002T032534Z/`. Incluye `workspace.tar.gz`
(árbol completo, Git y archivos sin rastrear), manifiesto SHA-256 verificado,
estado de Git, parches y copia consistente de SQLite. Extraer el archivo
en un directorio vacío para recuperar el estado previo sin pisar trabajo.

Verificación: 27 pruebas Django aprobadas en SQLite temporal en memoria;
compilación Vite aprobada. ESLint conserva los 6 errores y 5 advertencias
preexistentes. La comprobación de migraciones sigue señalando únicamente
las opciones descriptivas pendientes de 15 modelos; no se generaron ni
aplicaron migraciones. No se ejecutaron pruebas de navegador o hardware real.
