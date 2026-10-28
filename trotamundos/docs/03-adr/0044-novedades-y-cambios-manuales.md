---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (contrato booking.change.detected.v1)"
informed: ""
---

# Conflictos entre novedades y cambios manuales: dueño por campo y marca de borrado

> La asignación de reservas a viajes, que antes formaba parte de esta ADR, se separó en
> [ADR-0048](0048-asignacion-de-reservas-a-viajes.md).

## Context and Problem Statement

La iteración 2 entrega al núcleo novedades (`booking.change.detected.v1`) y resolvió los duplicados (control de
entrada idempotente) y el desorden (comparar la versión de la fuente si existe; conservar cancelaciones que llegan
antes que la reserva). Queda decidir qué pasa cuando una novedad del proveedor choca con lo que el usuario hizo a
mano sobre la misma reserva (RF-04): si la editó o si la borró.

## Decision Drivers

* RF-04 Gestión manual: el usuario puede agregar, editar y eliminar sus reservas.
* QA-6: procesar el 99,9 % de los mensajes válidos sin pérdida ni duplicación.
* El panel debe reflejar la realidad del proveedor (por ejemplo, un vuelo cancelado debe verse cancelado) sin perder
  lo que el usuario anotó.

## Considered Options

* A. Dueño por campo: el proveedor define sus datos y el usuario los suyos; se avisa si se pisa una edición
* B. Gana siempre el proveedor
* C. Gana siempre el usuario
* D. Cada conflicto queda pendiente hasta que el usuario decida

## Decision Outcome

Chosen option: "A. Dueño por campo", because el panel muestra la realidad del proveedor sin perder lo que el usuario
anotó, y la mayoría de los conflictos tienen una respuesta obvia según de quién es el dato.

**Edición:**

| Campo de la reserva | Dueño | Ante una novedad externa |
|---|---|---|
| Fechas y horarios, estado (confirmada, modificada, cancelada), código, proveedor, ubicación | Proveedor | Se aplica la novedad. Si el usuario había editado ese campo, se agrega un aviso al panel ("el hotel cambió la fecha que habías modificado") con relevancia alta (ADR-0046) |
| Nombre visible, notas, viaje asignado | Usuario | Se conserva el valor del usuario |

* Cada reserva registra qué campos editó el usuario, para poder avisar.
* Los avisos quedan en la lista `notices` del panel durante 7 días (suposición) y se leen por la API.

**Borrado:**

* Si el usuario elimina una reserva que vino de un proveedor, el núcleo guarda una **marca de borrado** con la
  identidad de la reserva (vinculación, proveedor y referencia externa).
* Las novedades posteriores sobre esa reserva no la vuelven a crear: se registran como descartadas por decisión del
  usuario, y el control de entrada las confirma para que no se reintenten.
* La marca se elimina junto con el resto de los datos del viaje (ADR-0045), o antes si el usuario vuelve a agregar
  esa reserva a mano.

**Común:**

* Una reserva creada a mano (sin referencia de proveedor) no recibe novedades hasta que una novedad con datos
  suficientes se concilie con ella, según la política de la iteración 2 (caso pendiente si hay ambigüedad).
* Todo se aplica en una transacción local de la partición del usuario: control de entrada de la novedad, cambio,
  panel (ADR-0040), y eventos en la outbox (ADR-0027, ADR-0046).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Idempotent Receiver* (iteración 2) | El control de entrada evita aplicar dos veces la misma novedad, incluidas las descartadas por borrado | QA-6 |
| Patrón *Transactional Outbox* (ADR-0027) | Cambio y eventos confirmados juntos | QA-6 |
| Marca de borrado (*tombstone*) | Recordar que el usuario eliminó una reserva para no recrearla | RF-04 |

Las reglas viven solo en el módulo `reservas` del núcleo.

### Consequences

* Good, because el panel refleja la realidad del proveedor y respeta las anotaciones del usuario.
* Good, because una reserva que el usuario borró no reaparece.
* Bad, because hay que registrar qué campos editó el usuario y guardar marcas de borrado.
* Bad, because si el usuario borra por error una reserva de proveedor, sus cambios posteriores (por ejemplo, una
  cancelación) ya no se ven; tiene que volver a agregarla a mano.

### Confirmation

Pruebas: una novedad de cancelación sobre una reserva editada a mano deja la reserva cancelada, conserva las notas y
agrega el aviso; una novedad sobre una reserva borrada no la recrea y no se reintenta; reentregar la misma novedad no
cambia nada.

## Pros and Cons of the Options

### A. Dueño por campo

* Good, because combina la realidad del proveedor con los datos del usuario.
* Bad, because exige definir y mantener el dueño de cada campo.

### B. Gana el proveedor

* Good, because es simple y siempre refleja al proveedor.
* Bad, because el usuario pierde sus notas y nombres, y una reserva borrada reaparece.

### C. Gana el usuario

* Good, because respeta las ediciones del usuario.
* Bad, because si el vuelo se cancela o cambia de horario, el panel muestra un dato falso.

### D. Decide el usuario

* Good, because nunca se pisa nada.
* Bad, because hasta que responda, el panel muestra información dudosa.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | RF-04, QA-6 |
| Vistas afectadas | [module-view](../02-views/module-view.md), [domain-model](../02-views/domain-model.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml), [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0024](0024-avance-y-publicacion-durable.md), [0027](0027-publicacion-del-nucleo.md), [0040](0040-modelo-de-lectura-del-panel.md), [0046](0046-notificador-de-cambios-del-panel.md), [0048](0048-asignacion-de-reservas-a-viajes.md) |
| Código del prototipo | `prototype/` |
