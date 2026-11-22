---
status: "accepted"
date: 2026-11-22
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Proceso de recomendación por región, alimentado por eventos y con su propio almacén de perfiles

## Context and Problem Statement

RF-09 pide sugerir alternativas ante una cancelación a partir del historial y las preferencias del viajero, y
refinar el modelo con su feedback. Hay que decidir dónde corre ese cómputo, de dónde se entera de las cancelaciones y
del historial, y dónde guarda el perfil de preferencias. ADR-0064 dejó establecido que el almacén analítico no sirve:
está seudonimizado con una clave anual y no ofrece un perfil estable por usuario.

## Decision Drivers

* QA-11 (sugerencias avisadas en 2 minutos) y QA-16 (una falla de la recomendación no afecta el panel).
* QA-2 y QA-4: el panel no puede perder latencia ni disponibilidad por el módulo nuevo.
* QA-14: el viajero desactiva la recomendación y borra su perfil.
* CON-3 (suposición): datos personales en la región de origen. CON-5 (suposición): sin capacidad ociosa.
* ADR-0001 (procesos separados), ADR-0002 (publicación/suscripción), ADR-0064 (analítica seudonimizada).

## Considered Options

Dónde corre:

* A1. Un proceso nuevo por región
* A2. Un módulo dentro del núcleo

De dónde se entera:

* B1. Consumiendo `booking.facts.v1`, que se amplía a dos consumidores
* B2. Publicando `booking.changed.v1` ampliado con los campos que faltan
* B3. Consultando la base del núcleo

Qué pasa con el perfil cuando se eliminan los viajes (ADR-0045):

* C1. El perfil resumido sobrevive y es borrable
* C2. El perfil se recalcula solo con los viajes vigentes

## Decision Outcome

Chosen options: "A1. Un proceso nuevo por región", "B1. Consumir `booking.facts.v1`" y "C1. El perfil sobrevive y es
borrable", because el proceso aparte no compite con la atención del panel (QA-2, QA-4) y puede fallar sin afectarlo
(QA-16); `booking.facts.v1` ya trae exactamente los campos que hacen falta (usuario, viaje, tipo, estado, origen,
proveedor, ciudades y fechas) y evita un segundo evento casi igual; y un perfil resumido conserva lo aprendido sin
guardar viajes ni reservas.

Reglas:

* **Proceso `recomendacion` por región**, como la analítica: varias instancias en al menos dos zonas, que compiten
  por su cola (*Competing Consumers*) y escalan de forma reactiva (ADR-0043). No lee la base del núcleo ni la de la
  analítica, y el núcleo no lee la suya.
* **Entrada de datos:** una cola quorum propia, `recommendation.facts`, enlazada a `booking.facts.v1` en
  `travel.domain`. El contrato de `booking.facts.v1` pasa a tener dos consumidores de la misma región: la analítica,
  que seudonimiza antes de guardar, y la recomendación, que usa el `userId` real porque necesita un perfil por
  usuario. `correlationId` se usa solo para trazas (ADR-0067). El evento suma `startsAt` y `endsAt` opcionales
  (con hora), porque la recomendación compara horarios con la reserva cancelada; la analítica los sigue guardando
  a nivel día, como pide ADR-0064.
* **Consecuencia sobre la decisión pendiente del prototipo:** `booking.changed.v1` se retira. No tenía consumidor y
  su papel lo cubre `booking.facts.v1`; el núcleo deja de declararlo (ver registro de impactos).
* **Recepción idempotente:** el consumidor deduplica por `eventId` y guarda el hecho, la actualización del perfil y,
  si corresponde, la búsqueda pendiente en una sola transacción antes del ACK (*Idempotent Receiver*).
* **Disparador:** un hecho con `changeType` `cancelled` de una reserva de alojamiento (`hotel`) o de transporte
  (`flight`, `train`, `bus`, `car`) con origen `provider` o `email`. Un borrado o una cancelación manual del propio
  viajero no dispara sugerencias. Si el viajero desactivó la recomendación, el hecho solo se descarta.
* **Perfil resumido:** contadores y promedios por tipo, proveedor y ciudad, duración típica de las estadías,
  anticipación típica, banda de precios de las ofertas aceptadas, preferencias explícitas y los ajustes de pesos por
  usuario (ADR-0083). No guarda códigos de reserva, nombres, notas ni textos del usuario.
* **Almacén propio en la región de origen** (CON-3): perfiles, preferencias, sugerencias, feedback, búsquedas
  pendientes y su outbox, en una base del proceso con réplica en otra zona, como el resto de las bases (ADR-0003).
* **Retención:** el perfil sobrevive al borrado de los viajes (ADR-0045) porque no los contiene. Se borra cuando el
  viajero lo pide o cuando se elimina su cuenta; el feedback identificable se borra junto con el perfil. Sugerencias
  vencidas (oferta caducada o reserva propuesta reemplazada) se borran a los 30 días (suposición).
* **Activación (opt-out):** la recomendación viene activada. El viajero la desactiva desde la app: desde ese
  momento no se generan sugerencias (QA-14) y puede borrar el perfil por separado.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Publish-Subscribe* (ADR-0002) | Cola propia enlazada a `booking.facts.v1`, sin tocar el núcleo | QA-15, QA-16 |
| Patrón *Competing Consumers* | Instancias que comparten `recommendation.facts` | QA-12 |
| Patrón *Idempotent Receiver* | Deduplicación por `eventId` con hecho, perfil y búsqueda en una transacción | QA-11 |
| Táctica *separar entidades* (seguridad) | Perfiles en un proceso y una base propios, fuera del núcleo y de la analítica | QA-14 |
| Táctica *limitar la exposición* (seguridad) | El perfil guarda métricas resumidas, no reservas ni textos | QA-14, CON-3 |
| Táctica *degradación elegante* (disponibilidad) | Si el proceso falla, el panel sigue y los hechos esperan en la cola | QA-16 |

### Consequences

* Good, because el núcleo no cambia para recibir datos: solo publica lo que ya publicaba.
* Good, because una caída de la recomendación deja los hechos esperando en su cola y el panel intacto.
* Good, because se cierra la decisión pendiente de `booking.changed.v1`.
* Bad, because `booking.facts.v1` deja de ser exclusivo de la analítica: un cambio de su lista de campos afecta a dos
  consumidores y su descripción de privacidad debe aclarar que la seudonimización es del consumidor analítico.
* Bad, because suma un proceso y una base por región para operar.
* Bad, because el perfil también se tiene que borrar cuando se elimina la cuenta, lo que exigía diseñar ese borrado
  para todo el sistema; lo resuelve [ADR-0085](0085-eliminacion-de-la-cuenta.md), con `account.deleted.v1` por la
  misma cola `recommendation.facts`.

### Confirmation

Pruebas del prototipo: una cancelación del proveedor genera sugerencias y una manual no; un hecho reentregado no
duplica; con la recomendación desactivada no se generan sugerencias; borrar el perfil elimina perfil y feedback;
con el proceso de recomendación detenido, el panel sigue respondiendo.

## Pros and Cons of the Options

### A1. Proceso nuevo por región

* Good, because aísla el cómputo y las fallas del panel.
* Bad, because es un proceso más para desplegar y observar.

### A2. Módulo del núcleo

* Good, because es más simple de desplegar.
* Bad, because la búsqueda de ofertas y el entrenamiento compiten con la atención del panel (QA-2) y una falla
  del módulo comparte el destino del núcleo.

### B1. Consumir `booking.facts.v1`

* Good, because los campos ya existen y ya pasan por la outbox del núcleo.
* Bad, because el contrato pasa a tener dos consumidores con usos distintos del `userId`.

### B2. Publicar `booking.changed.v1` ampliado

* Good, because mantiene `booking.facts.v1` exclusivo de la analítica.
* Bad, because publica dos eventos casi iguales por cada cambio de reserva.

### B3. Consultar la base del núcleo

* Bad, because rompe la propiedad de los datos de cada proceso (ADR-0001) y carga la base del panel.

### C1. El perfil sobrevive y es borrable

* Good, because conserva lo aprendido del viajero, que es lo que el human-in-the-loop construye.
* Bad, because los datos resumidos duran más que los viajes que los originaron; se compensa con el borrado a pedido.

### C2. El perfil se recalcula con los viajes vigentes

* Good, because nada dura más que los viajes.
* Bad, because cada año se pierde el aprendizaje y el feedback deja de influir.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 5, [iteration-5-recommendation](../01-add/iteration-5-recommendation.md) |
| Drivers | RF-09, QA-11, QA-14, QA-16, CON-3, CON-5 |
| Contratos | [booking-facts.v1.yaml](../../specs/asyncapi/booking-facts.v1.yaml), [recommendation.md](../../specs/recommendation.md) |
| Vistas afectadas | [Módulos](../02-views/module-view.md), [C&C](../02-views/cc-view.md), [despliegue](../02-views/deployment-view.md) |
| Código del prototipo | `prototype/recomendacion/` |
