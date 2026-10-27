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
mínimo para consumidores, su privacidad y almacenamiento analítico se refinan en 4. Datos incompletos no generan
un evento que afirme falsamente un cambio aplicado; pueden generar un resultado de resolución separado.

La outbox del núcleo y la de ingesta son distintas y cada proceso conserva propiedad de su almacenamiento.
Las rutas de lectura/escritura pueden seguir dentro del mismo desplegable; no se impone CQRS ni otro servicio.

Validación futura: fallo antes de confirmar la transacción no genera cambio/evento parcial; fallo tras commit
permite publicar al recuperar; reentregar una novedad no duplica el cambio; cambios manuales también se publican.
