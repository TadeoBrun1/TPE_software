# Drivers arquitectónicos

**Qué es:** resumen priorizado de lo que guía el diseño. Sirve de entrada a ADD (paso 1) y es inmutable durante
el proceso: si cambia, se hace por PR revisado por ambos y se anota la razón.
**Mantiene:** ambos. **Estado:** COMPLETADO.

## Propósito del diseño

Diseño de la arquitectura de Trotamundos para una startup, con un prototipo que demuestre su viabilidad.
Es diseño de un sistema nuevo (greenfield) y la 1ra iteración considera todo el sistema como un único elemento.

## Funcionalidad primaria

| ID | Descripción | Prioridad |
|---|---|---|
| RF-01 | Procesamiento de correo | Alta |
| RF-03 | Integración con terceros | Alta |
| RF-05 | Ciclo de vida del viaje | Alta |

Detalle completo en [functional-rqmts.md](functional-rqmts.md).

## Atributos de calidad

| ID | Atributo | Importancia | Dificultad | Driver principal |
|---|---|---|---|---|
| QA-4 | Disponibilidad | H | H | Sí |
| QA-5 | Escalabilidad | H | H | Sí |
| QA-1 | Performance (frescura) | H | H | Sí |
| QA-2 | Performance (web) | H | M | Sí |
| QA-6 | Interoperabilidad | H | M | Sí |
| QA-8 | Seguridad (correos) | H | M | Sí |
| QA-3 | Performance (móvil) | M | M | No |
| QA-7 | Seguridad (compartir) | M | M | No |
| QA-9 | Evolucionabilidad | M | M | No |
| QA-10 | Usabilidad e i18n | M | H | No |

Criterio: es **driver principal** todo escenario de importancia alta (H). Los de importancia media también se
atienden, en la iteración que indica el [plan](../01-add/iteration-plan.md). QA-9 y la parte multirregión de QA-10 se
adelantan a la iteración 1 porque condicionan la estructura (ver
[iteration-1-structure.md](../01-add/iteration-1-structure.md)).

Escenarios completos en [quality-attribute-scenarios.md](quality-attribute-scenarios.md) y árbol en
[utility-tree.md](utility-tree.md).

## Restricciones y concerns

| ID | Resumen | Estado |
|---|---|---|
| CON-1 | Integración con terceros solo por APIs estándar | Confirmada |
| CON-2 | Sistemas externos que no se pueden modificar | Confirmada |
| CON-3 | Datos personales según la normativa de cada región | Suposición a validar |
| CON-4 | El cliente móvil aprovecha capacidades nativas (GPS) | Confirmada |
| CON-5 | Startup con recursos limitados: sin capacidad ociosa sin evidencia de uso | Suposición a validar |
| CRN-1 | Estructura general del sistema | Iteración 1 |
| CRN-2 | Logging, monitoreo y trazas | Iteración 4 |
| CRN-3 | Errores y reintentos con sistemas externos | Iteración 2 |
| CRN-4 | Configuración y secretos | Iteración 2 |

Detalle en [constraints-concerns.md](constraints-concerns.md).

## Escala del sistema

2 millones de usuarios activos semanales, 15 millones de cuentas, picos domingo-lunes y jueves-viernes y ante
disrupciones de viaje.

## Decisiones pendientes que afectan los drivers

- [ ] Opción avanzada A (recomendación) o B (chatbot).
- [ ] Alcance exacto del prototipo (qué escenarios se implementan).
