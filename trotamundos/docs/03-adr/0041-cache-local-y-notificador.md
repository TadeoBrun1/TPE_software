---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (presupuesto de QA-1)"
informed: ""
---

# Caché local en la app y notificador separado para avisar cambios del panel

## Context and Problem Statement

Hay dos problemas del lado del cliente:

1. **QA-3:** el primer contenido en móvil debe aparecer en menos de 1,4 s con red 4G. Solo el viaje de ida y vuelta
   de la red móvil (resolución de nombres, conexión segura, solicitud y respuesta) puede llevar 600 a 1000 ms, así que
   si la app espera al servidor para mostrar algo el margen es muy chico.
2. **QA-1:** la iteración 2 asignó 30 s a la etapa "actualización visible en cliente" dentro de los 5 minutos. Hay
   que decidir cómo se entera la app de que su panel cambió.

## Decision Drivers

* QA-3 Primer despliegue móvil en menos de 1,4 s (95 % de las aperturas, red 4G, sesión iniciada).
* QA-1 Frescura: la etapa de cliente tiene 30 s dentro de los 300 s.
* QA-5 Escalabilidad: no generar tráfico de consultas vacías con 2 millones de usuarios activos.
* QA-4 Disponibilidad: si falla el mecanismo de avisos, el panel debe seguir funcionando.

## Considered Options

Para QA-3:

* A1. Caché local del panel en la app, mostrada al abrir y revalidada en paralelo
* A2. Sin caché: respuesta mínima del servidor con el próximo viaje primero
* A3. Ambas: caché local y, si no hay caché, respuesta mínima

Para avisar cambios:

* B1. Aviso del servidor: conexión persistente (SSE o WebSocket) con la app abierta y notificación push del sistema
  operativo con la app cerrada, desde un proceso notificador separado
* B2. Lo mismo que B1, pero con las conexiones dentro de las instancias del núcleo
* B3. Consulta periódica de la app cada ~20 s
* B4. Actualizar solo al abrir la app

## Decision Outcome

Chosen options: "A1. Caché local" y "B1. Aviso del servidor desde un notificador separado", because la caché local
saca a la red del camino de QA-3, y el aviso cumple los 30 s de QA-1 sin consultas vacías, con una carga (muchas
conexiones abiertas, casi sin cómputo) separada del núcleo, igual que ADR-0001 separó ingesta y analítica.

**Caché local (A1):**

* La app guarda el último panel recibido y su versión. Al abrir, lo muestra de inmediato.
* En paralelo pide `GET /panel` con `If-None-Match: <versión>`. Si no cambió, el servidor responde `304` sin cuerpo;
  si cambió, responde `200` con el panel nuevo y la app refresca la pantalla (*stale-while-revalidate*).
* La web aplica lo mismo con el almacenamiento del navegador cuando está disponible.

**Notificador (B1):**

* Proceso separado del núcleo, desplegado en cada región. Consume los eventos de dominio del broker
  (`booking.changed.v1` y `trip.changed.v1`), que ya llevan el usuario.
* Con la app abierta: la app mantiene una conexión SSE con el notificador (pasando por la puerta de entrada) y recibe
  "tu panel cambió, versión N". Al recibirlo, pide el panel.
* Con la app cerrada: envía una notificación push del sistema operativo solo para cambios relevantes para el usuario
  (cancelación, cambio de horario), no para cada actualización.
* El aviso no lleva datos de la reserva: solo la versión. Los datos siempre se piden por la API autenticada.
* Si el notificador se cae, nadie pierde datos: la app sigue mostrando su caché y revalida al abrir o al recargar.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Cache-Aside* en el cliente con revalidación (*stale-while-revalidate*) | Panel guardado en el dispositivo; `ETag`/`If-None-Match` | QA-3 |
| Táctica *mantener múltiples copias de los datos* (performance) | Copia del panel en el cliente | QA-3 |
| Patrón *Publish-Subscribe* (ADR-0002) | El notificador es un consumidor más de los eventos de dominio | QA-1, QA-9 |
| Táctica *dividir módulo* (modificabilidad) / separar cargas | Notificador fuera del núcleo | QA-5 |
| Táctica *degradación elegante* (disponibilidad) | Sin notificador, la app funciona con caché y revalidación | QA-4 |

### Consequences

* Good, because QA-3 deja de depender de la red y del servidor; además la app muestra el panel sin señal, algo útil
  para quien está viajando.
* Good, because los cambios llegan a la pantalla en segundos sin consultas periódicas.
* Good, because el núcleo sigue sin estado: las conexiones abiertas viven en otro proceso.
* Bad, because la app puede mostrar datos viejos durante el tiempo de revalidación (normalmente menos de un segundo).
* Bad, because la primera apertura después de instalar no tiene caché; ahí QA-3 depende de la red (riesgo menor:
  el escenario supone sesión iniciada).
* Bad, because hay un proceso más, con conexiones abiertas que dimensionar: se estima del 2 al 5 % de los usuarios
  activos con la app abierta a la vez (suposición).

### Confirmation

* Prototipo: la app de prueba muestra el panel guardado antes de recibir la respuesta; `GET /panel` con la versión
  vigente devuelve `304`; un cambio confirmado llega como aviso al cliente conectado.
* Medición del tiempo entre el commit en el núcleo y la recepción del aviso contra los 30 s de la etapa de cliente.

## Pros and Cons of the Options

### A2. Respuesta mínima sin caché

* Good, because los datos siempre son frescos.
* Bad, because con red 4G regular el tiempo de red solo ya se acerca a 1,4 s, y sin señal no se muestra nada.

### A3. Caché y respuesta mínima

* Good, because cubre también la primera apertura.
* Bad, because agrega un endpoint solo para un caso que el escenario de QA-3 no incluye; puede sumarse después.

### B2. Conexiones dentro del núcleo

* Good, because es un proceso menos.
* Bad, because miles de conexiones abiertas ocupan recursos de las instancias que responden el panel, y el núcleo
  deja de ser trivial de escalar.

### B3. Consulta periódica

* Good, because es muy simple y no guarda estado en el servidor.
* Bad, because genera tráfico vacío constante que crece en los picos, justo cuando menos capacidad sobra (QA-5), y
  con la app cerrada no avisa.

### B4. Solo al abrir

* Good, because es lo más simple.
* Bad, because con la app abierta un cambio no se vería: no cumple la etapa de cliente de QA-1.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | QA-3, QA-1, QA-5, QA-4 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md), [deployment-view](../02-views/deployment-view.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml), [trip-changed.v1.yaml](../../specs/asyncapi/trip-changed.v1.yaml), [booking-confirmed.v1.yaml](../../specs/asyncapi/booking-confirmed.v1.yaml) |
| ADRs relacionadas | [0002](0002-mensajeria-persistente-con-publicacion-suscripcion.md), [0004](0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md), [0027](0027-publicacion-del-nucleo.md), [0040](0040-modelo-de-lectura-del-panel.md) |
| Código del prototipo | `prototype/` |
