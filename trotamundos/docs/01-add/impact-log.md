# Registro de impactos entre iteraciones

**Qué es:** cada vez que una decisión de una iteración toca un elemento compartido o puede perjudicar a otra
iteración, se anota acá. Es la defensa contra "me rompieron mi iteración sin avisar".
**Cuándo se llena:** al crear el PR (ver [CONTRIBUTING §4](../../CONTRIBUTING.md)).

| Fecha | Iteración origen | Cambio o decisión | Iteración afectada | Impacto (positivo, neutro, negativo) | Resolución | ADR / PR |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## Elementos compartidos conocidos

Completar al cerrar la iteración 1.

| Elemento | Definido en | Quién lo cambia |
|---|---|---|
| Modelo de datos de reservas | Iteración 1 | Cualquiera, con aviso |
| Bus o cola de eventos | Iteración 1 | Cualquiera, con aviso |
| Contratos de `specs/` | Iteración que los crea | Su dueño, con aviso |
