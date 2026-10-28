---
status: "accepted"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: ""
informed: "Tomas Lateana"
---

# Archivado diario por partición y eliminación de viajes archivados después de un año

## Context and Problem Statement

RF-05 pide que, cuando un viaje se completa, sus elementos se archiven o eliminen automáticamente de la vista
principal. Hay que decidir cuándo un viaje está completo, qué pasa con él y qué mecanismo lo hace.

## Decision Drivers

* RF-05 Ciclo de vida del viaje, de forma automática.
* QA-2: mantener acotado el documento del panel (ADR-0040).
* CON-3 (suposición): minimizar los datos personales que se guardan.
* QA-5: que el proceso no compita con el tráfico de los viajeros.

## Considered Options

Cuándo y qué:

* A1. Completo a la fecha de su última reserva más 2 días; se archiva y se conserva
* A2. Igual que A1, y los viajes archivados se eliminan después de un plazo
* A3. El usuario marca el viaje como completo

Mecanismo:

* B1. Tarea programada diaria por partición
* B2. Temporizador por viaje (mensaje diferido a la fecha de fin)
* B3. Ocultar los viajes vencidos al armar el panel, sin proceso en segundo plano

## Decision Outcome

Chosen options: "A2. Archivar y eliminar después de un plazo" y "B1. Tarea programada diaria por partición", because
cumple RF-05 sin intervención del usuario, mantiene el panel chico, limita los datos personales guardados y usa las
mismas transacciones que cualquier otro cambio del núcleo.

Reglas:

* Un viaje está **completo** cuando pasó la fecha de su última reserva más **2 días** (margen para demoras y vuelos
  de vuelta tardíos). La fecha de fin sale **de los datos de las reservas**, que vienen de los proveedores o del
  usuario: el sistema no infiere emergencias, demoras climáticas ni cambios de planes que nadie informó.
* Si un proveedor cambia una fecha (por ejemplo, reprograma el vuelo de vuelta), llega una novedad, la reserva cambia
  y el viaje deja de estar completo. Esto ya funciona con ADR-0044 y ADR-0048.
* **Archivar:** el viaje pasa a estado `archivado`, sale de `panel_por_usuario` y queda consultable en "viajes
  anteriores". Si después llega una novedad (por ejemplo, un reembolso), se aplica igual sobre el viaje archivado.
* **Reactivar automáticamente:** si llega una novedad para una reserva de un viaje archivado y sus fechas todavía no
  pasaron (por ejemplo, el hotel extiende la estadía o se emite un vuelo de vuelta nuevo), el viaje vuelve a estar
  activo y reaparece en el panel.
* **Reactivar a mano:** el usuario puede devolver un viaje archivado al panel desde "viajes anteriores", o agregar una
  reserva manual con fecha futura a ese viaje, lo que lo reactiva. Cubre los casos en que ningún proveedor informa el
  cambio (por ejemplo, el usuario queda varado sin que se modifique ninguna reserva, o el proveedor tiene un error).
  Un viaje reactivado a mano guarda una fecha `reactivadoHasta` = fecha de reactivación + **7 días** (suposición). No
  se vuelve a archivar hasta que pasen esa fecha y la de su última reserva más 2 días, lo que ocurra último. El usuario
  también puede archivarlo a mano antes.
* **Eliminar:** los viajes archivados se eliminan definitivamente **1 año** después de archivados, con sus reservas.
  El plazo es una suposición del equipo (el enunciado no lo fija).
* **Mecanismo:** una vez por día, en el horario de menor carga de la región, cada partición busca en lotes los viajes
  completos y los archiva; la misma tarea elimina los archivados vencidos. Cada viaje se procesa en una transacción
  que actualiza el estado, el panel (ADR-0040) y publica en la outbox (ADR-0027) `trip.changed.v1` con el tipo
  `archived` o `deleted` y `panel.changed.v1` (ADR-0046).
* La tarea es idempotente: si se corta a mitad, la siguiente ejecución retoma.
* Los eventos ya enviados a la analítica no se eliminan con el viaje; se anonimizan al entrar a la analítica
  (resuelto en la iteración 4, ADR-0064).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Tarea programada por lotes (*batch job*) | Tarea diaria por partición | RF-05 |
| Táctica *programar recursos* (performance) | Se ejecuta en el horario de menor carga | QA-5 |
| Táctica *reducir la sobrecarga computacional* (performance) | El panel solo contiene viajes activos | QA-2 |
| Táctica *limitar la exposición* (seguridad) | Menos datos personales guardados: eliminación al año | CON-3 |

### Consequences

* Good, because es automático y reversible durante el año de archivo: archivar solo saca el viaje del panel.
* Good, because no depende de que un proveedor externo informe bien todos los cambios: el usuario puede corregirlo.
* Good, because el panel queda chico y la lectura sigue siendo barata.
* Good, because los datos personales no se acumulan indefinidamente.
* Bad, because un viaje puede tardar hasta un día en archivarse después de completarse.
* Bad, because si el usuario sigue de viaje sin que llegue ninguna novedad, el viaje se archiva igual y tiene que
  reactivarlo a mano.
* Bad, because el usuario pierde su historial después de un año.

### Confirmation

Prototipo: con una fecha simulada, la tarea archiva un viaje vencido (sale del panel y publica el evento), no toca
uno activo, y elimina un archivado de más de un año. Ejecutarla dos veces seguidas no produce cambios en la segunda.
Una novedad con fecha futura sobre un viaje archivado lo reactiva; `POST /trips/{tripId}/reactivate` también, y la
tarea no lo vuelve a archivar antes de `reactivadoHasta`.

## Pros and Cons of the Options

### A1. Archivar y conservar

* Good, because el usuario conserva todo su historial.
* Bad, because los datos personales se acumulan sin límite (CON-3).

### A3. Lo marca el usuario

* Good, because nunca se equivoca.
* Bad, because el enunciado pide que sea automático.

### B2. Temporizador por viaje

* Good, because archiva justo a tiempo.
* Bad, because hay que reprogramar el temporizador cada vez que cambian las fechas del viaje, y millones de mensajes
  diferidos ocupan el broker.

### B3. Ocultar al leer

* Good, because no necesita procesos en segundo plano.
* Bad, because el documento del panel crece sin límite y la lectura deja de ser trivial (QA-2); además nunca se
  eliminan datos.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | RF-05, QA-2, QA-5, CON-3 |
| Vistas afectadas | [module-view](../02-views/module-view.md), [domain-model](../02-views/domain-model.md) |
| Specs | [trip-changed.v1.yaml](../../specs/asyncapi/trip-changed.v1.yaml) |
| ADRs relacionadas | [0027](0027-publicacion-del-nucleo.md), [0046](0046-notificador-de-cambios-del-panel.md), [0048](0048-asignacion-de-reservas-a-viajes.md), [0040](0040-modelo-de-lectura-del-panel.md), [0042](0042-particion-de-la-base-por-usuario.md) |
| Código del prototipo | `prototype/` |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #6](https://github.com/TadeoBrun1/TPE_software/pull/6),
merge `54122ee` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
