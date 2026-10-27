# Arquitectura de Trotamundos — documento central

**Qué es:** punto de entrada y resumen de toda la arquitectura. No repite el detalle: lo resume y enlaza a la vista,
iteración, ADR o spec que lo contiene.
**Mantiene:** ambos. Se actualiza **al cerrar cada iteración** (y la revisa la otra persona).
**Estado:** completo hasta la iteración 1 (en revisión). Las secciones restantes se completan con las iteraciones 2 a 4.

Las secciones siguen la estructura sugerida por el paper adjunto al TPE (introducción, contexto, drivers, dominio,
contenedores, componentes, secuencias, interfaces y decisiones).

---

## 1. Introducción

Trotamundos es un panel de gestión de viajes para web y móvil que reúne en un único lugar todas las reservas de un
viajero (vuelos, hoteles, autos, trenes y autobuses), organizadas por viaje. Las reservas llegan solas desde el correo
del usuario y desde sistemas de terceros. El sistema es global: 15 millones de cuentas, 2 millones de usuarios activos
por semana y picos fuertes ante disrupciones.

Este documento resume la arquitectura y enlaza al detalle. Está dirigido a los docentes y a quien tenga que evolucionar
el diseño.

| Iteración | Estado | Qué aportó a este documento |
|---|---|---|
| 1 | En revisión | Arquitectura de referencia, contenedores, despliegue multirregión y primeras ADRs |
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
| Aplicación web y app móvil | Clientes ricos; la app móvil es nativa y usa GPS (CON-4) |
| Entrada global | Dirige cada solicitud a la región de origen del usuario |
| Puerta de entrada | Único punto de entrada a cada región; valida, balancea y limita el tráfico |
| Núcleo | Monolito modular sin estado; único dueño de viajes y reservas |
| Ingesta | Sondea correos, recibe notificaciones y consulta a terceros; un adaptador por proveedor |
| Intermediario de mensajes | Temas de novedades de reservas y de eventos de dominio |
| Base operativa | Datos de la región, particionados por usuario |
| Analítica | Proceso separado; su almacén se decide en la iteración 4 |

## 6. Vista de componentes

Ver [module-view.md](02-views/module-view.md): módulos del núcleo y de la ingesta. Se refina en las iteraciones 2 y 3.

## 7. Vistas de secuencia

Ver [sequence-views.md](02-views/sequence-views.md).

## 8. Interfaces

Ver [interfaces.md](02-views/interfaces.md) y [specs/](../specs/).

## 9. Decisiones de diseño

Ver [índice de ADRs](03-adr/README.md).

| Iteración | Decisiones principales |
|---|---|
| 1 | Clientes ricos y API Gateway ([0004](03-adr/0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md)); núcleo modular con ingesta y analítica separadas ([0001](03-adr/0001-nucleo-modular-con-procesos-separados.md)); publicación y suscripción ([0002](03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md)); multirregión con región de origen ([0003](03-adr/0003-despliegue-por-regiones-con-region-de-origen.md)) |
| 2 |  |
| 3 |  |
| 4 |  |

## 10. Trazabilidad

| Driver | Iteración | ADRs | Vista(s) | Spec(s) | Prototipo |
|---|---|---|---|---|---|
| QA-1 | 1, 2 | 0001, 0002 | C&C | asyncapi | Ingesta y broker |
| QA-2 |  |  |  |  |  |
| QA-4 | 1, 3 | 0001, 0003, 0004 | C&C, despliegue | — | Consulta con la ingesta caída |
| QA-5 | 1, 3 | 0001, 0003, 0004 | Despliegue | — | — |
| QA-6 |  |  |  |  |  |
| QA-8 |  |  |  |  |  |

## 11. Riesgos y deuda arquitectónica

| Riesgo o deuda | Origen | Mitigación | Estado |
|---|---|---|---|
| Sondear millones de buzones puede no entrar en los 5 minutos (QA-1) | Iteración 1 | Notificaciones del proveedor de correo, sondeo como respaldo | Abierto (iteración 2) |
| La conmutación ante fallas puede consumir el presupuesto de QA-4 | Iteración 1 | Heartbeat y conmutación automática con tiempos medibles | Abierto (iteración 3) |
| Notificaciones de terceros sin región conocida | Iteración 1 | Ubicar la región a partir de la reserva | Abierto (iteración 2) |
| Itinerarios compartidos entre regiones | Iteración 1 | Leer desde la región de origen del dueño | Abierto (iteración 4) |
| CON-3 es una suposición sin normativa concreta | Requerimientos | Validarla | Abierto |
