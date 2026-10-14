# Arquitectura de Trotamundos — documento central

**Qué es:** punto de entrada y resumen de toda la arquitectura. No repite el detalle: lo resume y enlaza a la vista,
iteración, ADR o spec que lo contiene.
**Mantiene:** ambos. Se actualiza **al cerrar cada iteración** (y la revisa la otra persona).
**Estado:** esqueleto. Completar secciones a medida que avanzan las iteraciones.

Las secciones siguen la estructura sugerida por el paper adjunto al TPE (introducción, contexto, drivers, dominio,
contenedores, componentes, secuencias, interfaces y decisiones).

---

## 1. Introducción

<!-- Una o dos páginas: qué es Trotamundos, para quién es este documento, cómo se leyó el enunciado, estado actual. -->

| Iteración | Estado | Qué aportó a este documento |
|---|---|---|
| 1 | Pendiente |  |
| 2 | Pendiente |  |
| 3 | Pendiente |  |
| 4 | Pendiente |  |

## 2. Contexto

Ver [diagrama de contexto](00-requirements/context-diagram.md).

<!-- Pegar el diagrama y un párrafo que explique qué muestra. -->

## 3. Drivers arquitectónicos

Resumen en [architectural-drivers.md](00-requirements/architectural-drivers.md).

| Tipo | Detalle |
|---|---|
| Requerimientos funcionales | [functional-rqmts.md](00-requirements/functional-rqmts.md) |
| Escenarios de calidad | [quality-attribute-scenarios.md](00-requirements/quality-attribute-scenarios.md) |
| Árbol de utilidad | [utility-tree.md](00-requirements/utility-tree.md) |
| Restricciones y concerns | [constraints-concerns.md](00-requirements/constraints-concerns.md) |

## 4. Modelo de dominio

Ver [domain-model.md](02-views/domain-model.md).

## 5. Vista de contenedores

Ver [cc-view.md](02-views/cc-view.md) y [deployment-view.md](02-views/deployment-view.md).

| Contenedor | Responsabilidad |
|---|---|
|  |  |

## 6. Vista de componentes

<!-- Un diagrama por contenedor, con su tabla de responsabilidades; enlazar o resumir desde cc-view.md. -->

## 7. Vistas de secuencia

Ver [sequence-views.md](02-views/sequence-views.md).

## 8. Interfaces

Ver [interfaces.md](02-views/interfaces.md) y [specs/](../specs/).

## 9. Decisiones de diseño

Ver [índice de ADRs](03-adr/README.md).

| Iteración | Decisiones principales |
|---|---|
| 1 |  |
| 2 |  |
| 3 |  |
| 4 |  |

## 10. Trazabilidad

| Driver | Iteración | ADRs | Vista(s) | Spec(s) | Prototipo |
|---|---|---|---|---|---|
| QA-1 |  |  |  |  |  |
| QA-2 |  |  |  |  |  |
| QA-4 |  |  |  |  |  |
| QA-5 |  |  |  |  |  |
| QA-6 |  |  |  |  |  |
| QA-8 |  |  |  |  |  |

## 11. Riesgos y deuda arquitectónica

| Riesgo o deuda | Origen | Mitigación | Estado |
|---|---|---|---|
|  |  |  |  |
