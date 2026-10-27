---
status: "proposed"
date: 2026-10-27
decision-makers: "Tomas Lateana; revisión cruzada pendiente"
consulted: "Asistencia de ChatGPT/Codex"
---

# Resolver región y recibir avisos mediante entrada global y Gateway

## Context and Problem Statement

La revisión de la primera iteración delega este problema a la iteración 2. Se conserva al núcleo como único dueño
del estado oficial y se precisa la integración sin cambiar los requisitos del sistema.

## Decision Drivers

QA-6, QA-10, ADR-0003/0004.

## Considered Options

* Aviso directo a ingesta.
* difusión a todas las regiones.
* directorio mínimo por suscripción.

## Decision Outcome

Opción propuesta: **Directorio mínimo por suscripción con origen verificable**. Detalle, responsabilidades, errores y límites en
[notification-routing.md](../../specs/notification-routing.md).

### Consequences

Evita exponer ingesta y permite ubicar la región; agrega metadata sensible y dependencia del directorio.

### Confirmation

Aplicar los casos futuros del contrato, con simuladores y revisión con el responsable del núcleo. No hay pruebas
ni cumplimiento de calidad demostrados por esta actualización documental.

## Pros and Cons of the Options

### Aviso directo a ingesta

Reduce algunas piezas iniciales, pero no satisface por sí sola el límite de responsabilidad o la recuperación requerida; ver contrato para el problema concreto.

### difusión a todas las regiones

Reduce algunas piezas iniciales, pero no satisface por sí sola el límite de responsabilidad o la recuperación requerida; ver contrato para el problema concreto.

### directorio mínimo por suscripción

Favorece el límite/fiabilidad buscado; introduce coordinación y operación adicionales.

## More Information

[Iteración 2](../01-add/iteration-2-ingestion.md) · [Impactos](../01-add/impact-log.md) ·
[Contrato](../../specs/notification-routing.md). El broker concreto y la validación del paso 7 permanecen pendientes.
