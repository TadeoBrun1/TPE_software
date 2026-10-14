# Drivers arquitectónicos

**Qué es:** resumen priorizado de lo que guía el diseño. Sirve de entrada a ADD (paso 1) y es inmutable durante
el proceso: si cambia, se hace por PR revisado por ambos y se anota la razón.
**Mantiene:** ambos. **Estado:** BORRADOR.

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

Escenarios completos en [quality-attribute-scenarios.md](quality-attribute-scenarios.md) y árbol en
[utility-tree.md](utility-tree.md).

## Restricciones y concerns

Ver [constraints-concerns.md](constraints-concerns.md).

## Escala del sistema

2 millones de usuarios activos semanales, 15 millones de cuentas, picos domingo-lunes y jueves-viernes y ante
disrupciones de viaje.

## Decisiones pendientes que afectan los drivers

- [ ] Opción avanzada A (recomendación) o B (chatbot).
- [ ] Alcance exacto del prototipo (qué escenarios se implementan).
