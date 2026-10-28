# Registro de auditoría de accesos a viajes compartidos

**Estado:** Propuesto (iteración 4)
**ADRs:** [0061](../docs/03-adr/0061-comparticion-con-cuenta-y-auditoria.md),
[0062](../docs/03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md)
**Driver:** QA-7 (el 100 % de los accesos no designados se rechaza y queda registrado)

## Qué se registra

| Acción | Cuándo |
|---|---|
| `share.read` | Cada `GET /shared/trips/{tripId}`, permitido o rechazado |
| `share.invite` | El dueño crea una invitación |
| `share.accept` | Alguien intenta aceptar una invitación, con éxito o no |
| `share.revoke` | El dueño revoca un permiso o cancela una invitación |
| `share.bad_region` | Un identificador con una región que no existe (se registra en la región del lector) |

## Formato de cada registro

| Campo | Contenido |
|---|---|
| `recordId` | Identificador único del registro |
| `at` | Instante (ISO 8601, UTC) |
| `action` | Una de las acciones de la tabla anterior |
| `result` | `allowed` o `denied` |
| `reason` | Si fue rechazado: `no_permission`, `revoked`, `expired`, `already_accepted`, `not_found`, `bad_region` |
| `actorUserId` | `userId` del token de quien pidió |
| `actorRegion` | Región de origen de quien pidió (del token) |
| `entryRegion` | Región cuya puerta de entrada recibió la solicitud |
| `tripId` | Viaje al que se quiso acceder |
| `shareId` | Invitación, si corresponde |
| `correlationId` | Para unir el registro con su traza (ADR-0067) |

No se guardan datos del itinerario, emails ni tokens.

## Reglas

* Se escribe en la región del dueño del viaje (la del prefijo del identificador) antes de responder, salvo
  `share.bad_region`, que se escribe en la región del lector porque esa región no existe. Si la escritura falla, la
  solicitud se rechaza con `503`: no hay accesos sin registrar.
* Solo agregado: ningún proceso de la aplicación puede modificar ni borrar registros. Solo la tarea de retención
  borra los registros de más de 1 año (suposición, mismo plazo que ADR-0045).
* Lo consulta el equipo de seguridad. Un aumento de rechazos para un mismo viaje o un mismo actor genera una alerta
  (ADR-0067).
* Una solicitud sin token válido se rechaza en la puerta de entrada con `401` antes de llegar al núcleo; se registra
  en los logs y métricas de la puerta de entrada (ADR-0067), no en este registro, porque no hay una identidad que
  registrar.
