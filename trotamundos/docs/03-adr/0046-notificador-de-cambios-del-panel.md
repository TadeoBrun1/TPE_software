---
status: "accepted"
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
  pide `GET /panel` (ADR-0041) si esa versión es mayor que la que tiene.
* **Orden de conexión, para no perder cambios:** la app **primero** abre la conexión SSE y espera la confirmación
  (evento `ready`), y **después** revalida el panel con `GET /panel` e `If-None-Match`. Así, un cambio que ocurra
  entre ambos pasos llega por SSE o queda incluido en la revalidación. Si se hiciera al revés, un cambio entre la
  revalidación y la conexión se perdería y la app quedaría con la versión vieja.
* **Reconexión:** SSE reconecta solo, pero el notificador no guarda los avisos de una conexión caída (no hay
  historial por usuario), así que reconectar no recupera lo perdido. Por eso, **cada vez que la conexión se
  restablece** (evento `ready`), la app vuelve a revalidar el panel. Como el aviso solo informa una versión, alcanza
  con revalidar una vez: no hace falta recuperar cada aviso perdido.
* **Respaldo mientras SSE está caído:** con la app abierta y sin conexión SSE, la app revalida el panel cada 60 s
  (con espera creciente si también falla la API) hasta que SSE vuelve. Es una consulta condicional barata (`304` si
  no cambió) y solo ocurre durante la caída. Mientras dure, la etapa de cliente de QA-1 puede pasar de 30 s a 60 s.
* **App cerrada:** solo los avisos con relevancia `important` (cancelación, cambio de horario, novedad que pisó una
  edición del usuario) generan un push del sistema operativo. Para no enviarlo una vez por instancia, esos avisos
  también van a una cola compartida `notifier.push` con consumidores que compiten entre sí.
* **Push repetidos:** la cola compartida evita que cada instancia envíe su copia, pero **no** garantiza un solo envío.
  El mismo aviso puede llegar dos veces (la outbox republica tras una caída, el broker reentrega si el trabajador
  cae después de enviar y antes de confirmar), y los servicios de push del sistema operativo tampoco garantizan una
  sola entrega. Se mitiga así:
  * cada push tiene una identidad estable: `eventId` + dispositivo destinatario;
  * el trabajador registra los push enviados (con vencimiento de 24 h) y descarta los que ya figuran;
  * cada push lleva una clave de colapso (`apns-collapse-id`, `collapse_key`) derivada de esa identidad, para que si
    igual llega dos veces el dispositivo muestre una sola notificación.

  Queda un caso sin cubrir: si el trabajador envía y cae antes de registrar el envío, se repite. Se acepta, porque un
  aviso duplicado (que además el dispositivo colapsa) es mucho menos grave que uno perdido.
* **Configuración de las colas** (detalle en `specs/ingestion-operations.md`): las colas de avisos por instancia son
  la única excepción a las colas *quorum* de ADR-0028. Son *classic*, exclusivas, no durables y se borran solas
  cuando la instancia se desconecta, porque perder un aviso no pierde datos (la app revalida al reconectar). La cola
  `notifier.push` sí es *quorum* y durable, como el resto.
* El texto del aviso al usuario (por ejemplo, "el hotel cambió la fecha que habías modificado") queda en el panel, en
  la lista `notices` (ADR-0044), y se lee por la API autenticada.
* Si el notificador cae, nadie pierde datos: la app sigue mostrando su caché y revalida al abrir o recargar.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Publish-Subscribe* (ADR-0002) | El notificador se suscribe a `panel.changed.v1` sin que el núcleo lo conozca | QA-1, QA-5 |
| Patrón *Transactional Outbox* (ADR-0027) | El aviso se publica solo si el cambio se confirmó | QA-1 |
| Patrón *Competing Consumers* | Cola compartida para los push: cada push lo procesa un solo trabajador | QA-1 |
| Patrón *Idempotent Receiver* | Registro de push enviados por `eventId` y dispositivo, más clave de colapso | QA-1 |
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
* Bad, because un push puede llegar duplicado en un caso de falla puntual (mitigado con la clave de colapso).
* Bad, because mientras SSE está caído, la app consulta cada 60 s y la etapa de cliente de QA-1 puede llegar a 60 s.
* Bad, because el núcleo publica un evento más por cada cambio.

### Confirmation

Prototipo: un cliente SSE conectado recibe la versión nueva después de un commit en el núcleo; con dos instancias del
notificador, el aviso llega a la que tiene la conexión y la otra lo descarta. Casos de prueba:

* un cambio que ocurre entre la apertura de SSE y la revalidación termina visible;
* después de cortar y reconectar SSE, la app revalida y obtiene la versión que cambió mientras estaba desconectada;
* con SSE caído, la app revalida cada 60 s;
* un aviso `important` reentregado no genera un segundo push (y si se fuerza el envío, el dispositivo lo colapsa).

Medir el tiempo entre el commit y la recepción del aviso contra los 30 s de la etapa de cliente.

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

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #6](https://github.com/TadeoBrun1/TPE_software/pull/6),
merge `54122ee` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
