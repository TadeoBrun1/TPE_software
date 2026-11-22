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

## Cuenta eliminada (iteración 5)

`DELETE /account` borra en una transacción los datos del usuario en su partición, deja una marca de cuenta
eliminada (30 días) y escribe `account.deleted.v1` en la misma outbox
([account-deleted.v1.yaml](asyncapi/account-deleted.v1.yaml), ADR-0085). Los eventos de ese usuario que estaban en la
outbox se borran en la misma transacción. Con la marca, el núcleo descarta las novedades y las aceptaciones de
sugerencias atrasadas de ese usuario.

## Transporte fijado

> **Iteración 5 (ADR-0081):** `booking.changed.v1` se retiró. Nunca tuvo consumidor y su papel lo cubre
> `booking.facts.v1`, que consumen la analítica y la recomendación de la región. Este apartado queda como registro
> del diseño original.

RabbitMQ, exchange `travel.domain`, routing key `booking.changed.v1`, cola independiente por consumidor; TLS,
roles y confirm/mandatory/ACK según [políticas](ingestion-operations.md). Esquema mínimo en
[booking-confirmed.v1.yaml](asyncapi/booking-confirmed.v1.yaml). La versión bookingVersion es interna del núcleo,
no sourceVersion del proveedor. El payload analítico puede ampliarse de forma compatible al refinar 4; este
contrato mínimo no decide su almacenamiento ni autoriza copiar datos personales indiscriminadamente.

## Consumidor analítico

La analítica aplica recepción y hechos atómicos, ACK posterior y tratamiento de períodos con clave destruida,
según [analytics-processing.md](analytics-processing.md). La outbox puede republicar: no se presupone entrega única.
