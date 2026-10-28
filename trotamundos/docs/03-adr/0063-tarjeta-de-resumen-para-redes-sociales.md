---
status: "accepted"
date: 2026-10-28
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
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
* La tarjeta tiene un enlace público propio (`/cards/{cardId}`), con el prefijo de la región del dueño en `cardId`
  para que la entrada global la enrute sin token (ADR-0060). Ese enlace no da acceso al viaje.
* **Excepción a ADR-0004 y ADR-0065, acotada a esta página:** los robots de las redes sociales no ejecutan la
  aplicación web ni tienen sesión, así que necesitan una página HTML con metadatos Open Graph ya armados. El núcleo
  sirve esa única página con una plantilla fija; no es una pantalla de la aplicación. El texto se arma una vez, al
  crear la tarjeta, en el idioma del perfil del dueño (ADR-0065), porque el robot no tiene un idioma propio.
* La tarjeta se borra cuando el usuario la borra o cuando el viaje se elimina (ADR-0045); el enlace deja de
  funcionar. Archivar el viaje no la borra.
* El usuario comparte el enlace con la función de compartir de su teléfono o del navegador; Trotamundos no publica en
  nombre del usuario ni guarda credenciales de redes sociales.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *limitar la exposición* (seguridad) | Solo se publica un resumen sin datos sensibles | QA-7 |
| Táctica *adherir a estándares* (integrabilidad) | Metadatos Open Graph que entienden todas las redes | Interoperabilidad |

### Consequences

* Good, because el itinerario sigue protegido y la publicación funciona en cualquier red.
* Good, because no hay integración por red social ni credenciales que custodiar (CON-2).
* Bad, because lo que se publica es un resumen, no el itinerario.
* Bad, because cualquiera con el enlace ve el destino y el mes: es información que el usuario elige hacer pública, y
  puede indicar cuándo el viajero no está en su casa. La app lo advierte al crear la tarjeta.
* Bad, because el núcleo sirve una página HTML y arma un texto en un idioma, dos excepciones acotadas a ADR-0004 y
  ADR-0065.

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
| ADRs relacionadas | [0004](0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md), [0045](0045-ciclo-de-vida-y-archivado-de-viajes.md), [0060](0060-identidad-por-region-con-tokens.md), [0061](0061-comparticion-con-cuenta-y-auditoria.md), [0065](0065-internacionalizacion-en-el-cliente.md) |
| Código del prototipo | — |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #7](https://github.com/TadeoBrun1/TPE_software/pull/7),
merge `00f21b9` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
