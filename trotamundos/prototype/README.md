# Prototipo — implementación pendiente

**Estado al cierre documental:** no hay servicios implementados, docker-compose ni resultados de ejecución.
Este directorio conserva el plan de validación, no un prototipo ejecutable. Los contratos y las ADRs orientan la
implementación futura. No hay un comando de arranque disponible todavía.

## Escenarios previstos

| Recorrido candidato | Contrato | Decisiones | Evidencia futura |
|---|---|---|---|
| Novedad de correo sin versión externa y reserva consultable | [ingestion-contract.md](../specs/ingestion-contract.md) | ADR-0020, 0024, 0027 y 0040 | Datos sintéticos, persistencia, outbox y lectura |
| Reentrega y recuperación ante caída | [ingestion-operations.md](../specs/ingestion-operations.md) | ADR-0024, 0027 y 0028 | Un efecto durable y publicación recuperable |
| Consulta del panel y aviso SSE | [itinerary-api.v1.yaml](../specs/openapi/itinerary-api.v1.yaml) | ADR-0040, 0041 y 0046 | Versión, ready, revalidación y reconexión |
| Compartición con autorización y auditoría | [access-audit.md](../specs/access-audit.md) | ADR-0060, 0061 y 0062 | Actor permitido, rechazado y permiso quitado |
| Hechos analíticos idempotentes | [analytics-processing.md](../specs/analytics-processing.md) | ADR-0064 | Reentrega, commit y cambio de período |

El conjunto definitivo se acotará antes de implementar. Estos son candidatos, no una afirmación de que la cátedra
aceptó ese alcance. Ver [plan de validación de ingesta](ingestion-validation.md),
[medición de calidad](../specs/quality-measurement.md) y [cierre documental](../docs/04-evaluation/first-delivery-review.md).

Cada servicio futuro deberá indicar cómo se ejecuta, qué contrato implementa, qué decisiones materializa y qué
pruebas se ejecutaron, con versión y resultados. Se usarán datos sintéticos y simuladores; no credenciales reales.
