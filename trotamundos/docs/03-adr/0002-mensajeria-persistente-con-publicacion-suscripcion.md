---
status: "proposed"
date: 2026-10-27
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Mensajería persistente con publicación y suscripción entre ingesta, núcleo y consumidores

## Context and Problem Statement

La ingesta obtiene información de correos y proveedores, pero solo el núcleo debe modificar el estado oficial de
viajes y reservas. Además, la analítica necesita conocer todos los cambios confirmados, incluidos los manuales. Hay
que decidir cómo se comunican estos elementos sin acoplar su disponibilidad ni perder o duplicar reservas.

## Decision Drivers

* QA-1 Frescura: el recorrido completo debe respetar los 5 minutos.
* QA-6 Interoperabilidad (se detalla en la iteración 2): 99,9 % de los mensajes válidos sin pérdida ni duplicación.
* QA-4 Disponibilidad: la caída de un elemento no debe arrastrar a los demás.
* QA-8 Seguridad (se detalla en la iteración 2): los mensajes no deben exponer credenciales ni correos completos.
* QA-9 Evolucionabilidad: el formato debe poder cambiar sin romper consumidores.

## Considered Options

* A. Llamada síncrona de la ingesta a una API del núcleo
* B. Cola punto a punto solo para la ingesta
* C. Mensajería persistente con publicación y suscripción, con dos flujos
* D. La ingesta escribe directamente en la base del núcleo

## Decision Outcome

Chosen option: "C. Mensajería persistente con publicación y suscripción, con dos flujos", because desacopla ritmos y
fallas, conserva los mensajes pendientes y alimenta con el mismo mecanismo a la analítica.

Los dos flujos son:

1. **Novedades de ingesta** (ingesta → núcleo). La ingesta normaliza los datos externos; el núcleo valida, decide a
   qué viaje corresponde y aplica el cambio. Si faltan datos, el caso queda pendiente de resolución.
2. **Eventos de dominio** (núcleo → consumidores). El núcleo publica cada cambio confirmado, venga de la ingesta o de
   una acción manual del usuario.

Reglas: entrega al menos una vez; consumidores idempotentes con clave proveedor + código de reserva + versión;
orden por reserva; los mensajes fallidos van a una cola de errores y no se descartan; el núcleo guarda el cambio y el
evento en la misma transacción (*outbox*); los mensajes no llevan contraseñas, tokens ni cuerpos completos de correo;
cada mensaje lleva versión de esquema.

### Consequences

* Good, because la ingesta y el núcleo trabajan a ritmos distintos y se recuperan solos tras una caída.
* Good, because un solo mecanismo alimenta al núcleo y a la analítica.
* Bad, because los mensajes pueden retrasarse o repetirse, y hay que diseñar la idempotencia y el orden.
* Bad, because hay un componente más que operar y proteger; hay que controlar el tiempo total contra los 5 minutos.

### Confirmation

Pruebas en el prototipo: enviar el mismo mensaje dos veces no crea dos reservas; una cancelación que llega antes que
el alta termina aplicada; con el núcleo detenido, los mensajes se procesan al volver. Contrato en `specs/asyncapi/`.

## Pros and Cons of the Options

### A. Llamada síncrona a una API del núcleo

* Good, because es la más simple de operar.
* Bad, because acopla la disponibilidad y la capacidad de ambos (QA-4, QA-1).
* Bad, because no resuelve cómo alimentar a la analítica.

### B. Cola punto a punto solo para la ingesta

* Good, because desacopla ingesta y núcleo.
* Bad, because la analítica necesitaría otro camino para recibir los cambios.

### C. Mensajería persistente con publicación y suscripción, con dos flujos

* Good, because cumple desacople, durabilidad y reutilización de eventos.
* Bad, because es más compleja que A y B.

### D. Escritura directa en la base del núcleo

* Good, because no requiere mensajería.
* Bad, because duplica reglas de negocio y acopla los esquemas (QA-9).

## More Information

La tecnología concreta del broker se decide en la iteración 2 (y queda en una ADR propia).

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 1, [iteration-1-structure](../01-add/iteration-1-structure.md) |
| Drivers | QA-1, QA-6, QA-4, QA-8, QA-9, CON-2 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | `specs/asyncapi/` |
| ADRs relacionadas | [0001](0001-nucleo-modular-con-procesos-separados.md), [0003](0003-almacen-analitico-separado.md) |
| Código del prototipo | `prototype/` |
