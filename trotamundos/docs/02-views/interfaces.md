# Interfaces

**Qué es:** resumen de los contratos del sistema. La fuente de verdad de cada contrato está en [`specs/`](../../specs/);
acá se explica quién usa cada uno y para qué.
**Mantiene:** quien posee el contrato.
**Estado:** PENDIENTE

| Contrato | Tipo | Archivo | Productor | Consumidores | Iteración | ADR |
|---|---|---|---|---|---|---|
| API de consulta de itinerarios | REST | `specs/openapi/itinerary-api.v1.yaml` | Servicio de consulta | Web, móvil | 3 | |
| Evento de reserva actualizada | Evento | `specs/asyncapi/booking-events.v1.yaml` | Ingesta | Consulta, analítica | 2 | |

## Reglas

- Cambiar un contrato usado por otro servicio se avisa en el PR y se anota en [impact-log](../01-add/impact-log.md).
- Las versiones se identifican en el nombre del archivo (`v1`, `v2`).
- Cada contrato indica errores y casos de falla, no solo el camino feliz.
