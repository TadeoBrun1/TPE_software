# Specs: los contratos mandan

Spec-driven development: **primero el contrato, después el código**. El enunciado evalúa que el prototipo sea
trazable, consistente con la arquitectura documentada y que respete las especificaciones definidas contractualmente.

## Contenido

| Carpeta | Qué va | Formato |
|---|---|---|
| [`openapi/`](openapi/) | APIs síncronas (REST) | OpenAPI 3 |
| [`asyncapi/`](asyncapi/) | Eventos y mensajes asíncronos | AsyncAPI 2 |

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
- Un cambio incompatible crea una versión nueva; no se edita la anterior.
- Cada operación define sus errores.
- El campo `info.description` indica la iteración y las ADRs relacionadas.

## Validar (opcional)

```bash
npx @redocly/cli lint specs/openapi/*.yaml
npx @asyncapi/cli validate specs/asyncapi/*.yaml
```

## Contrato propuesto de iteración 2

* [Semántica, errores y coordinación con el núcleo](ingestion-contract.md).
* [AsyncAPI de novedad detectada](asyncapi/booking-change-detected.v1.yaml), borrador 0.1.0.

No reemplaza con el mismo significado al ejemplo `booking-events.example.yaml`: distingue detectar una novedad
de confirmar un cambio. Revisión con la iteración 3 pendiente. RabbitMQ/AMQP y políticas se fijan en ADR-0028; contratos de APIs reales por proveedor se concretan al implementar. Validar sintaxis/esquemas no demuestra comportamiento ni cumplimiento temporal.

## Alineación de contratos de ingesta

[Enrutamiento y configuración](notification-routing.md), [agencia](agency-assistance.md),
[publicación del núcleo](core-publication.md). El esquema de novedades permite correo sin versión externa si los
datos son suficientes. RabbitMQ y políticas definidos en ADR-0028; pruebas del sistema pendientes.

## Operación y cierre de diseño de ingesta

[RabbitMQ y políticas](ingestion-operations.md), [autorización coordinada](ingestion-authorization.md),
[eventos confirmados](asyncapi/booking-confirmed.v1.yaml). Paso 7 analizado; [prototipo y evidencia futura](../prototype/ingestion-validation.md).
