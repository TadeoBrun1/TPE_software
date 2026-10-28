---
status: "accepted"
date: 2026-10-28
decision-makers: "Tomas Lateana"
consulted: "Revisión de Tadeo Brun y asistencia de IA"
---

# Publicar cambios confirmados mediante outbox transaccional del núcleo

## Context and Problem Statement

Una reserva puede confirmarse por ingesta o por una operación manual. Guardar el estado y publicar al broker son
dos operaciones distintas: una caída entre ambas deja el estado sin evento o un evento de un cambio inexistente.
La transacción pertenece al núcleo; la outbox de ingesta no puede garantizar la publicación de sus cambios.
Esta ADR conserva una decisión separada de ADR-0024 porque el productor, la transacción y los consumidores son distintos.

## Decision Drivers

* ADR-0002: publicar cambios confirmados para consumidores independientes
* QA-6: 99,9 % de mensajes válidos procesados sin pérdida ni duplicación
* CRN-3: recuperación de fallos entre base y broker
* RF-07: alimentar analítica sin acceso directo a tablas del núcleo

## Considered Options

* A. Publicar antes de confirmar la transacción de dominio
* B. Guardar y después publicar sin registro recuperable
* C. Guardar cambio y outbox en la misma transacción local

## Decision Outcome

Chosen option: **C. Guardar cambio y outbox en la misma transacción local**. Al aplicar una novedad, la transacción incluye
control de recepción, resultado de dominio y evento pendiente; las operaciones manuales incluyen cambio y evento.
Un publicador del núcleo envía con identidad estable y marca enviado tras confirmación y ausencia de retorno por
falta de ruta. Si cae antes de marcar envío, republica el mismo evento. El patrón es *Transactional Outbox*;
el control durable de entrada implementa *Idempotent Receiver*. Los consumidores de eventos confirmados también
deduplican antes de confirmar. El evento describe estado ya confirmado, a diferencia de la novedad externa.

### Consequences

* Good, because un commit conserva conjuntamente el cambio y la obligación de publicarlo.
* Bad, because requiere tabla de pendientes, publicador, limpieza y supervisión de antigüedad.
* Bad, because entrega al menos una vez permite duplicados; no asegura efectos únicos en consumidores externos sin su propio control.
* Bad, because no resuelve por sí sola identidad de reserva, orden de negocio ni latencia de extremo a extremo.

### Confirmation

Inyectar caídas antes y después del commit, después de publicar y antes de marcar enviado, y antes del ACK del
consumidor. Comprobar que tanto un cambio manual como uno externo producen un evento recuperable y que la
reentrega no repite el efecto. Verificar que una transacción fallida no deja un evento de cambio confirmado.

## Pros and Cons of the Options

### A. Publicar antes de confirmar la transacción de dominio

* Good, because el broker puede recibir rápidamente.
* Bad, because un rollback posterior deja un evento que afirma un cambio que nunca ocurrió.

### B. Guardar y después publicar sin registro recuperable

* Good, because no agrega almacenamiento de pendientes.
* Bad, because una caída tras el commit y antes del envío pierde la obligación de publicar.

### C. Guardar cambio y outbox en la misma transacción local

* Good, because cambio y obligación de publicación son atómicos en la base del núcleo.
* Bad, because el envío sigue siendo asíncrono y requiere deduplicación y recuperación.

## More Information

[Contrato](../../specs/core-publication.md) · [Outbox de ingesta](0024-avance-y-publicacion-durable.md).

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #4](https://github.com/TadeoBrun1/TPE_software/pull/4),
merge `0801315` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
