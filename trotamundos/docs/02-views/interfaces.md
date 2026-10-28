# Interfaces

**Qué es:** resumen de los contratos del sistema. La fuente de verdad de cada contrato está en [`specs/`](../../specs/);
acá se explica quién usa cada uno y para qué.
**Mantiene:** quien posee el contrato.
**Estado:** contratos de iteración 2 propuestos; API de consulta pendiente de iteración 3

| Contrato | Tipo | Archivo | Productor | Consumidores | Iteración | ADR |
|---|---|---|---|---|---|---|
| API de consulta de itinerarios | REST | `specs/openapi/itinerary-api.v1.yaml` | Servicio de consulta | Web, móvil | 3 | |
| Novedad de reserva detectada (propuesta) | Evento | [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml) | Ingesta | Consumidor del núcleo | 2 | 0020–0024 |
| Cambio confirmado de reserva | Evento | [booking-confirmed.v1.yaml](../../specs/asyncapi/booking-confirmed.v1.yaml) | Núcleo | Analítica | 2, implementación 3/4 | 0027 |

## Reglas

- Cambiar un contrato usado por otro servicio se avisa en el PR y se anota en [impact-log](../01-add/impact-log.md).
- Las versiones se identifican en el nombre del archivo (`v1`, `v2`).
- Cada contrato indica errores y casos de falla, no solo el camino feliz.

## Semántica de la ingesta

[Contrato y errores](../../specs/ingestion-contract.md). Los acuerdos se revisan con la iteración 3 antes de
implementar: novedad detectada no equivale a cambio confirmado. No se exige `tripId`. El núcleo verifica la
vinculación y decide conciliación/asociación. Los eventos no llevan secretos y deben tolerar reentregas.
La API de consulta sigue pendiente. El evento confirmado tiene contrato propuesto en ADR-0027; los archivos con
nombre `example` siguen siendo ejemplos.


## Contratos complementarios de la iteración 2

| Contrato | Productor / responsable | Consumidor / destino |
|---|---|---|
| [Enrutamiento](../../specs/notification-routing.md) | Entrada global y Gateway | Receptor interno de ingesta |
| [Asistencia](../../specs/agency-assistance.md) | Núcleo autoriza; módulo saliente de asistencia integra agencia | Agencia y seguimiento en núcleo |
| [Publicación confirmada](../../specs/core-publication.md) | Núcleo y su outbox | Consumidores de eventos de dominio |

La autenticación de la aplicación no es la autorización OAuth de un buzón. Sus mecanismos no se confunden.

## Transporte fijado

RabbitMQ/AMQP sobre TLS: [políticas](../../specs/ingestion-operations.md). Novedades llevan routing key con shard
pero conservan tipo lógico. Evento confirmado: [booking-confirmed.v1.yaml](../../specs/asyncapi/booking-confirmed.v1.yaml).
[Protocolo de autorización](../../specs/ingestion-authorization.md) completa la vigencia interna sin elegir login del viajero.
