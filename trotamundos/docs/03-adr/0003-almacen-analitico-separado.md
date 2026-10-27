---
status: "proposed"
date: 2026-10-27
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Almacenamiento y procesamiento analíticos separados del operativo

## Context and Problem Statement

El equipo de datos necesita consultas pesadas sobre tendencias, destinos y cancelaciones (RF-07). Ejecutarlas sobre la
base que atiende a los viajeros degradaría la consulta de itinerarios. Hay que decidir cómo aislar esa carga.

## Decision Drivers

* QA-4 Disponibilidad y QA-5 Escalabilidad: las consultas pesadas no deben afectar a los viajeros.
* RF-07 Analítica de datos (se detalla en la iteración 4).
* Los datos analíticos deben incluir los cambios manuales del usuario, no solo los de la ingesta.
* CON-3: los datos personales dependen de la región.

## Considered Options

* A. Réplica de lectura de la misma base
* B. Almacén propio alimentado por los eventos de dominio
* C. Captura de cambios (CDC) sobre la base del núcleo
* D. Carga por lotes nocturna

## Decision Outcome

Chosen option: "B. Almacén propio alimentado por los eventos de dominio", because aísla por completo la carga
analítica y reutiliza el mecanismo de ADR-0002.

En esta iteración solo se fija el límite entre ambos almacenamientos. La transferencia detallada, los permisos, la
conservación y el tratamiento de datos personales se refinan en la iteración 4.

### Consequences

* Good, because la analítica no comparte recursos con los viajeros.
* Good, because recibe todos los cambios confirmados, también los manuales.
* Bad, because hay que mantener otra representación de los datos y aceptar cierto retraso. **Ese retraso todavía no
  tiene un límite acordado.**
* Bad, because los datos analíticos pueden contener datos personales y quedar sujetos a CON-3.

### Confirmation

En el prototipo, una consulta analítica pesada no cambia la disponibilidad ni la latencia de la consulta de itinerarios. Cada cambio
confirmado, incluidos los manuales, aparece en el almacén analítico.

## Pros and Cons of the Options

### A. Réplica de lectura de la misma base

* Good, because es la más barata.
* Bad, because las consultas pesadas siguen compitiendo con las operativas y el esquema no sirve para analizar.

### B. Almacén propio alimentado por los eventos de dominio

* Good, because aísla la carga y permite un esquema analítico.
* Bad, because agrega retraso y otra copia de los datos.

### C. Captura de cambios (CDC) sobre la base del núcleo

* Good, because capta todos los cambios sin modificar el código del núcleo.
* Bad, because acopla la analítica al esquema operativo y depende de la herramienta de base de datos.
* Neutral, because puede revisarse en la iteración 4 si el outbox resulta costoso.

### D. Carga por lotes nocturna

* Good, because es la más simple.
* Bad, because el retraso es de un día.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 1, [iteration-1-structure](../01-add/iteration-1-structure.md) |
| Drivers | QA-4, QA-5, RF-07, CON-3 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md), [deployment-view](../02-views/deployment-view.md) |
| Specs | `specs/asyncapi/` |
| ADRs relacionadas | [0001](0001-nucleo-modular-con-procesos-separados.md), [0002](0002-mensajeria-persistente-con-publicacion-suscripcion.md) |
| Código del prototipo | `prototype/` |
