---
status: "proposed"
date: 2026-10-27
decision-makers: "Tomas Lateana; revisión cruzada pendiente"
consulted: "Asistencia de ChatGPT/Codex"
---

# Integrar la agencia preferida mediante adaptador de asistencia

## Context and Problem Statement

La revisión de la primera iteración delega este problema a la iteración 2. Se conserva al núcleo como único dueño
del estado oficial y se precisa la integración sin cambiar los requisitos del sistema.

## Decision Drivers

RF-06, QA-6, CRN-3.

## Considered Options

* Cliente llama agencia.
* núcleo integra proveedor directamente.
* adaptador de ingesta por contrato de asistencia.

## Decision Outcome

Opción propuesta: **Adaptador de asistencia con solicitud autorizada por núcleo y entrega persistente**. Detalle, responsabilidades, errores y límites en
[agency-assistance.md](../../specs/agency-assistance.md).

### Consequences

Conserva reglas/permisos en núcleo y encapsula la API; agrega seguimiento y manejo de resultados inciertos.

### Confirmation

Aplicar los casos futuros del contrato, con simuladores y revisión con el responsable del núcleo. No hay pruebas
ni cumplimiento de calidad demostrados por esta actualización documental.

## Pros and Cons of the Options

### Cliente llama agencia

Reduce algunas piezas iniciales, pero no satisface por sí sola el límite de responsabilidad o la recuperación requerida; ver contrato para el problema concreto.

### núcleo integra proveedor directamente

Reduce algunas piezas iniciales, pero no satisface por sí sola el límite de responsabilidad o la recuperación requerida; ver contrato para el problema concreto.

### adaptador de ingesta por contrato de asistencia

Favorece el límite/fiabilidad buscado; introduce coordinación y operación adicionales.

## More Information

[Iteración 2](../01-add/iteration-2-ingestion.md) · [Impactos](../01-add/impact-log.md) ·
[Contrato](../../specs/agency-assistance.md). El broker se elige en [ADR-0028](0028-rabbitmq-y-politicas.md) y el paso 7 se analiza en la iteración; la ejecución del prototipo sigue pendiente.
