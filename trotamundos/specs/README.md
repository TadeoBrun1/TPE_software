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
