---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: ""
informed: "Tomas Lateana"
---

# Caché local del panel en la app, revalidada por versión

> El aviso de cambios al cliente, que antes formaba parte de esta ADR, se separó en
> [ADR-0046](0046-notificador-de-cambios-del-panel.md) para respetar la regla de una decisión por archivo.

## Context and Problem Statement

QA-3 exige que el primer contenido en móvil aparezca en menos de 1,4 s con red 4G y sesión iniciada. Si la app espera
la respuesta del servidor para mostrar algo, el tiempo depende de la red móvil: resolución de nombres, conexión
segura, solicitud y respuesta. Se supone que ese recorrido puede llevar entre 600 y 1000 ms con 4G (suposición: el
enunciado no fija condiciones de red), y con red regular se acerca al límite. Hay que decidir cómo logra la app
mostrar contenido a tiempo.

## Decision Drivers

* QA-3 Primer despliegue móvil en menos de 1,4 s (95 % de las aperturas, 4G, sesión iniciada).
* CON-4: la app es nativa y puede guardar datos en el dispositivo.
* QA-5: la solución no debe agregar carga en el servidor durante los picos.

## Considered Options

* A. Caché local del panel en la app, mostrada al abrir y revalidada en paralelo con la versión
* B. Sin caché: respuesta mínima del servidor con el próximo viaje primero
* C. Caché local y, cuando no hay caché, respuesta mínima

## Decision Outcome

Chosen option: "A. Caché local revalidada por versión", because saca a la red y al servidor del camino de QA-3:
la app muestra contenido sin esperar nada externo.

* La app guarda el último panel recibido y su versión. Al abrir, lo muestra de inmediato.
* En paralelo pide `GET /panel` con `If-None-Match: <versión>`. Si no cambió, el servidor responde `304` sin cuerpo;
  si cambió, responde `200` con el panel nuevo y la app refresca la pantalla (*stale-while-revalidate*).
* La versión es la del documento `panel_por_usuario` (ADR-0040), así que la validación es una comparación barata.
* La web aplica lo mismo con el almacenamiento del navegador cuando está disponible.

**Cobertura de QA-3: aperturas sin caché.** Tener la sesión iniciada no garantiza tener caché: la primera apertura
después de instalar, un dispositivo nuevo, una reinstalación o que el sistema operativo borre el almacenamiento de
la app dejan la sesión sin panel guardado. El escenario QA-3 no excluye esos casos, así que **cuentan dentro del
95 %**:

* Suposición (a validar con métricas de uso): las aperturas sin caché son menos del 5 % del total, porque la caché
  se conserva entre aperturas y solo se pierde en esos casos puntuales. Si es así, el 95 % se puede cumplir aunque
  esas aperturas tarden más.
* Para que también sean rápidas, la respuesta del panel va comprimida y un panel típico pesa hasta 20 KB (ADR-0040).
* Si las mediciones muestran que superan el 5 %, o que tardan demasiado, se agrega la respuesta mínima con el
  próximo viaje (opción C). Queda como **cobertura pendiente** de QA-3.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Caché del cliente con validación condicional (HTTP `ETag` / `If-None-Match`, *stale-while-revalidate*) | El panel guardado se muestra y se revalida con su versión | QA-3 |
| Táctica *mantener múltiples copias de los datos* (performance) | Copia del panel en el dispositivo | QA-3 |
| Táctica *reducir la sobrecarga computacional* (performance) | Si no hubo cambios, el servidor responde `304` sin armar ni enviar el cuerpo | QA-5 |

### Consequences

* Good, because QA-3 deja de depender de la red y del servidor; además la app muestra el panel sin señal, algo útil
  para quien está viajando.
* Good, because las revalidaciones sin cambios son baratas para el servidor.
* Bad, because la app puede mostrar datos viejos durante la revalidación (normalmente menos de un segundo).
* Bad, because las aperturas sin caché (instalación, dispositivo nuevo, caché borrada) dependen de la red y cuentan
  dentro del 95 % de QA-3; su cumplimiento depende de que sean pocas (suposición a validar).

### Confirmation

Prototipo: una app o cliente de prueba muestra el panel guardado antes de recibir la respuesta; `GET /panel` con la
versión vigente devuelve `304`. Medición del primer contenido con red 4G simulada, con y sin caché, y medición en
uso real de qué porcentaje de las aperturas no tiene caché.

## Pros and Cons of the Options

### A. Caché local revalidada por versión

* Good, because el primer contenido no depende de la red.
* Bad, because puede mostrar datos viejos por un instante y no cubre la primera instalación.

### B. Respuesta mínima sin caché

* Good, because los datos siempre son frescos.
* Bad, because con red 4G regular el tiempo de red solo ya se acerca a 1,4 s, y sin señal no se muestra nada.

### C. Caché y respuesta mínima

* Good, because cubre también la primera apertura.
* Bad, because agrega un endpoint solo para un caso que el escenario de QA-3 no incluye.
* Neutral, because puede sumarse después sin cambiar esta decisión.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | QA-3, QA-5, CON-4 |
| Vistas afectadas | [sequence-views](../02-views/sequence-views.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0004](0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md), [0040](0040-modelo-de-lectura-del-panel.md), [0046](0046-notificador-de-cambios-del-panel.md) |
| Código del prototipo | `prototype/` |
