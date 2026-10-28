---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (contrato booking.change.detected.v1)"
informed: ""
---

# Aplicación de novedades en el núcleo: dueño por campo y asignación automática a un viaje

## Context and Problem Statement

La iteración 2 entrega al núcleo novedades (`booking.change.detected.v1`) que no afirman que la reserva cambió y que no
traen el viaje (`tripId`). También resolvió duplicados (control de entrada idempotente) y desorden (comparar versión
de la fuente si existe; conservar cancelaciones que llegan antes que la reserva). Quedan dos decisiones del núcleo:

1. Qué pasa cuando una novedad externa choca con un cambio manual del usuario sobre la misma reserva (RF-04).
2. A qué viaje se asigna una reserva nueva que llega sin viaje (RF-05).

## Decision Drivers

* RF-04 Gestión manual: el usuario puede editar sus reservas.
* RF-05 Ciclo de vida del viaje: las reservas se agrupan por viaje de forma automática.
* QA-6: procesar el 99,9 % de los mensajes válidos sin pérdida ni duplicación.
* El panel debe reflejar la realidad del proveedor (por ejemplo, un vuelo cancelado debe verse cancelado).

## Considered Options

Conflicto entre cambio manual y novedad:

* A1. Dueño por campo: el proveedor define sus datos y el usuario los suyos; se avisa si se pisa una edición
* A2. Gana siempre el proveedor
* A3. Gana siempre el usuario
* A4. Cada conflicto queda pendiente hasta que el usuario decida

Reserva nueva sin viaje:

* B1. Asignación automática por fechas, o viaje nuevo si ninguno las cubre
* B2. Bandeja de reservas sin asignar para que el usuario las ubique
* B3. Un viaje nuevo por cada reserva sin viaje

## Decision Outcome

Chosen options: "A1. Dueño por campo" y "B1. Asignación automática por fechas", because el panel muestra la realidad
del proveedor sin perder lo que el usuario anotó, y se arma solo, que es el objetivo del producto.

**Dueño por campo (A1):**

| Campo de la reserva | Dueño | Ante una novedad externa |
|---|---|---|
| Fechas y horarios, estado (confirmada, modificada, cancelada), código, proveedor, ubicación | Proveedor | Se aplica la novedad. Si el usuario había editado ese campo, se le avisa ("el hotel cambió la fecha que habías modificado") |
| Nombre visible, notas, viaje asignado | Usuario | Se conserva el valor del usuario |

* Cada reserva registra qué campos editó el usuario y cuándo, para poder avisar.
* Una reserva creada a mano (sin referencia de proveedor) no recibe novedades hasta que una novedad con datos
  suficientes se concilie con ella; esa conciliación sigue la política de la iteración 2 (caso pendiente si hay
  ambigüedad).
* El orden entre novedades sigue lo decidido en la iteración 2: versión de la fuente si existe; si no hay orden
  confiable, no se pisa a ciegas.

**Asignación a un viaje (B1):**

1. Si las fechas de la reserva caen dentro de un viaje activo del usuario, o a menos de 2 días de su inicio o fin, se
   agrega a ese viaje. Si hay más de un candidato, se elige el más cercano en fechas.
2. Si ningún viaje la cubre, se crea un viaje nuevo con nombre sugerido por el destino y el mes.
3. Si la reserva pertenece a un viaje archivado y sus fechas todavía no pasaron, el viaje se reactiva (ADR-0045).
4. El usuario puede mover la reserva a otro viaje; desde ese momento el viaje asignado es un campo del usuario y las
   novedades no lo cambian.

Todo se aplica en una transacción local de la partición del usuario: control de entrada de la novedad, cambio,
actualización del panel (ADR-0040) y evento de dominio en la outbox (ADR-0027).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Idempotent Receiver* (de la iteración 2) | El control de entrada evita aplicar dos veces la misma novedad | QA-6 |
| Patrón *Transactional Outbox* (ADR-0027) | Cambio y evento confirmados juntos | QA-6 |
| Táctica *aumentar la cohesión* (modificabilidad) | Las reglas de dueño por campo y de asignación viven solo en los módulos `reservas` y `viajes` | RF-04, RF-05 |

### Consequences

* Good, because el panel refleja la realidad del proveedor y respeta las anotaciones del usuario.
* Good, because las reservas se agrupan solas, sin intervención del usuario (RF-05).
* Bad, because hay que registrar qué campos editó el usuario.
* Bad, because la asignación por fechas puede equivocarse con dos viajes cercanos; el usuario lo corrige moviendo la
  reserva, y su corrección se respeta.

### Confirmation

Prototipo y pruebas: una novedad de cancelación sobre una reserva editada a mano deja la reserva cancelada, conserva
las notas y genera el aviso; una reserva nueva con fechas dentro de un viaje se agrega a ese viaje; una sin viaje
crea uno nuevo; mover una reserva y recibir otra novedad no la devuelve al viaje original.

## Pros and Cons of the Options

### A2. Gana el proveedor

* Good, because es simple y siempre refleja al proveedor.
* Bad, because el usuario pierde sus notas y nombres sin entender por qué.

### A3. Gana el usuario

* Good, because respeta las ediciones del usuario.
* Bad, because si el vuelo se cancela o cambia de horario, el panel muestra un dato falso.

### A4. Decide el usuario

* Good, because nunca se pisa nada.
* Bad, because hasta que responda, el panel muestra información dudosa, y la mayoría de los conflictos tienen una
  respuesta obvia.

### B2. Bandeja sin asignar

* Good, because nunca se equivoca.
* Bad, because contradice la idea de un panel que se arma solo.

### B3. Viaje nuevo por reserva

* Good, because es simple.
* Bad, because un viaje con vuelo, hotel y auto termina partido en tres.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | RF-04, RF-05, QA-6 |
| Vistas afectadas | [module-view](../02-views/module-view.md), [domain-model](../02-views/domain-model.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | [ingestion-contract.md](../../specs/ingestion-contract.md), [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml) |
| ADRs relacionadas | [0024](0024-avance-y-publicacion-durable.md), [0027](0027-publicacion-del-nucleo.md), [0040](0040-modelo-de-lectura-del-panel.md) |
| Código del prototipo | `prototype/` |
