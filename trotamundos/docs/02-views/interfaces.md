# Interfaces

**Qué es:** resumen de los contratos del sistema. La fuente de verdad de cada contrato está en [`specs/`](../../specs/);
acá se explica quién usa cada uno y para qué.
**Mantiene:** quien posee el contrato.
**Estado:** PENDIENTE

| Contrato | Tipo | Archivo | Productor | Consumidores | Iteración | ADR |
|---|---|---|---|---|---|---|
| API de consulta de itinerarios | REST | `specs/openapi/itinerary-api.v1.yaml` | Servicio de consulta | Web, móvil | 3 | |
| Novedad de reserva detectada (propuesta) | Evento | [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml) | Ingesta | Consumidor del núcleo | 2 | 0020–0024 |
| Cambio confirmado de reserva | Evento pendiente de especificar | Iteraciones 3/4 | Núcleo | Analítica | 3/4 | Pendiente |

## Reglas

- Cambiar un contrato usado por otro servicio se avisa en el PR y se anota en [impact-log](../01-add/impact-log.md).
- Las versiones se identifican en el nombre del archivo (`v1`, `v2`).
- Cada contrato indica errores y casos de falla, no solo el camino feliz.

## Semántica de la ingesta

[Contrato y errores](../../specs/ingestion-contract.md). Los acuerdos se revisan con la iteración 3 antes de
implementar: novedad detectada no equivale a cambio confirmado. No se exige `tripId`. El núcleo verifica la
vinculación y decide conciliación/asociación. Los eventos no llevan secretos y deben tolerar reentregas.
La API de consulta y el evento confirmado de analítica siguen pendientes; los ejemplos no son contratos reales.
