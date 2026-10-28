# Registro de auditoría de accesos a viajes compartidos

**Estado:** Propuesto (iteración 4)
**ADRs:** [0061](../docs/03-adr/0061-comparticion-con-cuenta-y-auditoria.md),
[0062](../docs/03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md)
**Driver:** QA-7 (el 100 % de los accesos no designados se rechaza y queda registrado)

## Quién escribe y qué

| Acción | Escribe | Dónde | Cuándo |
|---|---|---|---|
| `share.read` | Núcleo (`comparticion`) | Región del dueño | Cada pedido sobre un viaje ajeno, por `/shared/trips/{tripId}` o por cualquier otro endpoint, permitido o rechazado |
| `share.invite` | Núcleo (`comparticion`) | Región del dueño | El dueño crea una invitación |
| `share.accept` | Núcleo (`comparticion`) | Región del dueño | Cada intento de aceptar una invitación, aceptado o no |
| `share.remove` | Núcleo (`comparticion`) | Región del dueño | El dueño quita un permiso o cancela una invitación |
| `share.gateway_reject` | Puerta de entrada | Región de la puerta que rechaza | Todo rechazo previo al núcleo sobre `/trips/{tripId}` y sus subrutas, `/bookings/{bookingId}`, `/shared/trips/...` o `/shares/...`, incluso de la misma región y sin token válido |

## Formato de cada registro

| Campo | Contenido |
|---|---|
| `recordId` | Identificador único del registro |
| `at` | Instante (ISO 8601, UTC) |
| `action` | Una de las acciones de la tabla anterior |
| `result` | `allowed` o `denied` |
| `reason` | Si fue rechazado: `no_permission`, `owner_endpoint`, `removed`, `expired`, `secret_mismatch`, `email_mismatch`, `not_found`, `unauthenticated`, `rate_limited`, `bad_region`, `owner_region_unavailable` |
| `actorUserId` | `userId` del token de quien pidió; vacío si no había un token válido |
| `actorRegion` | Región de origen del emisor verificado; junto con actorUserId identifica al actor; vacío si no había token válido |
| `actorIssuer` | Emisor verificado del token; vacío si no había token válido |
| `method` y `route` | Método y plantilla de ruta, sin query string, secretos ni cuerpos |
| `bookingId` | Identificador solicitado, cuando la ruta es de reservas |
| `entryRegion` | Región cuya puerta de entrada recibió la solicitud |
| `tripId` | Identificador solicitado si la ruta lo incluye; ausente cuando solo hay bookingId y el núcleo aún no resolvió el viaje |
| `shareId` | Invitación, si corresponde |
| `correlationId` | Para unir el registro con su traza (ADR-0067) |

No se guardan datos del itinerario, emails, direcciones IP ni tokens.

## Reglas

* Se escribe antes de responder. El núcleo escribe en la región del dueño del viaje (la del prefijo del
  identificador); la puerta de entrada escribe en su propia región los rechazos que ocurren antes de llegar al núcleo
  del dueño: sin token o con token inválido (`unauthenticated`), región inexistente (`bad_region`) y región del dueño
  que no responde (`owner_region_unavailable`).
* Si la escritura falla, la solicitud se rechaza con `503` y el evento queda en los logs estructurados de la puerta
  de entrada con una alerta (ADR-0067). El rechazo está garantizado siempre; el registro, salvo que fallen a la vez el
  registro de auditoría y los logs de la región (riesgo residual aceptado).
* Solo agregado: ningún proceso de la aplicación puede modificar ni borrar registros. Solo la tarea de retención
  borra los registros de más de 1 año (suposición, mismo plazo que ADR-0045).
* El registro de cada región se opera como un nodo más de la base (ADR-0042): primaria y réplica sincrónica en dos
  zonas, el mismo monitor de base con acuerdo de dos de tres y reconstrucción de la réplica en la zona C.
* Lo consulta el equipo de seguridad. Un aumento de rechazos para un mismo viaje o de un mismo actor genera una
  alerta (táctica *detectar intrusiones*, ADR-0067).

## Clasificación de rutas y principal

La puerta clasifica por método y plantilla antes de rechazar autenticación o límites de tasa, sin consultar a la
base para decidir si un viaje es ajeno. Audita conservadoramente todos los rechazos de las rutas de recurso
anteriores, incluso `GET /trips/sa-east:7` sin token recibido en `sa-east`, y `PATCH /bookings/b1` con token inválido.
Cuando no puede verificar identidad, actorUserId, actorRegion y actorIssuer quedan vacíos; nunca se llenan desde
un JWT sin validar. Una ruta de reserva puede registrar bookingId sin tripId. Con token válido, el núcleo resuelve
propiedad y aplica el control de ADR-0061 antes de devolver datos o realizar cambios.

Los fallos `401`, `404`, `429` y de reenvío también siguen esa regla; un límite por cliente no es una excepción
silenciosa de auditoría. El cuerpo de la solicitud, secretos de invitación y tickets SSE no se registran.
La página pública `/cards/{cardId}` es la excepción deliberada de ADR-0063 y no concede acceso al itinerario.
La comparación de permisos usa `(actorRegion, actorUserId)` y no el identificador local aislado.

Pruebas adicionales: solicitud sin token a viaje de la misma región; token inválido sobre una reserva; acceso
con token válido por endpoint del dueño; rechazo por límite de tasa. Cada caso deja un registro o activa el
procedimiento documentado de fallo de auditoría, sin devolver datos.
