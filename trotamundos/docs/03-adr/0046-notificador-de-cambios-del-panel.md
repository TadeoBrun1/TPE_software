---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (presupuesto de QA-1 y topología de RabbitMQ)"
informed: ""
---

# Notificador separado que avisa cambios del panel por SSE y push, con evento propio y cola por instancia

## Context and Problem Statement

La iteración 2 asignó 30 s a la etapa "actualización visible en cliente" dentro de los 5 minutos de QA-1. Hay que
decidir cómo se entera la app de que su panel cambió, quién mantiene esa comunicación, qué información recibe para
avisar y cómo llega cada aviso a la instancia que tiene abierta la conexión del usuario.

## Decision Drivers

* QA-1 Frescura: la etapa de cliente tiene 30 s dentro de los 300 s.
* QA-5 Escalabilidad: no generar consultas vacías con 2 millones de usuarios activos, y escalar las conexiones abiertas
  sin afectar al núcleo.
* QA-4 Disponibilidad: si falla el mecanismo de avisos, el panel debe seguir funcionando.
* RF-04: el usuario debe enterarse cuando una novedad del proveedor cambia algo que él había editado (ADR-0044).

## Considered Options

Cómo se entera el cliente:

* A1. Aviso del servidor: conexión SSE con la app abierta y push del sistema operativo con la app cerrada, desde un
  proceso notificador separado
* A2. Lo mismo, con las conexiones dentro de las instancias del núcleo
* A3. Consulta periódica de la app cada ~20 s
* A4. Actualizar solo al abrir la app

Qué evento consume el notificador:

* B1. Los eventos de dominio existentes (`booking.changed.v1`, `trip.changed.v1`)
* B2. Un evento propio, `panel.changed.v1`, publicado por el núcleo en la misma transacción que cambia el panel

Cómo llega el aviso a la instancia con la conexión del usuario:

* C1. Una cola exclusiva por instancia, que recibe todos los avisos (*fan-out*); cada instancia descarta los de
  usuarios que no tiene conectados
* C2. Registro de presencia (qué usuario está en qué instancia) y ruteo dirigido

## Decision Outcome

Chosen options: "A1. Notificador separado", "B2. Evento propio `panel.changed.v1`" y "C1. Cola por instancia".

**A1:** cumple los 30 s sin consultas vacías, y la carga del notificador (muchas conexiones abiertas, casi sin
cómputo) queda separada del núcleo, igual que ADR-0001 separó ingesta y analítica.

**B2:** los eventos de dominio de la iteración 2 no traen la versión del panel ni distinguen un cambio de horario de
una edición de notas, y `booking.changed.v1` no admite campos adicionales. En lugar de cambiar un contrato que
consume la analítica, el núcleo publica en su outbox (ADR-0027), en la misma transacción que actualiza el panel
(ADR-0040), el evento `panel.changed.v1` con: usuario, versión del panel, motivo y relevancia. No lleva datos de la
reserva.

**C1:** con los volúmenes supuestos (cientos de cambios de panel por segundo por región), que cada instancia reciba
todos los avisos multiplica el tráfico por la cantidad de instancias, lo cual es aceptable, y evita un componente
con estado. Si el número de instancias crece mucho, se revisa con C2.

Funcionamiento:

* El notificador corre en cada región, con varias instancias en al menos dos zonas.
* **App abierta:** la app abre `GET /panel/events` (SSE) a través de la puerta de entrada y queda conectada a una
  instancia del notificador. Cada instancia tiene una cola exclusiva en el exchange `travel.domain` enlazada a
  `panel.changed.v1`; al recibir un aviso de un usuario conectado le envía `panel-changed` con la versión, y la app
  pide `GET /panel` (ADR-0041).
* **App cerrada:** solo los avisos con relevancia `important` (cancelación, cambio de horario, novedad que pisó una
  edición del usuario) generan un push del sistema operativo. Para no enviarlo una vez por instancia, esos avisos
  también van a una cola compartida `notifier.push` con consumidores que compiten entre sí.
* El texto del aviso al usuario (por ejemplo, "el hotel cambió la fecha que habías modificado") queda en el panel, en
  la lista `notices` (ADR-0044), y se lee por la API autenticada.
* Si el notificador cae, nadie pierde datos: la app sigue mostrando su caché y revalida al abrir o recargar.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Publish-Subscribe* (ADR-0002) | El notificador se suscribe a `panel.changed.v1` sin que el núcleo lo conozca | QA-1, QA-5 |
| Patrón *Transactional Outbox* (ADR-0027) | El aviso se publica solo si el cambio se confirmó | QA-1 |
| Patrón *Competing Consumers* | Cola compartida para los push, para enviar cada uno una sola vez | QA-1 |
| Táctica *aumentar recursos* (performance) | El notificador escala por conexiones abiertas, separado del núcleo | QA-5 |
| Táctica *degradación elegante* (disponibilidad) | Sin notificador, la app funciona con caché y revalidación | QA-4 |

### Consequences

* Good, because los cambios llegan a la pantalla en segundos, sin consultas periódicas.
* Good, because el núcleo sigue sin estado: las conexiones viven en otro proceso.
* Good, because no se modifica ningún contrato de la iteración 2.
* Bad, because hay un proceso más, con conexiones abiertas que dimensionar. Se supone, a partir de los 2 M de usuarios
  activos semanales de QA-5, que del 2 al 5 % tiene la app abierta a la vez. Las mismas conexiones pasan por la
  puerta de entrada, que también hay que dimensionar.
* Bad, because con la cola por instancia el tráfico interno crece con la cantidad de instancias.
* Bad, because el núcleo publica un evento más por cada cambio.

### Confirmation

Prototipo: un cliente SSE conectado recibe la versión nueva después de un commit en el núcleo; con dos instancias del
notificador, el aviso llega a la que tiene la conexión y la otra lo descarta; un aviso `important` genera un solo
push simulado. Medir el tiempo entre el commit y la recepción del aviso contra los 30 s de la etapa de cliente.

## Pros and Cons of the Options

### A1. Notificador separado

* Good, because no carga al núcleo y escala por su cuenta.
* Bad, because es un proceso más.

### A2. Conexiones dentro del núcleo

* Good, because es un proceso menos.
* Bad, because miles de conexiones abiertas ocupan recursos de las instancias que responden el panel.

### A3. Consulta periódica

* Good, because es simple y no guarda estado en el servidor.
* Bad, because genera tráfico vacío constante que crece en los picos (QA-5), y con la app cerrada no avisa.

### A4. Solo al abrir

* Good, because es lo más simple.
* Bad, because con la app abierta un cambio no se vería: no cumple la etapa de cliente de QA-1.

### B1. Eventos de dominio existentes

* Good, because no agrega un evento.
* Bad, because no traen la versión del panel ni la relevancia, y cambiarlos afecta a la analítica (iteración 4).

### B2. Evento propio

* Good, because tiene exactamente lo que el notificador necesita y no toca contratos ajenos.
* Bad, because es un evento más que publicar y mantener.

### C1. Cola por instancia

* Good, because no necesita estado compartido.
* Bad, because cada instancia procesa avisos de usuarios que no tiene conectados.

### C2. Registro de presencia

* Good, because cada aviso va solo a la instancia correcta.
* Bad, because agrega un componente con estado que debe mantenerse al día con cada conexión y desconexión.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | QA-1, QA-5, QA-4, RF-04 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md), [deployment-view](../02-views/deployment-view.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | [panel-changed.v1.yaml](../../specs/asyncapi/panel-changed.v1.yaml), [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0002](0002-mensajeria-persistente-con-publicacion-suscripcion.md), [0027](0027-publicacion-del-nucleo.md), [0028](0028-rabbitmq-y-politicas.md), [0040](0040-modelo-de-lectura-del-panel.md), [0041](0041-cache-local-del-panel.md), [0044](0044-novedades-y-cambios-manuales.md) |
| Código del prototipo | `prototype/` |
