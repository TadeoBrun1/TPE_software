# Registro de impactos entre iteraciones

**Qué es:** cada vez que una decisión de una iteración toca un elemento compartido o puede perjudicar a otra
iteración, se anota acá. Es la defensa contra "me rompieron mi iteración sin avisar".
**Cuándo se llena:** al crear el PR (ver [CONTRIBUTING §4](../../CONTRIBUTING.md)).

| Fecha | Iteración origen | Cambio o decisión | Iteración afectada | Impacto (positivo, neutro, negativo) | Resolución | ADR / PR |
|---|---|---|---|---|---|---|
| 2026-10-27 | 1 | ADR-0002 deja sin decidir: idempotencia y su clave (los correos no traen versión), mensajes desordenados desde la fuente, *outbox*, cola de errores, datos personales en los mensajes y tecnología del broker | 2 | Neutro | Se resuelven con ADRs del rango 0020–0039 | [0002](../03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) |
| 2026-10-27 | 1 | ADR-0001 deja para después la separación entre lectura y escritura del núcleo | 3 | Neutro | Se analiza con QA-2 | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| 2026-10-27 | 1 | ADR-0003 (almacén analítico) se traslada a la iteración 4 | 4 | Neutro | ADR-0060 en estado `proposed` | [0060](../03-adr/0060-almacen-analitico-separado.md) |
| 2026-10-27 | 1 | La puerta de entrada valida la identidad, pero el mecanismo de autenticación no se decide | 4 | Neutro | Se decide con QA-7 | [0005](../03-adr/0005-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) |

## Elementos compartidos conocidos

Definidos en la iteración 1.

| Elemento | Definido en | Quién lo cambia |
|---|---|---|
| Modelo de datos de reservas | Iteración 1 | Cualquiera, con aviso |
| Bus o cola de eventos | Iteración 1 | Cualquiera, con aviso |
| Contratos de `specs/` | Iteración que los crea | Su dueño, con aviso |
| Modelo canónico de reserva | Iteración 1 | Cualquiera, con aviso |
| Esquema de mensajes (novedades y eventos de dominio) | Iteración 1 | Cualquiera, con aviso |
| Clave de partición por usuario y región de origen | Iteración 1 | Cualquiera, con aviso |
| Módulos del núcleo | Iteración 1 | Cualquiera, con aviso |
| Puerta de entrada (API Gateway) | Iteración 1 | Iteraciones 3 y 4, con aviso |
