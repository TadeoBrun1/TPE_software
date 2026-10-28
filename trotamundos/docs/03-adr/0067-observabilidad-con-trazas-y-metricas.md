---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (revisión cruzada en el PR de la iteración 4)"
informed: ""
---

# Observabilidad con trazas distribuidas, métricas por etapa y logs estructurados

## Context and Problem Statement

CRN-2 pide registro de eventos, monitoreo y trazas. Sin eso no se pueden verificar dos drivers centrales: QA-1 (5
minutos desde que el proveedor genera el cambio hasta que se ve en la app, pasando por ingesta, broker, núcleo,
notificador y cliente) y QA-4 (máximo 5 minutos de inactividad por mes). Hay que decidir cómo se observa el sistema.

## Decision Drivers

* CRN-2: logs, monitoreo y trazas.
* QA-1: medir el recorrido completo y cada etapa del presupuesto de 300 s.
* QA-4: medir la inactividad y detectar fallas.
* CON-3: los logs no deben llevar datos personales fuera de su región.

## Considered Options

* A. Trazas distribuidas con un identificador de correlación, métricas por etapa y logs estructurados, con un estándar
  abierto (OpenTelemetry) y un colector por región
* B. Métricas y logs por proceso, sin trazas que crucen procesos
* C. Las herramientas de monitoreo del proveedor de nube

## Decision Outcome

Chosen option: "A. Trazas, métricas y logs con OpenTelemetry", because es la única opción que sigue un cambio a
través del broker y permite medir cada etapa del presupuesto de QA-1, y no ata el diseño a un proveedor.

Reglas:

* **Correlación:** el `correlationId` que ya existe en los eventos (iteración 2) se genera cuando la ingesta detecta
  el cambio y viaja por `booking.change.detected.v1`, la transacción del núcleo, `booking.changed.v1` y
  `panel.changed.v1`. Las solicitudes HTTP llevan el contexto de traza estándar (`traceparent`).
* **Métricas por etapa de QA-1:** detección, extracción, publicación, espera en cola, aplicación y aviso al cliente,
  con los límites de `specs/ingestion-operations.md`. La app informa cuándo mostró la versión nueva, para cerrar la
  medición de punta a punta.
* **Métricas de QA-4:** disponibilidad de la puerta de entrada (solicitudes exitosas sobre totales, por minuto),
  conmutaciones del monitor de base y tiempo con una sola copia (ADR-0042).
* **Logs estructurados:** sin emails, nombres, códigos de reserva ni tokens; solo identificadores internos.
* **Colector por región:** cada región guarda sus trazas, métricas y logs (CON-3). Las alertas (por ejemplo, la
  antigüedad de la cola de más de 40 s o una conmutación) se envían al equipo de operación.
* **Muestreo:** se guardan todas las trazas con error o lentas y una fracción de las normales (suposición: 10 %); las
  métricas no se muestrean.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *monitor* (disponibilidad) | Métricas y alertas de disponibilidad y conmutaciones | QA-4 |
| Táctica *grabar y reproducir* (testeabilidad) | Trazas y logs estructurados que permiten reconstruir cada recorrido | QA-1, CRN-2 |
| Patrón *Distributed Tracing* con identificador de correlación | `correlationId` y `traceparent` de punta a punta | QA-1 |
| Táctica *adherir a estándares* (integrabilidad) | OpenTelemetry | CRN-2 |

### Consequences

* Good, because se puede medir QA-1 por etapa y encontrar dónde se pierde tiempo.
* Good, because la disponibilidad de QA-4 se mide con datos y no se supone.
* Good, because no depende de un proveedor de nube.
* Bad, because cada proceso tiene que propagar el contexto, incluido a través del broker.
* Bad, because guardar trazas tiene costo; el muestreo reduce el costo pero pierde detalle de casos normales.

### Confirmation

Prototipo: una novedad simulada genera una traza que recorre ingesta, broker, núcleo y notificador con el mismo
`correlationId`, y las métricas por etapa muestran el tiempo de cada una.

## Pros and Cons of the Options

### A. Trazas, métricas y logs

* Good, because cubre QA-1 de punta a punta y es independiente del proveedor.
* Bad, because exige propagar contexto en todos los procesos.

### B. Métricas y logs por proceso

* Good, because es más simple.
* Bad, because no permite medir el recorrido completo de QA-1.

### C. Herramientas del proveedor de nube

* Good, because requiere poco trabajo.
* Bad, because ata el diseño a un proveedor y no sigue los mensajes a través del broker.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 4, [iteration-4-security-evolvability](../01-add/iteration-4-security-evolvability.md) |
| Drivers | CRN-2, QA-1, QA-4, CON-3 |
| Vistas afectadas | [deployment-view](../02-views/deployment-view.md), [cc-view](../02-views/cc-view.md) |
| Specs | [ingestion-operations.md](../../specs/ingestion-operations.md) |
| ADRs relacionadas | [0024](0024-avance-y-publicacion-durable.md), [0027](0027-publicacion-del-nucleo.md), [0042](0042-particion-de-la-base-por-usuario.md), [0046](0046-notificador-de-cambios-del-panel.md) |
| Código del prototipo | `prototype/` |
