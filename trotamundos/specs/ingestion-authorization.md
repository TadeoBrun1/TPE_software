# Coordinación de autorización y revocación del correo

**Decisión de diseño de iteración 2, refinamiento de ADR-0021.** No decide autenticación del viajero de la app.

Autoridad regional: módulo de usuarios/vinculaciones del núcleo; referencia secretRef en ingesta identifica tokens
protegidos. Nunca se publica el token en eventos. Configuración tiene revision monotónica y estado active,
revoking o revoked. La región coincide con homeRegion validada por el núcleo.

Puerto interno propuesto (autenticación mutua entre servicios; API exacta en implementación):
- Obtener contexto vigente: connectionId → userId, homeRegion, revision, permisos y filtros, sin secretos.
- Iniciar operación: connectionId/revision/operationId/tipo consulta-publicación → permitido o rechazo.
- Sellar vinculación: connectionId/revision → barrera instalada, operaciones ya iniciadas y resultado.

Cada coordinador/publicador registra el inicio de una operación bajo la misma exclusión por vinculación que
se usa al instalar la barrera de revocación. No basta comprobar una bandera y arrancar mucho después.
El núcleo marca revoking y niega nuevos permisos; ordena el sellado al coordinador regional. Ingesta impide
nuevos inicios, pausa trabajos pendientes y confirma su revisión sellada. Núcleo solo confirma desvinculación
completa al viajero después de esa respuesta; si hay indisponibilidad devuelve estado pendiente y reintenta el
sellado, no informa éxito falso. Una vinculación revoking no sirve para nuevas consultas aunque un caché diga active.

Las solicitudes de proveedor o publicaciones que ya se iniciaron pueden terminar. No se promete cancelar una
llamada enviada ni retirar mensajes ya aceptados por el canal. Desde confirmación de la barrera no se inician
nuevas llamadas/publicaciones para esa revisión. El núcleo puede conservar lo ya importado según política de
usuario y retención; desvincular no borra automáticamente las reservas. La primera entrega registra este alcance.

Renovación de token usa exclusión/revision por vinculación; solo persiste el nuevo secreto si la revisión sigue
activa. Revocación externa se detecta por respuesta del proveedor o aviso si existe; no se promete detección local
instantánea de una revocación que el sistema aún desconoce. `invalid_grant` requiere nueva autorización, no bucle.

Valores iniciales: concesión de inicio de uso inmediato y timeout operativo 3 s; revocación pendiente alerta a
10 s y escalado a 30 s. El proceso no transforma un timeout en aprobación ni reanuda con tokens antiguos.
Prueba futura: carrera entre inicio y sellado, caída del coordinador, renovación simultánea y revocación externa.
