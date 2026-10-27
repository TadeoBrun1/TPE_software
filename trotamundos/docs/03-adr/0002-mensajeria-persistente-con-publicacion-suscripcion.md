---
status: "proposed"
date: 2026-10-27
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Comunicación asincrónica mediante un intermediario de mensajes con publicación y suscripción

## Context and Problem Statement

ADR-0001 separa la ingesta y la analítica del núcleo. La ingesta trae información de correos y proveedores, pero
solo el núcleo puede modificar el estado oficial de viajes y reservas; y los consumidores como la analítica
necesitan enterarse de todos los cambios confirmados, incluidos los manuales. Hay que decidir cómo se comunican
estos procesos sin que la caída o la lentitud de uno arrastre a los otros.

## Decision Drivers

* QA-4 Disponibilidad: la caída de la ingesta, del núcleo o de un consumidor no debe arrastrar a los demás.
* QA-1 Frescura: las novedades tienen que llegar al núcleo dentro de los 5 minutos, aunque la ingesta y el núcleo
  trabajen a ritmos distintos.
* QA-9 Evolucionabilidad: agregar un productor (un medio de transporte nuevo) o un consumidor nuevo no debe obligar
  a cambiar los existentes.
* CON-2: los sistemas externos tienen ráfagas, demoras y caídas que no controlamos; el núcleo no debe recibirlas
  directamente.

## Considered Options

* A. Llamada síncrona de la ingesta a una API del núcleo
* B. Cola punto a punto entre ingesta y núcleo (cada mensaje tiene un único consumidor)
* C. Intermediario de mensajes persistente con publicación y suscripción
* D. La ingesta escribe directamente en la base del núcleo

## Decision Outcome

Chosen option: "C. Intermediario de mensajes persistente con publicación y suscripción", because desacopla la
disponibilidad y el ritmo de cada proceso, conserva los mensajes mientras un consumidor está caído y permite sumar
consumidores sin modificar a quien publica.

Se definen dos flujos (temas):

1. **Novedades de reservas** (ingesta → núcleo): la ingesta publica la reserva ya traducida al modelo canónico; el
   núcleo valida, decide a qué viaje pertenece y aplica el cambio.
2. **Eventos de dominio** (núcleo → consumidores): el núcleo publica cada cambio confirmado, venga de la ingesta o de
   una acción manual del usuario. La analítica es el primer consumidor.

El formato de los mensajes de ambos flujos se define como contrato en `specs/asyncapi/` y lleva versión de esquema.

Patrones y tácticas que aplica:

| Patrón o táctica (Bass) | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Publish-Subscribe* | Los productores publican en un tema sin conocer a los consumidores | QA-9 |
| Táctica *usar un intermediario* (modificabilidad e integrabilidad) | El broker separa a productores y consumidores | QA-9, QA-4 |
| Táctica *limitar el tamaño de las colas* / amortiguar la demanda (performance) | Las ráfagas de los proveedores se acumulan en el broker y el núcleo las consume a su ritmo | QA-1, CON-2 |
| Táctica *redundancia* del intermediario (disponibilidad) | El broker se despliega replicado entre zonas (ADR-0004) | QA-4 |

### Qué no decide esta ADR

Lo siguiente es detalle de tácticas que corresponden a drivers de la iteración 2 (QA-6 sin pérdida ni duplicación,
QA-8 seguridad de correos). Queda registrado en el [registro de impactos](../01-add/impact-log.md):

* Cómo se garantiza que un mensaje repetido no cree dos reservas (idempotencia y su clave). La clave no puede
  depender de una "versión" del proveedor, porque un correo no la trae.
* Cómo se tratan los mensajes que llegan desordenados desde la fuente (por ejemplo, una cancelación antes del alta).
  El orden del broker no lo resuelve, porque solo preserva el orden en que se publica.
* Cómo se garantiza que un cambio confirmado en el núcleo se publique siempre (por ejemplo, *outbox*).
* Qué pasa con los mensajes que fallan repetidamente (cola de errores).
* Qué datos personales pueden viajar en un mensaje.
* La tecnología concreta del broker.

### Consequences

* Good, because la ingesta y el núcleo trabajan a ritmos distintos y se recuperan solos tras una caída: los
  mensajes esperan en el broker.
* Good, because un consumidor nuevo (analítica, notificaciones, una futura recomendación) se suscribe sin tocar el
  núcleo.
* Bad, because un broker persistente entrega "al menos una vez": los consumidores tienen que tolerar mensajes
  repetidos (se diseña en la iteración 2).
* Bad, because es un componente más que operar, replicar y proteger.
* Bad, because el tiempo que un mensaje pasa en el broker consume parte de los 5 minutos de QA-1 y hay que medirlo.

### Confirmation

* Contrato de ambos flujos en `specs/asyncapi/`, revisado por los dos integrantes.
* Prueba en el prototipo: con el núcleo detenido, la ingesta sigue publicando; al levantar el núcleo, procesa los
  mensajes pendientes.

## Pros and Cons of the Options

### A. Llamada síncrona a una API del núcleo

* Good, because no agrega componentes y el resultado se conoce en el momento.
* Bad, because si el núcleo está caído o lento, la ingesta se frena o pierde novedades (QA-4, QA-1).
* Bad, because las ráfagas de los proveedores llegan directo al núcleo (CON-2).

### B. Cola punto a punto entre ingesta y núcleo

* Good, because desacopla ingesta y núcleo y amortigua las ráfagas.
* Bad, because cada mensaje tiene un solo consumidor: para avisar de los cambios a la analítica u otros
  consumidores hace falta un segundo mecanismo (QA-9).

### C. Intermediario persistente con publicación y suscripción

* Good, because desacopla, conserva mensajes y admite varios consumidores con un solo mecanismo.
* Bad, because es más complejo de operar que una llamada directa.

### D. Escritura directa en la base del núcleo

* Good, because no requiere mensajería.
* Bad, because la ingesta tendría que conocer y repetir las reglas de negocio del núcleo, y cualquier cambio de
  esquema rompe la ingesta (QA-9).
* Bad, because rompe la regla de que solo el núcleo modifica el estado oficial (ADR-0001).

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 1, [iteration-1-structure](../01-add/iteration-1-structure.md) |
| Drivers | QA-4, QA-1, QA-9, CON-2 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | `specs/asyncapi/` |
| ADRs relacionadas | [0001](0001-nucleo-modular-con-procesos-separados.md), [0004](0004-despliegue-por-regiones-con-region-de-origen.md), [0060](0060-almacen-analitico-separado.md) |
| Código del prototipo | `prototype/` |
