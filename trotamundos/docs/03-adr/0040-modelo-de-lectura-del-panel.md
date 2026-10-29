---
status: "accepted"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (impactos con la iteración 2)"
informed: ""
---

# Modelo de lectura del panel por usuario, actualizado en la misma transacción

## Context and Problem Statement

El panel muestra los viajes activos de un usuario con todas sus reservas agrupadas. En la base del núcleo esos datos
están normalizados (viajes, reservas, datos propios del usuario), así que armar el panel en cada apertura exige
buscar, unir y ordenar varias tablas. Ese trabajo se repite en cada lectura, crece con la cantidad de reservas y, en
un pico por disrupción, compite con las escrituras que llegan de la ingesta. Hay que decidir cómo el núcleo obtiene
el panel para cumplir los 800 ms de QA-2 de forma estable.

## Decision Drivers

* QA-2 Latencia web: el 95 % de las solicitudes del panel en 800 ms o menos.
* QA-5 Escalabilidad: la latencia debe mantenerse en los picos, cuando además llegan muchas novedades.
* RF-04 Gestión manual: el viajero que cambia una reserva tiene que ver su cambio al recargar el panel (coherencia).
* QA-1: el panel no debe consumir parte de los 5 minutos de frescura.

## Considered Options

* A. Consulta directa sobre las tablas normalizadas, con índices por usuario
* B. Consulta directa con una caché distribuida delante (*cache-aside*)
* C. Modelo de lectura por usuario en la misma base, actualizado en la misma transacción que el cambio
* D. Modelo de lectura por usuario actualizado de forma asincrónica desde los eventos de dominio
* E. Modelo de lectura (C) más una caché distribuida para usuarios activos

## Decision Outcome

Chosen option: "C. Modelo de lectura por usuario en la misma base, actualizado en la misma transacción", because
convierte la lectura del panel en una búsqueda por clave, sin uniones ni ordenamientos en cada apertura, y
mantiene coherencia fuerte sin agregar componentes: el núcleo es un monolito con una base por región (ADR-0001,
ADR-0003), así que el cambio y la copia del panel se pueden confirmar juntos.

Reglas:

* Además de las tablas normalizadas, el núcleo guarda `panel_por_usuario`: un documento por usuario con sus viajes
  activos y las reservas de cada uno, en el formato que devuelve la API.
* Toda transacción que cambia un viaje o una reserva actualiza, en la misma transacción, el documento del usuario y
  la outbox de eventos de dominio (ADR-0027).
* **Único escritor:** solo el componente *proyector del panel* escribe `panel_por_usuario`. Los demás módulos le
  piden la actualización; ninguno escribe la tabla directamente (regla de dependencia en la vista de módulos).
* **Reconstruible:** las tablas normalizadas son la fuente de verdad. El panel de un usuario se puede regenerar desde
  cero en cualquier momento (por ejemplo, ante un error o un cambio de formato).
* **Concurrencia por usuario:** "único escritor" dice qué módulo escribe, pero ese módulo corre en varias instancias
  a la vez, y un cambio manual y una novedad del mismo usuario pueden llegar al mismo tiempo. Por eso, cada
  transacción que modifica algo de un usuario **toma primero un bloqueo sobre la fila de `panel_por_usuario` de ese
  usuario** (bloqueo pesimista, del tipo `SELECT ... FOR UPDATE`). Las transacciones del mismo usuario quedan en fila
  una detrás de otra; las de usuarios distintos no se esperan. Si una espera más de 2 s, se aborta y se reintenta
  (hasta 3 veces), y si igual falla, el cambio manual responde `503` y la novedad vuelve a la cola.
* **Versionado:** dentro de esa transacción, la versión del panel pasa a `versión anterior + 1`, así que crece de a uno
  y nunca se repite ni retrocede. Se usa para detectar desvíos, como `ETag` de la API (ADR-0041) y en el aviso al
  cliente (ADR-0046).
* **Tamaño del panel:** leer por clave evita las uniones, pero leer, serializar y enviar el documento cuesta más
  cuanto más grande es. Los viajes archivados no están en el documento (ADR-0045), pero siguen creciendo las
  reservas activas, futuras y sin asignar. Tamaños de referencia (suposición, a validar):

  | Caso | Viajes activos | Reservas | Tamaño aproximado del documento |
  |---|---|---|---|
  | Típico | 1 a 3 | hasta 20 | hasta 20 KB |
  | Grande (viajero frecuente) | hasta 15 | hasta 150 | hasta 150 KB |
  | Límite | más de 15 viajes o más de 150 reservas | — | Se aplica la estrategia de abajo |

  **Estrategia para paneles grandes:** el documento guarda completos los 15 viajes activos más próximos; del resto
  guarda solo un resumen (nombre, fechas, cantidad de reservas), y su detalle se pide con `GET /trips/{tripId}`. Las
  respuestas van comprimidas (gzip). Así el documento queda acotado aunque el usuario acumule viajes.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón CQRS (separación de modelos de lectura y escritura), en su variante con un solo almacén | Tablas normalizadas para escribir; documento por usuario para leer | QA-2 |
| Patrón *Materialized View* | El documento del panel es una vista precalculada | QA-2, QA-5 |
| Táctica *mantener múltiples copias de los datos* (performance) | Segunda representación de los mismos datos, optimizada para leer | QA-2 |
| Táctica *reducir la sobrecarga computacional* (performance) | Se elimina el armado del panel en cada lectura | QA-2, QA-5 |
| Táctica *limitar el tiempo de ejecución* / acotar el tamaño (performance) | Documento acotado a 15 viajes completos; el resto en resumen | QA-2 |
| Bloqueo pesimista por usuario | Serializa las transacciones de un mismo usuario | QA-2, RF-04 |

### Consequences

* Good, because la lectura del panel es una búsqueda por clave dentro de la partición del usuario (ADR-0042), sin
  uniones; su costo crece con el tamaño del documento, que queda acotado por la estrategia de paneles grandes.
* Good, because hay coherencia fuerte: no existe un momento en que la reserva cambió y el panel todavía no.
* Good, because no agrega ningún componente de infraestructura.
* Bad, because cada escritura hace más trabajo (cambio + documento + outbox).
* Bad, because hay dos representaciones de los mismos datos; un error de programación puede desincronizarlas. Se
  mitiga con el único escritor, la versión y la reconstrucción.
* Bad, because los cambios de un mismo usuario se serializan por el bloqueo; si llegan muchos a la vez, esperan.
  Es aceptable porque los cambios de un mismo usuario son pocos por minuto.
* Bad, because un usuario con muchos viajes ve el detalle de los más lejanos con una solicitud más.

### Confirmation

* Revisión de la [vista de módulos](../02-views/module-view.md): solo el proyector escribe `panel_por_usuario`.
* Prototipo: el endpoint del panel responde con una lectura por clave; un cambio manual y una novedad aplicada
  actualizan el documento en la misma transacción; regenerar el panel desde las tablas da el mismo resultado.
* Prueba de concurrencia: un cambio manual y una novedad sobre reservas distintas del mismo usuario, al mismo
  tiempo, terminan con el panel conteniendo los dos cambios y la versión aumentada en 2.
* Prueba de carga del panel contra QA-2 en el escenario de pico, con paneles de tamaño típico, grande y en el límite.

## Pros and Cons of the Options

### A. Consulta directa sobre tablas normalizadas

* Good, because hay una sola representación y nada que sincronizar.
* Bad, because cada lectura repite uniones y ordenamientos; la latencia depende del volumen y compite con las
  escrituras en los picos (QA-2, QA-5).

### B. Consulta directa con caché distribuida

* Good, because es muy rápido cuando el dato está en caché.
* Bad, because en una disrupción llegan muchos usuarios que no estaban en caché, y su primera consulta va a la base.
* Bad, because la invalidación de caché es una fuente típica de datos viejos.

### C. Modelo de lectura en la misma transacción

* Good, because combina lectura barata y coherencia fuerte sin componentes nuevos.
* Bad, because encarece un poco cada escritura y exige disciplina de un único escritor.

### D. Modelo de lectura asincrónico

* Good, because las escrituras son más livianas.
* Bad, because el panel queda atrasado unos segundos, y ese atraso se descuenta de los 100 s que la iteración 2
  asignó al núcleo y al cliente dentro de QA-1.
* Neutral, because tiene sentido cuando el modelo de lectura vive en otro almacén, que no es el caso.

### E. Modelo de lectura más caché distribuida

* Good, because es la opción más rápida.
* Bad, because agrega un componente y otra copia para ganar una diferencia que QA-2 no pide: una lectura por clave
  entra con margen en 800 ms.
* Neutral, because se puede agregar después sin cambiar esta decisión si las pruebas lo justifican.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | QA-2, QA-5, QA-1, RF-04 |
| Vistas afectadas | [module-view](../02-views/module-view.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0001](0001-nucleo-modular-con-procesos-separados.md), [0027](0027-publicacion-del-nucleo.md), [0041](0041-cache-local-del-panel.md), [0046](0046-notificador-de-cambios-del-panel.md), [0042](0042-particion-de-la-base-por-usuario.md), [0045](0045-ciclo-de-vida-y-archivado-de-viajes.md) |
| Código del prototipo | `prototype/nucleo/panel/`, `prototype/nucleo/api/rutas.py` |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #6](https://github.com/TadeoBrun1/TPE_software/pull/6),
merge `54122ee` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
