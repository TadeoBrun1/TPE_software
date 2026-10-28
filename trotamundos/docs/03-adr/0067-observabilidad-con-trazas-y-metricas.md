---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
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
  el cambio y recorre la cadena de QA-1: `booking.change.detected.v1` → transacción del núcleo →
  `panel.changed.v1` (campo `correlationIds`, una lista, porque un cambio del panel puede juntar varias novedades)
  → evento SSE `panel-changed` (mismo campo) → la app. `booking.changed.v1` no está en esa cadena: no tiene
  consumidores. Todos los mensajes llevan además el contexto de traza estándar (`traceparent`) en sus encabezados
  AMQP, declarado en sus AsyncAPI, y las solicitudes HTTP lo llevan en el encabezado HTTP.
* **Métricas por etapa de QA-1:** detección, extracción, publicación, espera en cola, aplicación y aviso al cliente,
  con los límites de `specs/ingestion-operations.md`. Para cerrar la medición de punta a punta, la app informa cuándo
  mostró la versión nueva con `POST /telemetry/panel-shown` (versión del panel, `correlationIds` e instante), una
  operación de prioridad baja que se puede rechazar con 503 ante sobrecarga, con reintento del cliente. Un 202
  confirma recepción durable: no se descarta un reporte aceptado. Las pérdidas se cuentan en la cobertura.
* **Métricas de QA-4:** separar proporción de solicitudes exitosas de segundos de indisponibilidad. Sondas
  independientes cada 5 s recorren entrada, puerta, núcleo y base por región y partición, aun sin tráfico real.
  Registrar intervalos, cobertura y fallos parciales; unir intervalos solapados antes de comparar con 300 s/mes.
  Conmutaciones y tiempo con una sola copia se observan adicionalmente (ADR-0042).
* **Logs estructurados:** sin emails, nombres, códigos de reserva ni tokens; solo identificadores internos.
* **Colector por región:** cada región guarda sus trazas, métricas y logs (CON-3). Las alertas (por ejemplo, la
  antigüedad de la cola de más de 40 s, una conmutación, o un aumento de rechazos en la auditoría de ADR-0061) se
  envían al equipo de operación.
* **Muestreo:** para conservar trazas con error o lentas y 10 % de las normales, seleccionar al final (tail sampling),
  dimensionar su ventana y contar trazas incompletas. No se promete recuperar spans ya descartados al inicio.
  Las métricas de disponibilidad y cobertura no se muestrean.
* **Cobertura de QA-1:** contar actualizaciones esperadas, reportadas, lentas y desconocidas. Telemetría perdida en
  sobrecarga no se considera éxito; declarar desfase de reloj del cliente y ausencia de occurredAt externo. El
  percentil de los reportes recibidos no demuestra el del conjunto si faltan muestras sesgadas por carga.

El protocolo y las pruebas están en [quality-measurement.md](../../specs/quality-measurement.md).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *monitor* (disponibilidad) | Métricas, trazas y alertas de disponibilidad, conmutaciones y tiempos por etapa | QA-4, QA-1, CRN-2 |
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
`correlationId`; el cliente de prueba recibe el `panel-changed` con ese identificador y lo informa en
`POST /telemetry/panel-shown`; las métricas por etapa muestran el tiempo de cada una. Agregar caída sin tráfico,
solapamiento de incidentes, 503 de telemetría, reentrega del reporte y desfase del reloj del cliente.

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
| Specs | [ingestion-operations.md](../../specs/ingestion-operations.md), [panel-changed.v1.yaml](../../specs/asyncapi/panel-changed.v1.yaml), [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0024](0024-avance-y-publicacion-durable.md), [0027](0027-publicacion-del-nucleo.md), [0042](0042-particion-de-la-base-por-usuario.md), [0046](0046-notificador-de-cambios-del-panel.md) |
| Código del prototipo | `prototype/` |
