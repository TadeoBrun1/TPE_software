---
status: "accepted"
date: 2026-10-27
decision-makers: "Tomas Lateana"
consulted: "Asistencia de ChatGPT/Codex"
informed: "Revisión cruzada mediante el PR de iteración 2"
---

# Coordinar cursores, resultados y outbox con reintentos controlados

## Context and Problem Statement

Avanzar el cursor antes de conservar/publicar resultados puede saltar novedades. Publicar y marcar enviado son operaciones separadas: una caída entre ambas produce reentregas.

## Decision Drivers

* QA-1: retraso de actualización
* QA-6: pérdida/duplicación
* CRN-3: recuperación
* CRN-4: protección de datos pendientes

## Considered Options

* Avanzar cursor y después publicar sin registro recuperable
* Releer siempre toda la fuente y publicar directamente
* Outbox y avance coordinados en almacenamiento durable

## Decision Outcome

Chosen option: **Outbox y avance coordinados en almacenamiento durable**. Guardar resultados de la página, casos pendientes, outbox y avance/versionado juntos antes de adelantar la sincronización. Publicar con ID estable y marcar enviado después de confirmación durable. El núcleo aplica efecto idempotente.

Evitar dos confirmaciones concurrentes del mismo cursor usando versión/lease con control al guardar. Si se procesa por página, registrar todos sus elementos antes de avanzar. Reintentar solo fallos transitorios con esperas crecientes/variación; cuota según proveedor; autorización revocada se detiene; datos inválidos a resolución. Fijar límites/retención y vigilar acumulación antes de implementar. No afirmar atomicidad entre fuente, broker y base ni exactly-once.

### Patrones y tácticas

* Patrón o mecanismo: Transactional Outbox e Idempotent Receiver.
* Tácticas: Retry y Exception handling: reintentar fallos temporales y clasificar resultados.

### Consequences

* Favorable: Permite reanudar y no adelantar avance sin representar sus resultados.
* Desfavorable: Costo transaccional, limpieza, retención y control de concurrencia; no evita reentregas.

### Confirmation

Inyectar fallos antes/después de guardar avance/outbox, después de recibir confirmación del canal y durante aplicación. Reobtener páginas y reentregar mensajes sin perder novedades ni duplicar efectos; medir recuperación dentro del presupuesto cuando sea viable.

## Pros and Cons of the Options

### Avanzar cursor y después publicar sin registro recuperable

* A favor: Menos persistencia.
* En contra: Una caída puede perder novedades definitivamente.

### Releer siempre toda la fuente y publicar directamente

* A favor: No necesita cursor persistente sencillo.
* En contra: Carga y cuotas excesivas; no resuelve por sí sola duplicación ni fuentes con retención.

### Outbox y avance coordinados en almacenamiento durable

* A favor: Permite reanudar y no adelantar avance sin representar sus resultados.
* En contra: Costo transaccional, limpieza, retención y control de concurrencia; no evita reentregas.

## More Information

| Elemento | Enlace |
|---|---|
| Iteración | [2 — Ingesta](../01-add/iteration-2-ingestion.md) |
| Drivers | [Requisitos y escenarios](../00-requirements/architectural-drivers.md) |
| Vistas | [Ingesta](../02-views/ingestion-view.md), [secuencias](../02-views/ingestion-sequences.md) |
| Contrato | [Semántica](../../specs/ingestion-contract.md), [AsyncAPI](../../specs/asyncapi/booking-change-detected.v1.yaml) |
| Relación con 1/3 | [Impactos](../01-add/impact-log.md); base integrada y coordinada mediante PRs #3, #4, #6 y #7; validación de implementación pendiente |
| ADR relacionadas | [Índice](README.md), ADR-0020 a 0024 |
| Prototipo | [Alcance](../../prototype/README.md); implementación pendiente |

### Integración con la primera iteración revisada

ADR-0002 delega idempotencia/orden a esta iteración. `eventId` reconoce reentregas; `businessChangeKey` identifica
novedades por referencia estable de fuente o huella acordada, sin exigir una versión externa a todos los correos.
`reservationKey` identifica la reserva dentro de su ámbito. El núcleo no aplica ciegamente cambios contradictorios
sin orden confiable. ADR-0003 define la región; ADR-0004, la puerta de entrada.

Esta outbox es la de ingesta; la publicación transaccional del núcleo se documenta aparte en
[ADR-0027](0027-publicacion-del-nucleo.md). RabbitMQ y sus políticas se definen en [ADR-0028](0028-rabbitmq-y-politicas.md); las pruebas del prototipo siguen pendientes.

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #4](https://github.com/TadeoBrun1/TPE_software/pull/4),
merge `0801315` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
