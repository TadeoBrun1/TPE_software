---
status: "proposed"
date: 2026-10-28
decision-makers: "Tomas Lateana; revisión cruzada pendiente en PR #4"
consulted: "Revisión de Tadeo Brun y asistencia de ChatGPT/Codex"
---

# Integrar asistencia mediante un módulo saliente del núcleo

## Context and Problem Statement

RF-06 requiere resolver problemas con la agencia preferida. La solicitud la inicia un usuario y comparte datos
sujetos a permisos por viaje. Es una operación saliente, distinta de obtener novedades de reservas. Colocarla en
la ingesta entrante de ADR-0001 mezclaría responsabilidades. La latencia de la agencia tampoco debe bloquear
los hilos que responden consultas del núcleo.

## Decision Drivers

* RF-06: asistencia con la agencia preferida
* QA-6 y QA-9: contratos externos y evolución de adaptadores
* CRN-3: fallos, reintentos y resultado incierto
* ADR-0001: núcleo modular e ingesta entrante separada

## Considered Options

* A. Cliente se comunica directamente con la agencia
* B. Adaptador saliente dentro de la ingesta
* C. Módulo de asistencia saliente del núcleo con trabajo asíncrono
* D. Proceso independiente de integraciones salientes

## Decision Outcome

Chosen option: **C. Módulo de asistencia saliente del núcleo con trabajo asíncrono**. El núcleo autoriza el viaje y guarda la
solicitud y su publicación pendiente en una transacción. Un trabajador del módulo `asistencia`, dentro del mismo
desplegable del núcleo, consume trabajo persistente mediante un adaptador específico de agencia. Usa un conjunto
acotado de trabajadores y conexiones, independiente de la atención HTTP, con timeout y reintentos por categoría.
El dominio invoca un puerto de asistencia; el adaptador conoce la API externa. Los resultados vuelven por el
contrato de asistencia y se aplican con control de duplicados. Se usan *Ports and Adapters*, *Transactional Outbox*
y *Idempotent Receiver*, y tácticas *Tailor interface*, *Retry*, *Exception handling* y *Limit access*.
Ingesta no envía asistencia. Un eventual cambio de reserva informado por la agencia entra por el flujo habitual
de novedades. Extraer un proceso saliente se reevaluará si su carga o aislamiento lo justifica.

### Consequences

* Good, because conserva permisos y seguimiento cerca del dominio sin ampliar la responsabilidad de ingesta.
* Good, because una llamada lenta no ocupa el hilo de consulta del viajero.
* Bad, because el trabajador comparte el despliegue y recursos físicos del núcleo: los límites de concurrencia no garantizan aislamiento total.
* Bad, because una respuesta incierta exige consultar estado o revisión antes de repetir una operación no idempotente.

### Confirmation

Verificar solicitud autorizada y rechazada, caída tras envío, respuesta repetida y agencia indisponible. Medir
que el conjunto acotado de trabajadores no degrada la consulta bajo la carga acordada con iteración 3.

## Pros and Cons of the Options

### A. Cliente se comunica directamente con la agencia

* Good, because el servidor no necesita transportar la solicitud.
* Bad, because dispersa permisos, secretos y seguimiento entre clientes y limita la recuperación durable.

### B. Adaptador saliente dentro de la ingesta

* Good, because reutiliza mecanismos de consulta y reintento externos.
* Bad, because mezcla flujo entrante con asistencia saliente y vincula su disponibilidad y despliegue.

### C. Módulo de asistencia saliente del núcleo con trabajo asíncrono

* Good, because mantiene un límite modular y transacciones locales con autorización central.
* Bad, because exige controlar recursos para no competir con la consulta.

### D. Proceso independiente de integraciones salientes

* Good, because permite escalar y aislar físicamente asistencia.
* Bad, because añade despliegue, comunicación y operación sin evidencia actual de una carga que requiera separarlo.

## More Information

[Contrato](../../specs/agency-assistance.md) · [Módulos](../02-views/module-view.md) · [Impactos](../01-add/impact-log.md).
