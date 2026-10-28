---
status: "accepted"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: ""
informed: "Tomas Lateana"
---

# Priorización y degradación ante sobrecarga

## Context and Problem Statement

Con escalado solo reactivo (ADR-0043), durante los minutos en que arrancan instancias nuevas puede llegar más demanda
de la que el sistema atiende. Además, un cliente puede generar tráfico excesivo en cualquier momento. Hay que decidir
qué pasa con esa demanda.

## Decision Drivers

* QA-2 Latencia web: lo más importante para el viajero es ver su panel.
* QA-4 Disponibilidad: una sobrecarga no debe convertirse en una caída.
* QA-5 Escalabilidad: proteger al núcleo mientras se agrega capacidad.

## Considered Options

* A. Limitar por cliente, priorizar la lectura del panel y rechazar lo demás con reintento
* B. Solo limitar por cliente, sin distinguir operaciones
* C. Encolar todas las solicitudes hasta que haya capacidad

## Decision Outcome

Chosen option: "A. Limitar, priorizar y degradar", because protege lo más importante para el viajero durante la
sobrecarga y evita que el núcleo se sature.

Reglas (la puerta de entrada las aplica):

| Situación | Respuesta |
|---|---|
| Un cliente supera su límite de solicitudes, haya o no sobrecarga | `429 Too Many Requests` con `Retry-After` |
| Sobrecarga del núcleo: lectura del panel (`GET /panel`) | Prioridad alta: se atiende |
| Sobrecarga del núcleo: cambios manuales (RF-04) | Prioridad media: se atienden si hay lugar; si no, `503 Service Unavailable` con `Retry-After` |
| Sobrecarga del núcleo: operaciones secundarias (viajes anteriores, reactivar o archivar viajes, asistencia) | Prioridad baja: se rechazan primero, con `503` y `Retry-After` |

* **Novedades de la ingesta:** no pasan por la puerta de entrada. El consumo ya está acotado por los 8 consumidores
  activos y su *prefetch* (iteración 2). Durante una sobrecarga el núcleo puede bajar el *prefetch* o pausar el
  consumo; las novedades esperan en el broker. Ese atraso se descuenta de la espera en cola (40 s) y del margen
  compartido (40 s) del presupuesto de QA-1; si los supera, se registra como incumplimiento potencial, no se oculta.
* **App móvil:** mientras tanto muestra su caché local (ADR-0041).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *administrar las solicitudes de trabajo* (performance) | Límite por cliente (`429`) | QA-5 |
| Táctica *priorizar eventos* (performance) | El panel se atiende antes que lo demás | QA-2 |
| Táctica *limitar la respuesta a eventos* (performance) | Se baja o pausa el consumo de novedades | QA-5 |
| Táctica *degradación elegante* (disponibilidad) | Se rechaza lo secundario con reintento; la app muestra su caché | QA-4 |
| Patrones *Rate Limiting* y *Load Shedding* | Puerta de entrada | QA-5 |

### Consequences

* Good, because en el peor momento el viajero sigue viendo su panel.
* Good, because los clientes saben cuándo reintentar (`Retry-After`).
* Bad, because durante la sobrecarga algunas operaciones del usuario fallan y hay que reintentarlas.
* Bad, because QA-1 puede atrasarse para algunas actualizaciones durante un pico fuerte.
* Bad, because si la lectura del panel por sí sola supera la capacidad, la priorización no alcanza y QA-2 se
  incumple hasta que llega la capacidad nueva (ADR-0043).

### Confirmation

Prueba de sobrecarga: las operaciones de baja prioridad reciben `503` antes que las de prioridad media, el panel sigue
respondiendo, y un cliente que excede su límite recibe `429`.

## Pros and Cons of the Options

### A. Limitar, priorizar y degradar

* Good, because protege la operación más importante.
* Bad, because requiere clasificar cada operación y mantener esa clasificación.

### B. Solo limitar

* Good, because es simple y protege al núcleo.
* Bad, because un usuario puede quedarse sin ver su panel justo durante una disrupción.

### C. Encolar todo

* Good, because no rechaza nada.
* Bad, because las consultas del panel superarían los 800 ms mientras esperan (QA-2).

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | QA-2, QA-4, QA-5 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) (respuestas `429` y `503`) |
| ADRs relacionadas | [0004](0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md), [0028](0028-rabbitmq-y-politicas.md), [0041](0041-cache-local-del-panel.md), [0043](0043-escalado-solo-reactivo.md) |
| Código del prototipo | `prototype/` |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #6](https://github.com/TadeoBrun1/TPE_software/pull/6),
merge `54122ee` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
