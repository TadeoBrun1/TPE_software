---
status: "proposed"
date: 2026-10-27
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Almacenamiento analítico propio, alimentado por los eventos de dominio

> Reemplaza a [ADR-0003](0003-almacen-analitico-separado.md), que se había creado en la iteración 1. Se trasladó a la
> iteración 4 porque su driver principal (RF-07) pertenece a esa iteración. Queda en estado `proposed` hasta que se
> trabaje la iteración 4.

## Context and Problem Statement

El equipo de datos necesita ejecutar consultas pesadas sobre tendencias, destinos y cancelaciones (RF-07).
ADR-0001 ya separa la analítica como proceso propio; falta decidir **de dónde saca los datos y dónde los guarda**
sin degradar la base que atiende a los viajeros.

## Decision Drivers

* RF-07 Analítica de datos con consultas pesadas.
* QA-4 Disponibilidad y QA-5 Escalabilidad: las consultas pesadas no deben competir con las de los viajeros.
* Los datos analíticos deben incluir los cambios manuales del usuario, no solo los de la ingesta.
* CON-3 (suposición): los datos personales se tratan según la normativa de la región del usuario.

## Considered Options

* A. Réplica de lectura de la base operativa
* B. Almacén propio alimentado por los eventos de dominio (ADR-0002)
* C. Captura de cambios (CDC) sobre la base del núcleo
* D. Carga por lotes nocturna

## Decision Outcome

Chosen option: "B. Almacén propio alimentado por los eventos de dominio", because aísla por completo la carga
analítica, permite un esquema pensado para analizar y reutiliza el flujo de eventos de dominio de ADR-0002.

Tácticas que aplica: *mantener múltiples copias de los datos* (performance) y *usar un intermediario*
(modificabilidad): la analítica no depende del esquema operativo.

Queda para el resto de la iteración 4: el retraso máximo aceptable, la anonimización de datos personales antes de
agregarlos entre regiones, los permisos de acceso del equipo de datos y la conservación de los datos.

### Consequences

* Good, because la analítica no comparte recursos con los viajeros.
* Good, because recibe todos los cambios confirmados, también los manuales.
* Bad, because hay otra copia de los datos y cierto retraso, que todavía no tiene un límite acordado.
* Bad, because los datos analíticos pueden contener datos personales y quedar sujetos a CON-3.

### Confirmation

En el prototipo, una consulta analítica pesada no cambia la latencia de la consulta de itinerarios, y cada cambio
confirmado, incluidos los manuales, aparece en el almacén analítico.

## Pros and Cons of the Options

### A. Réplica de lectura de la base operativa

* Good, because es la más barata.
* Bad, because comparte el motor y el esquema operativos: el esquema no sirve para analizar y la replicación puede
  atrasarse bajo carga.

### B. Almacén propio alimentado por los eventos de dominio

* Good, because aísla la carga y permite un esquema analítico.
* Bad, because agrega retraso y otra copia de los datos.

### C. Captura de cambios (CDC) sobre la base del núcleo

* Good, because capta todos los cambios sin tocar el código del núcleo.
* Bad, because acopla la analítica al esquema operativo y a la herramienta de base de datos.

### D. Carga por lotes nocturna

* Good, because es la más simple.
* Bad, because los datos llegan con un día de atraso, lo que no sirve para analizar disrupciones en curso.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 4, [iteration-4-security-evolvability](../01-add/iteration-4-security-evolvability.md) |
| Drivers | RF-07, QA-4, QA-5, CON-3 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md), [deployment-view](../02-views/deployment-view.md) |
| Specs | `specs/asyncapi/` |
| ADRs relacionadas | Reemplaza a [0003](0003-almacen-analitico-separado.md); depende de [0001](0001-nucleo-modular-con-procesos-separados.md) y [0002](0002-mensajeria-persistente-con-publicacion-suscripcion.md) |
| Código del prototipo | `prototype/` |
