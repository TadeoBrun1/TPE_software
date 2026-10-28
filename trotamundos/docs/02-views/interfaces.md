# Interfaces

**Qué es:** resumen de los contratos del sistema. La fuente de verdad de cada contrato está en [`specs/`](../../specs/);
acá se explica quién usa cada uno y para qué.
**Mantiene:** quien posee el contrato.
**Estado:** contratos de las iteraciones 2, 3 y 4 propuestos

| Contrato | Tipo | Archivo | Productor | Consumidores | Iteración | ADR |
|---|---|---|---|---|---|---|
| API de itinerarios (panel, avisos SSE con ticket, viajes archivados, gestión manual, compartición, tarjeta para redes, telemetría del cliente) | REST y SSE | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) (0.2.0) | Núcleo (SSE: notificador; ticket y reenvío: puerta de entrada) | Web, móvil, redes sociales (solo `/cards/{id}`) | 3, 4 | 0040–0048, 0060–0063, 0065, 0066 |
| Novedad de reserva detectada (propuesta) | Evento | [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml) (0.2.0: tipo abierto y `details`) | Ingesta | Consumidor del núcleo | 2, 4 | 0020–0024, 0066 |
| Cambio confirmado de reserva | Evento | [booking-confirmed.v1.yaml](../../specs/asyncapi/booking-confirmed.v1.yaml) | Núcleo | Sin consumidores en la primera entrega: la analítica usa `booking.facts.v1` porque este evento solo lleva identificadores. Queda como evento de dominio general | 2 | 0027 |
| Hechos de reservas para la analítica | Evento | [booking-facts.v1.yaml](../../specs/asyncapi/booking-facts.v1.yaml) | Núcleo | Analítica de la misma región | 4 | 0064 |
| Cambio confirmado de viaje | Evento | [trip-changed.v1.yaml](../../specs/asyncapi/trip-changed.v1.yaml) | Núcleo | Analítica (iteración 4) | 3 | 0045, 0048 |
| Aviso de cambio del panel | Evento | [panel-changed.v1.yaml](../../specs/asyncapi/panel-changed.v1.yaml) (0.2.0: `correlationIds`) | Núcleo | Notificador (cola por instancia y cola de push) | 3, 4 | 0046, 0067 |
| Esquemas de detalles por tipo | JSON Schema | [specs/schemas/](../../specs/schemas/README.md) | Quien agrega el medio | Núcleo (validación), clientes (vista), adaptadores de ingesta | 4 | 0066 |
| Registro de auditoría | Formato de registros | [access-audit.md](../../specs/access-audit.md) | Núcleo (`comparticion`) y puerta de entrada | Equipo de seguridad | 4 | 0061 |
| Login y tokens | OpenID Connect (estándar) | — | Proveedor de identidad de cada región | Web, móvil, puerta de entrada | 4 | 0060 |
| Catálogos de textos | Archivos estáticos versionados (`/i18n/{idioma}.v{n}.json`) | — | Equipo de producto | Web, móvil | 4 | 0065 |

## Reglas

- Cambiar un contrato usado por otro servicio se avisa en el PR y se anota en [impact-log](../01-add/impact-log.md).
- Las versiones se identifican en el nombre del archivo (`v1`, `v2`).
- Cada contrato indica errores y casos de falla, no solo el camino feliz.

## Semántica de la ingesta

[Contrato y errores](../../specs/ingestion-contract.md). Los acuerdos se revisan con la iteración 3 antes de
implementar: novedad detectada no equivale a cambio confirmado. No se exige `tripId`. El núcleo verifica la
vinculación y decide conciliación/asociación. Los eventos no llevan secretos y deben tolerar reentregas.
La API de itinerarios se definió en la iteración 3 (`itinerary-api.v1.yaml`). El evento confirmado tiene contrato
propuesto en ADR-0027; los archivos con nombre `example` que quedan siguen siendo ejemplos.


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
El login del viajero se define en la iteración 4 (ADR-0060).

## Refinamiento de revisión de iteración 4

API de itinerarios: borrador 0.3.0. La vista compartida usa una proyección sin details; un DELETE de referencia
se ejecuta localmente aunque el GET del mismo tripId sea remoto. Ver el perfil JWT de ADR-0060, la clasificación
completa de [auditoría](../../specs/access-audit.md), el [consumo analítico](../../specs/analytics-processing.md) y
la [medición](../../specs/quality-measurement.md). Los contratos son propuestas para revisión, no implementación.
