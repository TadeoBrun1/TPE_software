# Enrutamiento de avisos y configuración de vinculaciones

**Estado:** diseño de la iteración 2, revisado con las iteraciones 3 y 4 e integrado en `main`; implementación pendiente. **ADR:** 0025.

## Entrada

Internet → entrada global → API Gateway de región → receptor interno de ingesta.
Antes de habilitar avisos se registra una suscripción/vinculación: proveedor, identificador opaco de suscripción,
región de origen, vinculación local y mecanismo permitido para comprobar el origen. El proveedor recibe una URL
con referencia opaca o usa una referencia que su API admita; nunca tokens de correo en la URL.

La entrada global resuelve esa referencia con un directorio mínimo de enrutamiento y deriva al Gateway regional.
Ese directorio no almacena correos ni itinerarios, pero su metadata puede ser sensible: acceso y conservación
restringidos. El Gateway y el receptor verifican origen/suscripción según el contrato real del proveedor.
No se confía en un `homeRegion` arbitrario enviado por terceros. El núcleo valida nuevamente el ámbito del evento.

Si el proveedor entrega solo un ID de reserva, la integración necesita una correspondencia registrada y acotada
por proveedor/tenant antes de habilitar notificaciones. Si no hay correspondencia inequívoca, registrar el caso
con contenido mínimo o rechazarlo según contrato, sin difundirlo a todas las regiones ni inventar un usuario.
Una caída temporal del directorio permite respuesta reintentable según el protocolo externo; el sondeo de
reconciliación por cuentas conocidas recupera novedades. El adaptador de directorio es un puerto del servicio de entrada regional/global; timeout inicial 3 s y reintentos/retención conforme a las políticas operativas. Motor concreto se define al implementar sin replicar contenido de reservas.

## Propiedad de datos

El núcleo administra usuario, región de origen, preferencias, whitelist y metadata/estado de las vinculaciones.
Ingesta guarda cursores, deduplicación de fuentes, pendientes, outbox y referencias a tokens protegidos.
Ningún proceso lee o escribe tablas del otro. Configuración y cambios de vigencia se obtienen por puertos internos
versionados acordados con 3. Una copia desactualizada no autoriza consultas tras confirmar revocación: el inicio
de operaciones debe coordinarse con la autoridad regional. Renovar tokens no reactiva una vinculación revocada.

La región se asigna según ADR-0003, no por GPS del viajero. Recuperación entre regiones no se presupone diseñada.

## Vigencia y políticas

El [protocolo de revocación](ingestion-authorization.md) define autoridad, revisión y barrera; no queda decidido
solo como «consulta un caché». Los límites de [operación](ingestion-operations.md) gobiernan consultas y registros.
