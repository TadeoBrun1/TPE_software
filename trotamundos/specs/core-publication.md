# Publicación confiable de eventos del núcleo

**Estado:** propuesta de iteración 2 coordinada con 3; ADR-0027. No es implementación del núcleo.

El núcleo guarda en una misma transacción: cambio de viaje/reserva, control de aplicación del mensaje cuando
provenga de ingesta y evento pendiente en su propia outbox. Los cambios manuales generan eventos de la misma forma.
Solo se confirma al canal de novedades después de persistir el resultado o una resolución durable pendiente.

Un publicador del núcleo lee su outbox y publica en el tema de eventos de dominio; marca enviado después de la
confirmación durable del broker. Si cae en ese intervalo, puede republicar con el mismo eventId. Consumidores
como analítica deben tolerar reentregas. No se promete atomicidad entre base y broker ni entrega exactamente una vez.

Sobre inicial a acordar: eventId, schemaVersion, correlationId, userId/homeRegion, bookingId, bookingVersion
interna del núcleo, tipo de cambio y committedAt. Esa versión interna no es sourceVersion externa. El payload
mínimo para consumidores, su privacidad y almacenamiento analítico se refinaron en la iteración 4: la analítica
consume `booking.facts.v1`, un evento aparte con la lista de campos permitidos (ADR-0064). Datos incompletos no generan
un evento que afirme falsamente un cambio aplicado; pueden generar un resultado de resolución separado.

Cada fila de la outbox guarda también el contexto de traza (`traceparent`) que se publica como encabezado del
mensaje ([ingestion-operations.md](ingestion-operations.md#5-contexto-de-traza-en-los-mensajes), ADR-0067).

La outbox del núcleo y la de ingesta son distintas y cada proceso conserva propiedad de su almacenamiento.
Las rutas de lectura/escritura pueden seguir dentro del mismo desplegable; no se impone CQRS ni otro servicio.

Validación futura: fallo antes de confirmar la transacción no genera cambio/evento parcial; fallo tras commit
permite publicar al recuperar; reentregar una novedad no duplica el cambio; cambios manuales también se publican.

## Transporte fijado

RabbitMQ, exchange `travel.domain`, routing key `booking.changed.v1`, cola independiente por consumidor; TLS,
roles y confirm/mandatory/ACK según [políticas](ingestion-operations.md). Esquema mínimo en
[booking-confirmed.v1.yaml](asyncapi/booking-confirmed.v1.yaml). La versión bookingVersion es interna del núcleo,
no sourceVersion del proveedor. El payload analítico puede ampliarse de forma compatible al refinar 4; este
contrato mínimo no decide su almacenamiento ni autoriza copiar datos personales indiscriminadamente.
