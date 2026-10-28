# Specs: los contratos mandan

Spec-driven development: **primero el contrato, después el código**. El enunciado evalúa que el prototipo sea
trazable, consistente con la arquitectura documentada y que respete las especificaciones definidas contractualmente.

## Contenido

| Carpeta | Qué va | Formato |
|---|---|---|
| [`openapi/`](openapi/) | APIs síncronas (REST) | OpenAPI 3 |
| [`asyncapi/`](asyncapi/) | Eventos y mensajes asíncronos | AsyncAPI 2 |
| [`schemas/`](schemas/README.md) | Detalles propios de cada tipo de reserva | JSON Schema 2020-12 |

Los archivos `*.example.yaml` son **ejemplos de formato**. Reemplazarlos por los contratos reales cuando se
definan en las iteraciones.

## Flujo de trabajo

1. En la iteración (paso 5 de ADD) se define o cambia un contrato.
2. Se edita el archivo en esta carpeta y se abre un PR.
3. Se anota en [interfaces.md](../docs/02-views/interfaces.md) quién lo produce y quién lo consume.
4. Si otro servicio lo usa, se avisa y se anota en [impact-log](../docs/01-add/impact-log.md).
5. Se implementa en `prototype/` contra ese contrato; el README del servicio indica a qué spec responde.

## Convenciones

- Nombre: `<servicio>.v<versión>.yaml` (por ejemplo `itinerary-api.v1.yaml`).
- Un cambio incompatible crea una versión nueva; no se edita la anterior. Mientras un contrato esté en versión 0.x
  (diseño, sin consumidores en producción) se puede ajustar subiendo `info.version` y anotándolo en el impact-log.
- Cada operación define sus errores.
- El campo `info.description` indica la iteración y las ADRs relacionadas.

## Validar (opcional)

```bash
npx @redocly/cli lint specs/openapi/*.yaml
npx @asyncapi/cli validate specs/asyncapi/*.yaml
```

## Contrato propuesto de iteración 2

* [Semántica, errores y coordinación con el núcleo](ingestion-contract.md).
* [AsyncAPI de novedad detectada](asyncapi/booking-change-detected.v1.yaml), borrador 0.1.0 (la iteración 4 lo amplió
  a 0.2.0; ver abajo).

No reemplaza con el mismo significado al ejemplo `booking-events.example.yaml`: distingue detectar una novedad
de confirmar un cambio. Revisado con la iteración 3 (el núcleo lo consume sin cambios, ADR-0044). RabbitMQ/AMQP y políticas se fijan en ADR-0028; contratos de APIs reales por proveedor se concretan al implementar. Validar sintaxis/esquemas no demuestra comportamiento ni cumplimiento temporal.

## Alineación de contratos de ingesta

[Enrutamiento y configuración](notification-routing.md), [agencia](agency-assistance.md),
[publicación del núcleo](core-publication.md). El esquema de novedades permite correo sin versión externa si los
datos son suficientes. RabbitMQ y políticas definidos en ADR-0028; pruebas del sistema pendientes.

## Operación y cierre de diseño de ingesta

[RabbitMQ y políticas](ingestion-operations.md), [autorización coordinada](ingestion-authorization.md),
[eventos confirmados](asyncapi/booking-confirmed.v1.yaml). Paso 7 analizado; [prototipo y evidencia futura](../prototype/ingestion-validation.md).

## Contratos de la iteración 3

* [API de itinerarios v1](openapi/itinerary-api.v1.yaml): panel con `ETag`, avisos SSE, viajes archivados y gestión
  manual. Reemplaza al ejemplo de formato `itinerary-api.example.yaml`.
* [Cambios confirmados de viajes](asyncapi/trip-changed.v1.yaml): lo consume la analítica (iteración 4).
* [Avisos de cambio del panel](asyncapi/panel-changed.v1.yaml): lo consume solo el notificador (ADR-0046).

## Contratos de la iteración 4

* [API de itinerarios](openapi/itinerary-api.v1.yaml), 0.2.0: token de acceso concreto, ticket SSE, invitaciones,
  viajes compartidos, tarjeta para redes, tipo de reserva abierto con `details` y montos con moneda ISO 4217.
* [Hechos de reservas para la analítica](asyncapi/booking-facts.v1.yaml): solo campos permitidos (ADR-0064).
* [Novedades de reservas](asyncapi/booking-change-detected.v1.yaml), 0.2.0: tipo abierto, `arrivalLocation` y
  `details` (ADR-0066).
* [Esquemas de detalles por tipo](schemas/README.md): `flight.v1` y `train.v1`.
* [Registro de auditoría](access-audit.md) de accesos a viajes compartidos (ADR-0061).

## Refinamientos de revisión de iteración 4

* [Procesamiento analítico](analytics-processing.md): deduplicación, ACK y claves anuales.
* [Medición de calidad](quality-measurement.md): tiempo de caída, cobertura y reportes de cliente.
* API de itinerarios pasa a borrador 0.3.0: SharedBooking omite details, respuestas compartidas no-store,
  DELETE de referencias local, perfil completo de bearerAuth y recepción durable de telemetría.
