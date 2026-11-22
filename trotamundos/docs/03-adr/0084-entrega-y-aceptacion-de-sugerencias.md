---
status: "accepted"
date: 2026-11-22
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Sugerencias por una API propia con aviso del notificador, y aceptación como reserva propuesta en el núcleo

## Context and Problem Statement

Una vez calculadas las sugerencias (ADR-0081 a ADR-0083), hay que decidir cómo se entera el viajero, cómo las lee e
interactúa con ellas, y qué pasa cuando acepta una. Trotamundos no compra ni emite reservas (diagrama de contexto),
pero el equipo eligió que aceptar deje la alternativa en el viaje como **reserva propuesta** y ofrezca el enlace a la
oferta del proveedor. Una cancelación ya genera hoy un push (ADR-0046), y el panel es un documento por usuario con
un único escritor (ADR-0040).

## Decision Drivers

* QA-11: sugerencias disponibles y avisadas en 2 minutos.
* QA-13: reordenar en 2 s ante un rechazo o un ajuste.
* QA-2 y QA-4: el panel no se agranda ni depende del módulo nuevo.
* QA-7: solo el dueño del viaje ve sus sugerencias.
* ADR-0040 (panel por lectura por clave, único escritor), ADR-0044 (dueño por campo), ADR-0046 (notificador).

## Considered Options

Cómo se entera y cómo las lee:

* A1. API propia del proceso de recomendación, con aviso push y SSE del notificador
* A2. Sugerencias dentro del documento del panel
* A3. Solo en la app, sin push nuevo

Qué pasa al aceptar:

* B1. La recomendación publica un evento y el núcleo crea la reserva propuesta
* B2. La recomendación llama a la API del núcleo para crear la reserva
* B3. Solo se abre el enlace al proveedor

## Decision Outcome

Chosen options: "A1. API propia con aviso del notificador" y "B1. Evento y reserva propuesta en el núcleo", because el
panel no cambia de forma ni de tamaño (QA-2), el aviso reutiliza el notificador que ya existe, y la reserva propuesta
la escribe el núcleo como cualquier otro cambio del viaje, en una transacción de la partición del usuario y con su
outbox, sin una llamada sincrónica entre procesos.

Reglas de entrega:

* **API de sugerencias** servida por el proceso de recomendación, detrás de la puerta de entrada de la región
  ([OpenAPI](../../specs/openapi/itinerary-api.v1.yaml)): `GET /trips/{tripId}/suggestions`,
  `POST /suggestions/{suggestionId}/feedback` (aceptar, rechazar o ajustar), `GET` y `PUT
  /recommendations/preferences`, y `DELETE /recommendations/profile`. La puerta valida el token como en el resto de
  la API (ADR-0060) y las atiende con **prioridad baja** ante sobrecarga (ADR-0047).
* **Solo el dueño:** las sugerencias pertenecen al `userId` del viaje. Esas rutas no están en la tabla del canal
  entre regiones (ADR-0062): un viaje con prefijo de otra región responde `404` en la puerta. Dentro de la región,
  el proceso de recomendación filtra por el usuario autenticado; como no sabe de quién es cada viaje, un viaje ajeno
  responde igual que uno sin sugerencias (`searchStatus: none`, lista vacía), sin revelar si existe, y una
  sugerencia ajena responde `404`. Quien tiene un viaje compartido no ve sugerencias y la vista compartida tampoco
  muestra reservas propuestas.
* **Aviso:** la recomendación publica `suggestions.available.v1` desde su outbox. El notificador lo envía como push
  (relevancia importante) y como evento SSE `suggestions-available` a la app abierta. El push usa la clave de
  colapso de la reserva cancelada, la misma que el núcleo pone en el push de la cancelación
  (`panel.changed.v1` 0.3.0, campo `collapseKey`): en el teléfono queda un solo aviso, "Tu vuelo fue cancelado:
  encontramos 3 alternativas" (extensión de ADR-0046).

Reglas de aceptación:

* Al aceptar, la recomendación guarda el feedback y publica `suggestion.accepted.v1` en la misma transacción (su
  outbox) y responde `202` con el enlace a la oferta. El núcleo lo consume con una cola quorum propia
  (`core.suggestions`), con deduplicación por `suggestionId`, y crea en el viaje de la reserva cancelada una reserva
  con estado **`proposed`** y origen **`suggestion`**, con los datos de la oferta y su enlace. El panel cambia
  (`booking_added`) y llega a la app por SSE como cualquier cambio.
* **Reglas de la reserva propuesta** (módulo `reservas` del núcleo): no genera `booking.facts.v1` (no es una
  reserva real para la analítica ni para el perfil); no cambia las fechas del viaje ni su archivado (ADR-0045,
  ADR-0048); el viajero la puede borrar; y la tarea diaria la elimina cuando pasa su fecha de inicio sin confirmarse.
* **Conciliación con la reserva real:** si el viajero reserva y la reserva llega por la ingesta con el mismo tipo,
  el mismo proveedor y fechas que se superponen (tolerancia de un día, suposición) en el mismo viaje, la novedad
  reemplaza a la propuesta en la misma transacción (ADR-0044). Si hay más de una propuesta posible, no se elige:
  se crea la reserva real y las propuestas quedan para que el viajero las borre.
* Rechazar o ajustar no pasa por el núcleo: la respuesta trae las sugerencias reordenadas (ADR-0083).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *API Gateway* (ADR-0004) | La puerta enruta las rutas de sugerencias al proceso de recomendación | QA-7 |
| Patrones *Transactional Outbox* e *Idempotent Receiver* | Aceptación y evento en una transacción; el núcleo deduplica por `suggestionId` | QA-6 |
| Patrón *Publish-Subscribe* | `suggestions.available.v1` al notificador y `suggestion.accepted.v1` al núcleo | QA-11, QA-16 |
| Táctica *priorizar eventos* (performance) | Las rutas de sugerencias son de prioridad baja ante sobrecarga | QA-2 |
| Táctica *autorizar actores* (seguridad) | Sugerencias y preferencias solo para el dueño | QA-7 |

### Consequences

* Good, because el panel y su caché (ADR-0040, ADR-0041) no cambian de forma.
* Good, because el viajero recibe un solo aviso con la cancelación y las alternativas.
* Good, because la reserva propuesta sigue las mismas reglas de transacción, outbox y panel que el resto.
* Bad, because el núcleo suma un estado de reserva y una regla de conciliación, y la OpenAPI cambia (estado
  `proposed`, origen `suggestion`, enlace a la oferta).
* Bad, because la aceptación es asincrónica: la reserva propuesta aparece en el panel unos segundos después del `202`.
* Bad, because la conciliación por tipo, proveedor y fechas puede no reconocer una reserva real distinta de la
  oferta; en ese caso la propuesta queda hasta que el viajero la borra o vence.

### Confirmation

Pruebas del prototipo: la cancelación y las alternativas usan la misma clave de colapso; aceptar crea la reserva
propuesta una sola vez aunque el evento se reentregue; la reserva real que llega por la ingesta reemplaza a la
propuesta; otro usuario recibe una lista vacía para un viaje ajeno y `404` para una sugerencia ajena, y desde otra
región el viaje da `404`; la ruta de sugerencias recibe `503` antes que el panel ante sobrecarga y, con la
recomendación detenida, el panel sigue respondiendo (`test_iteracion5_recomendacion.py`).

## Pros and Cons of the Options

### A1. API propia con aviso del notificador

* Good, because desacopla el panel del módulo y reutiliza el notificador.
* Bad, because la app hace una solicitud más para ver las sugerencias.

### A2. Sugerencias dentro del panel

* Good, because la app las recibe sin una solicitud aparte.
* Bad, because agranda el documento del panel, suma un segundo escritor y acopla su forma al módulo (ADR-0040).

### A3. Solo en la app, sin push

* Good, because no cambia ADR-0046.
* Bad, because no es proactivo: el viajero se entera recién cuando abre la app.

### B1. Evento y reserva propuesta en el núcleo

* Good, because el núcleo escribe sus datos con sus reglas y sin llamadas sincrónicas.
* Bad, because la reserva aparece con un atraso de segundos.

### B2. Llamada a la API del núcleo

* Good, because la reserva aparece en la misma respuesta.
* Bad, because acopla la disponibilidad de la aceptación a la del núcleo y suma una llamada entre procesos con sus
  reintentos.

### B3. Solo el enlace

* Good, because no toca el núcleo.
* Bad, because la alternativa elegida no queda en el viaje hasta que el viajero reserve.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 5, [iteration-5-recommendation](../01-add/iteration-5-recommendation.md) |
| Drivers | RF-09.1, RF-09.2, QA-7, QA-11, QA-13 |
| Contratos | [OpenAPI](../../specs/openapi/itinerary-api.v1.yaml), [suggestions-available.v1.yaml](../../specs/asyncapi/suggestions-available.v1.yaml), [suggestion-accepted.v1.yaml](../../specs/asyncapi/suggestion-accepted.v1.yaml), [panel-changed.v1.yaml](../../specs/asyncapi/panel-changed.v1.yaml) |
| Vistas afectadas | [C&C](../02-views/cc-view.md), [secuencias](../02-views/sequence-views.md) |
| Código del prototipo | `prototype/recomendacion/`, `prototype/nucleo/reservas/propuestas.py`, `prototype/notificador/` |
