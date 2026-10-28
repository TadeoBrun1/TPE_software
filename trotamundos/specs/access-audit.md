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
| `share.gateway_reject` | Puerta de entrada | Región de la puerta que rechaza | Un pedido sobre un recurso de compartición (`/shared/trips/...`, `/shares/...`, o un viaje con prefijo de otra región) que se rechaza antes de llegar al núcleo del dueño |

## Formato de cada registro

| Campo | Contenido |
|---|---|
| `recordId` | Identificador único del registro |
| `at` | Instante (ISO 8601, UTC) |
| `action` | Una de las acciones de la tabla anterior |
| `result` | `allowed` o `denied` |
| `reason` | Si fue rechazado: `no_permission`, `owner_endpoint`, `removed`, `expired`, `secret_mismatch`, `email_mismatch`, `not_found`, `unauthenticated`, `bad_region`, `owner_region_unavailable` |
| `actorUserId` | `userId` del token de quien pidió; vacío si no había un token válido |
| `actorRegion` | Región de origen de quien pidió (del token); vacío si no había un token válido |
| `entryRegion` | Región cuya puerta de entrada recibió la solicitud |
| `tripId` | Viaje al que se quiso acceder (tal como vino en la solicitud) |
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
