# Contrato inicial de asistencia con agencia — RF-06

**Estado:** propuesta; requiere revisión con núcleo y agencia elegida. **ADR:** 0026.

## Recorrido

Usuario → Gateway → núcleo (autoriza acceso al viaje y crea solicitud) → trabajo persistente de integración →
trabajador de asistencia y adaptador de agencia del núcleo → API/canal de agencia. La respuesta normalizada vuelve al núcleo por mensaje
persistente y este actualiza el seguimiento. Son intercambios separados de `booking.change.detected.v1`.
No se implementan recomendaciones ni chatbot; RF-06 es asistencia con la agencia preferida.

## Solicitud

Campos: `requestId` estable, `schemaVersion`, `correlationId`, `userId`, `homeRegion`, `tripId`, `agencyId`,
`issueCategory`, descripción mínima necesaria y referencias de reservas autorizadas, cuando correspondan.
El núcleo decide qué información puede compartirse; no enviar el correo completo ni credenciales de usuario.
El adaptador verifica que el destino corresponda a la agencia configurada. La API externa concreta se define
antes de implementar; este contrato semántico no afirma que todas las agencias admitan el mismo protocolo.

## Resultado

Campos: `resultId`, `requestId`, `schemaVersion`, `correlationId`, `homeRegion`, `agencyId`, estado
(`submitted`, `in_progress`, `resolved`, `failed`), referencia externa opcional, fecha conocida y resumen mínimo.
El núcleo valida origen/correlación y conserva seguimiento; el adaptador no modifica reservas directamente.
Si la agencia informa un cambio de reserva, se normaliza por el flujo de novedades con sus reglas habituales.

## Fallos

Reintentos usan el mismo requestId y el mecanismo idempotente externo si existe. Ante resultado incierto, consultar
estado o apartar para resolución antes de duplicar solicitudes; no prometer entrega única en una API sin soporte.
Fallo temporal conserva trabajo; rechazo permanente o destino desconocido requiere revisión. Autorización y
permisos por viaje pertenecen al núcleo. La cola interna no es endpoint público que el usuario pueda invocar.

## Confirmación futura

Una solicitud autorizada llega a la agencia simulada; se rechaza otra sin permiso. Reintentos y respuestas
repetidas no duplican el seguimiento. No se declara un tiempo máximo de resolución que el enunciado no fija.

## Propiedad y aislamiento

El módulo saliente `asistencia` pertenece al desplegable del núcleo (ADR-0026). La solicitud y su outbox se guardan
atómicamente. El trabajador consume la cola de asistencia con concurrencia acotada y conexiones independientes de
los hilos HTTP. Los resultados se aplican con control durable por `resultId` y `requestId`. No comparte tablas ni
código de ingesta. Compartir desplegable no garantiza aislamiento físico: verificar impacto en consulta con la
iteración 3 antes de dimensionar producción.
