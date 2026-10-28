---
status: "accepted"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (contrato booking.change.detected.v1)"
informed: ""
---

# Asignación automática de reservas a viajes por fechas

## Context and Problem Statement

RF-05 pide agrupar las reservas por viaje. Las novedades de la iteración 2 no traen el viaje (`tripId` no es
obligatorio), y las fechas de la reserva (`startAt`, `endAt`) también son opcionales en el contrato. Hay que decidir a
qué viaje va una reserva nueva que llega sin viaje, con y sin fechas.

## Decision Drivers

* RF-05 Ciclo de vida del viaje: el panel se arma por viaje, de forma automática.
* RF-04: el usuario puede corregir la asignación.
* Contrato `booking.change.detected.v1`: viaje y fechas opcionales.

## Considered Options

* A. Asignación automática por fechas, o viaje nuevo si ninguno las cubre
* B. Bandeja de reservas sin asignar para que el usuario las ubique
* C. Un viaje nuevo por cada reserva sin viaje

## Decision Outcome

Chosen option: "A. Asignación automática por fechas", because arma el panel sin intervención del usuario, que es el
objetivo del producto, y deja la bandeja solo para los casos en que no hay datos para decidir.

Reglas:

1. Si la reserva tiene fechas y caen dentro de un viaje activo del usuario, o a menos de 2 días de su inicio o fin, se
   agrega a ese viaje. Si hay más de un candidato, se elige el más cercano en fechas.
2. Si tiene fechas y ningún viaje las cubre, se crea un viaje nuevo con nombre sugerido por el destino y el mes.
3. Si pertenece a un viaje archivado y sus fechas todavía no pasaron, el viaje se reactiva (ADR-0045).
4. **Si no tiene fechas**, no se puede asignar por fechas: queda en estado `pendiente` de asignación y aparece en la
   sección "sin asignar" del panel para que el usuario la ubique. Si una novedad posterior trae las fechas, se asigna
   con las reglas 1 a 3.
5. El usuario puede mover cualquier reserva a otro viaje; desde ese momento el viaje asignado es un campo del usuario y
   las novedades no lo cambian (ADR-0044).

La asignación ocurre en la misma transacción que aplica la novedad, en la partición del usuario.

Patrones y tácticas que aplica: no introduce patrones nuevos; es una regla de dominio del módulo `viajes`, aplicada
dentro de la transacción de ADR-0040 y ADR-0044.

### Consequences

* Good, because las reservas se agrupan solas en la gran mayoría de los casos (RF-05).
* Good, because una reserva sin fechas no se asigna a ciegas.
* Bad, because la asignación por fechas puede equivocarse con dos viajes cercanos; el usuario lo corrige moviendo la
  reserva, y su corrección se respeta.
* Bad, because las reservas sin fechas necesitan una acción del usuario.

### Confirmation

Pruebas: una reserva con fechas dentro de un viaje se agrega a ese viaje; una sin viaje que la cubra crea uno nuevo;
una sin fechas queda en "sin asignar"; mover una reserva y recibir otra novedad no la devuelve al viaje original.

## Pros and Cons of the Options

### A. Asignación automática por fechas

* Good, because el panel se arma solo.
* Bad, because puede equivocarse con viajes cercanos en fechas.

### B. Bandeja sin asignar para todo

* Good, because nunca se equivoca.
* Bad, because contradice la idea de un panel que se arma solo. Se usa solo para las reservas sin fechas.

### C. Viaje nuevo por reserva

* Good, because es simple.
* Bad, because un viaje con vuelo, hotel y auto termina partido en tres.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | RF-05, RF-04 |
| Vistas afectadas | [module-view](../02-views/module-view.md), [domain-model](../02-views/domain-model.md) |
| Specs | [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml), [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0040](0040-modelo-de-lectura-del-panel.md), [0044](0044-novedades-y-cambios-manuales.md), [0045](0045-ciclo-de-vida-y-archivado-de-viajes.md) |
| Código del prototipo | `prototype/` |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #6](https://github.com/TadeoBrun1/TPE_software/pull/6),
merge `54122ee` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
