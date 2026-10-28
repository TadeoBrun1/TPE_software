---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (revisión cruzada en el PR de la iteración 4)"
informed: ""
---

# Tarjeta de resumen pública para compartir en redes sociales

## Context and Problem Statement

El enunciado pide que el sistema interopere "con redes sociales para compartir itinerarios", y a la vez que el uso
compartido asegure que "solo personas específicas designadas puedan visualizarlos" (QA-7). Publicar un itinerario en
una red social lo hace visible para cualquiera. Hay que decidir qué se publica.

## Decision Drivers

* QA-7: solo las personas designadas ven el itinerario.
* Interoperabilidad con redes sociales (enunciado).
* CON-2: las redes sociales son sistemas externos que no controlamos.

## Considered Options

* A. Tarjeta de resumen pública, con datos no sensibles, que no da acceso al itinerario
* B. Publicar una invitación: quien la abre pide acceso y el dueño lo acepta
* C. Publicar un enlace al itinerario completo

## Decision Outcome

Chosen option: "A. Tarjeta de resumen", because interopera con las redes (se ve como una publicación normal, con
imagen y texto) sin exponer el itinerario, que sigue protegido por ADR-0061.

Reglas:

* A pedido del usuario (`POST /trips/{tripId}/social-card`), el núcleo genera una tarjeta con: destino (ciudad o
  país), mes y cantidad de días. Nunca incluye vuelos, hoteles, horarios, direcciones ni códigos de reserva.
* La tarjeta tiene un enlace público propio (`/cards/{cardId}`) con metadatos estándar para que las redes muestren la
  vista previa (Open Graph). Ese enlace no da acceso al viaje.
* El usuario comparte el enlace con la función de compartir de su teléfono o del navegador; Trotamundos no publica en
  nombre del usuario ni guarda credenciales de redes sociales.
* El usuario puede borrar la tarjeta; el enlace deja de funcionar.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *limitar la exposición* (seguridad) | Solo se publica un resumen sin datos sensibles | QA-7 |
| Táctica *adherir a estándares* (integrabilidad) | Metadatos Open Graph que entienden todas las redes | Interoperabilidad |

### Consequences

* Good, because el itinerario sigue protegido y la publicación funciona en cualquier red.
* Good, because no hay integración por red social ni credenciales que custodiar (CON-2).
* Bad, because lo que se publica es un resumen, no el itinerario.
* Bad, because cualquiera con el enlace ve el destino y el mes: es información que el usuario elige hacer pública.

### Confirmation

Prueba: la tarjeta generada no contiene datos de reservas; su enlace muestra la vista previa y no permite leer el
viaje; borrarla invalida el enlace.

## Pros and Cons of the Options

### A. Tarjeta de resumen

* Good, because no rompe QA-7.
* Bad, because no comparte el itinerario en sí.

### B. Invitación por redes

* Good, because no expone nada.
* Bad, because no es realmente compartir en la red, y obliga al dueño a aceptar a cada persona.

### C. Itinerario público

* Good, because es lo que suele esperarse de "compartir en redes".
* Bad, because contradice QA-7 y expone datos personales.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 4, [iteration-4-security-evolvability](../01-add/iteration-4-security-evolvability.md) |
| Drivers | QA-7, interoperabilidad con redes sociales, CON-2 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0061](0061-comparticion-con-cuenta-y-auditoria.md) |
| Código del prototipo | — |
