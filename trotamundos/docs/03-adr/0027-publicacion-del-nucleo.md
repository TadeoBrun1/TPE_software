---
status: "proposed"
date: 2026-10-27
decision-makers: "Tomas Lateana; revisión cruzada pendiente"
consulted: "Asistencia de ChatGPT/Codex"
---

# Publicar cambios confirmados con outbox del núcleo

## Context and Problem Statement

La revisión de la primera iteración delega este problema a la iteración 2. Se conserva al núcleo como único dueño
del estado oficial y se precisa la integración sin cambiar los requisitos del sistema.

## Decision Drivers

ADR-0002, QA-6, CRN-3.

## Considered Options

* Publicar antes de guardar.
* guardar y publicar sin recuperación.
* outbox transaccional.

## Decision Outcome

Opción propuesta: **Outbox en la misma transacción del cambio y control de aplicación**. Detalle, responsabilidades, errores y límites en
[core-publication.md](../../specs/core-publication.md).

### Consequences

No pierde la obligación de publicar tras commit; agrega almacenamiento y reentregas que deben deduplicarse.

### Confirmation

Aplicar los casos futuros del contrato, con simuladores y revisión con el responsable del núcleo. No hay pruebas
ni cumplimiento de calidad demostrados por esta actualización documental.

## Pros and Cons of the Options

### Publicar antes de guardar

Reduce algunas piezas iniciales, pero no satisface por sí sola el límite de responsabilidad o la recuperación requerida; ver contrato para el problema concreto.

### guardar y publicar sin recuperación

Reduce algunas piezas iniciales, pero no satisface por sí sola el límite de responsabilidad o la recuperación requerida; ver contrato para el problema concreto.

### outbox transaccional

Favorece el límite/fiabilidad buscado; introduce coordinación y operación adicionales.

## More Information

[Iteración 2](../01-add/iteration-2-ingestion.md) · [Impactos](../01-add/impact-log.md) ·
[Contrato](../../specs/core-publication.md). El broker se elige en [ADR-0028](0028-rabbitmq-y-politicas.md) y el paso 7 se analiza en la iteración; la ejecución del prototipo sigue pendiente.
