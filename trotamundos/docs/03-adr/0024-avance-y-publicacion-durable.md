---
status: "proposed"
date: 2026-10-27
decision-makers: "Tomas Lateana; revisión cruzada pendiente"
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

Opción propuesta: **Outbox y avance coordinados en almacenamiento durable**. Guardar resultados de la página, casos pendientes, outbox y avance/versionado juntos antes de adelantar la sincronización. Publicar con ID estable y marcar enviado después de confirmación durable. El núcleo aplica efecto idempotente.

Evitar dos confirmaciones concurrentes del mismo cursor usando versión/lease con control al guardar. Si se procesa por página, registrar todos sus elementos antes de avanzar. Reintentar solo fallos transitorios con esperas crecientes/variación; cuota según proveedor; autorización revocada se detiene; datos inválidos a resolución. Fijar límites/retención y vigilar acumulación antes de implementar. No afirmar atomicidad entre fuente, broker y base ni exactly-once.

### Consequences

* Favorable: Permite reanudar y no adelantar avance sin representar sus resultados.
* Desfavorable: Costo transaccional, limpieza, retención y control de concurrencia; no evita reentregas.
* Las comprobaciones de cumplimiento se realizan en el paso 7/prototipo, no se declaran ejecutadas.

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
| Relación con 1/3 | [Impactos](../01-add/impact-log.md); base de 1 publicada en main, revisión de integración pendiente |
| ADR relacionadas | [Índice](README.md), ADR-0020 a 0024 |
| Prototipo | [Alcance](../../prototype/README.md); implementación pendiente |

### Integración con la primera iteración publicada

ADR-0002 requiere clave proveedor/reserva/versión y orden por reserva; el contrato distingue `eventId`,
`businessChangeKey` y `reservationKey`, con ámbito usuario/región/vinculación. Si la fuente no aporta identidad
o versión confiable, se conserva para resolución. ADR-0004 requiere enrutamiento por `homeRegion` del usuario,
no por su ubicación actual. Queda por elegir broker y probar esas propiedades; no se cambian los ADR de la primera.
