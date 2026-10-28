---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Almacenes analíticos regionales, con los eventos anonimizados al entrar

## Context and Problem Statement

RF-07 pide recopilar datos analíticos (tendencias, destinos, cancelaciones) para el equipo de datos, con consultas
pesadas. ADR-0001 separó la analítica como proceso propio. El núcleo ya publica `booking.changed.v1` y
`trip.changed.v1`, pero esos eventos solo llevan identificadores: no dicen el tipo de reserva, el destino ni las
fechas. Falta decidir de dónde saca la analítica esos datos, dónde los guarda, cómo se tratan los datos personales
entre regiones y qué pasa con los datos de viajes que se eliminan al año (ADR-0045).

## Decision Drivers

* RF-07: consultas pesadas del equipo de datos.
* QA-4 y QA-5: las consultas pesadas no deben afectar a los viajeros.
* CON-3 (suposición): los datos personales no cruzan regiones.
* ADR-0045: los viajes se eliminan al año.

## Considered Options

Dónde se guardan:

* A1. Un almacén analítico por región, sin almacén global
* A2. Almacenes por región más un almacén global solo con agregados
* A3. Un almacén global con eventos seudonimizados

Cómo se tratan los eventos de viajes eliminados:

* B1. Anonimizar al entrar: lo guardado ya no es dato personal
* B2. Guardar con el `userId` y borrar en cascada cuando se elimina el viaje

## Decision Outcome

Chosen options: "A1. Solo almacenes regionales" y "B1. Anonimizar al entrar", because el sistema no mueve datos de
viajes entre regiones (ni personales ni agregados: no hay almacén ni proceso global), y lo que se guarda no tiene
identificadores reales ni textos del usuario, así que eliminar un viaje no exige tocar la analítica.

Reglas:

* **De dónde salen los datos:** el núcleo publica, por la misma outbox y en la misma transacción que cada cambio de
  reserva (ADR-0027), un evento `booking.facts.v1` con los datos que la analítica necesita: tipo, estado, origen de la
  reserva, ciudades, fechas, fecha de creación de la reserva, proveedor y tipo de cambio. No lleva códigos de reserva, nombres, notas ni detalles por
  tipo. La analítica también consume `trip.changed.v1` (archivados, reactivados, eliminados). La analítica no lee la
  base operativa.
* En cada región, el proceso de analítica consume esos eventos con su propia cola y los guarda en un almacén analítico
  propio, separado de la base operativa. Las consultas pesadas corren solo ahí.
* **Anonimización al entrar**, antes de guardar:
  * `userId`, `tripId` y `bookingId` se reemplazan por códigos calculados con una clave de la región que solo tiene
    el proceso de analítica y que se cambia y se destruye cada año. El almacén no guarda los identificadores
    originales ni la clave: con la clave destruida, esos códigos ya no se pueden vincular con nadie;
  * las fechas se guardan a nivel día y los lugares a nivel ciudad;
  * se descartan `correlationId` y cualquier otro dato que no esté en la lista de campos permitidos del contrato.
* **Eliminación de viajes:** un viaje se elimina un año después de archivarse (ADR-0045). Casi todos sus eventos son
  anteriores al archivado, y su clave ya se destruyó cuando el viaje se elimina. Pero un viaje archivado todavía
  puede recibir una novedad tardía (por ejemplo, un reembolso, ADR-0045): ese hecho queda vinculable hasta que se
  destruye la clave del período en que llegó, es decir, hasta un año después de eliminado el viaje en el peor caso.
  Se acepta y no se borra nada en la analítica al eliminar un viaje.
* **Cancelaciones:** como `booking.facts.v1` lleva la fecha de creación de la reserva, la anticipación de una
  cancelación se calcula con el mismo evento de cancelación, sin vincularlo con el de creación. Una reserva creada y
  cancelada en períodos de clave distintos aparece con dos códigos distintos.
* **Consultas globales:** el equipo de datos consulta cada región por separado. Para combinar tendencias de varias
  regiones solo puede exportar agregados (cantidades por ciudad, mes y tipo de reserva) de grupos de al menos 20
  reservas (suposición), nunca filas del almacén. La combinación se hace fuera del sistema operativo.
* Atraso esperado: el que tarda el consumo de eventos (segundos a minutos). No es un requisito: se fija en 15 minutos
  como objetivo de operación (suposición).
* **Para la segunda entrega:** un sistema de recomendación (opción A del enunciado) necesita preferencias por usuario,
  que este almacén no tiene porque está anonimizado. Ese sistema tendrá que guardar su propio perfil resumido por
  usuario (métricas comprimidas), calculado a partir de los datos operativos, en la región del usuario y eliminado
  junto con su cuenta. Queda registrado en el registro de impactos; no se decide acá.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Publish-Subscribe* (ADR-0002) y *Transactional Outbox* (ADR-0027) | La analítica es un consumidor más; `booking.facts.v1` sale en la misma transacción que el cambio | RF-07 |
| Táctica *mantener múltiples copias de los datos* (performance) | Almacén analítico separado de la base operativa | QA-4, QA-5 |
| Táctica *limitar la exposición* (seguridad) | Anonimización al entrar; el sistema no mueve datos entre regiones; solo se exportan agregados de grupos grandes | CON-3 |

### Consequences

* Good, because las consultas pesadas no comparten recursos con los viajeros.
* Good, because el almacén no guarda identificadores ni textos de los usuarios, y al destruirse la clave anual los
  datos dejan de ser vinculables: eliminar un viaje no exige recorrer la analítica.
* Good, because el sistema no mueve datos de viajes entre regiones (CON-3).
* Bad, because no hay una vista global automática: las tendencias globales se combinan a mano región por región, y
  la regla de agregados exportables la aplica el equipo de datos, no el sistema.
* Bad, because un hecho tardío sobre un viaje archivado queda vinculable hasta un año después de eliminado el viaje.
* Bad, because una reserva creada y cancelada en períodos de clave distintos no se puede seguir como una sola.
* Bad, because al anonimizar se pierden análisis por usuario a lo largo de varios años.
* Bad, because durante el año en que la clave existe, los códigos son seudónimos y no anónimos: si un usuario elimina
  su cuenta, sus datos analíticos quedan hasta que se destruye la clave (a lo sumo un año). Se acepta porque el
  almacén no tiene datos de contacto ni textos.
* Bad, because el núcleo publica un evento más por cada cambio de reserva.

### Confirmation

Prueba: un evento `booking.facts.v1` se guarda sin `userId`, `tripId`, `bookingId` ni `correlationId`, y con campos
fuera de la lista permitida se descartan; una consulta pesada en
el almacén analítico no cambia la latencia del panel.

## Pros and Cons of the Options

### A1. Solo regionales

* Good, because el sistema no mueve datos entre regiones ni hay un almacén global que operar.
* Bad, because las tendencias globales se arman fuera del sistema, con agregados exportados a mano.

### A2. Regionales más global agregado

* Good, because da tendencias globales automáticas.
* Bad, because el sistema mueve agregados entre regiones de forma automática y continua: hay que definir, mantener y
  operar ese proceso y el almacén global, y un agregado mal definido se replica sin que nadie lo revise.

### A3. Global seudonimizado

* Good, because las consultas son más simples.
* Bad, because un seudónimo sigue siendo dato personal para normativas como el GDPR: los datos cruzan
  jurisdicciones (CON-3).

### B1. Anonimizar al entrar

* Good, because lo guardado no tiene identificadores reales y deja de ser vinculable al destruirse la clave.
* Bad, because se pierden análisis por usuario.

### B2. Borrar en cascada

* Good, because conserva datos más ricos.
* Bad, because cada eliminación recorre el almacén analítico, y un error deja datos que debían borrarse.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 4, [iteration-4-security-evolvability](../01-add/iteration-4-security-evolvability.md) |
| Drivers | RF-07, QA-4, QA-5, CON-3 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md), [deployment-view](../02-views/deployment-view.md) |
| Specs | [booking-facts.v1.yaml](../../specs/asyncapi/booking-facts.v1.yaml), [trip-changed.v1.yaml](../../specs/asyncapi/trip-changed.v1.yaml) |
| ADRs relacionadas | [0001](0001-nucleo-modular-con-procesos-separados.md), [0027](0027-publicacion-del-nucleo.md), [0045](0045-ciclo-de-vida-y-archivado-de-viajes.md) |
| Código del prototipo | `prototype/` |
