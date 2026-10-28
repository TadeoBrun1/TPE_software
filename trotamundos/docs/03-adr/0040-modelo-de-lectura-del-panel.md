---
status: "proposed"
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
* Coherencia: el viajero no debe ver un panel que contradiga un cambio que ya se confirmó.
* QA-1: el panel no debe consumir parte de los 5 minutos de frescura.

## Considered Options

* A. Consulta directa sobre las tablas normalizadas, con índices por usuario
* B. Consulta directa con una caché distribuida delante (*cache-aside*)
* C. Modelo de lectura por usuario en la misma base, actualizado en la misma transacción que el cambio
* D. Modelo de lectura por usuario actualizado de forma asincrónica desde los eventos de dominio
* E. Modelo de lectura (C) más una caché distribuida para usuarios activos

## Decision Outcome

Chosen option: "C. Modelo de lectura por usuario en la misma base, actualizado en la misma transacción", because
convierte la lectura del panel en una búsqueda por clave, cuyo costo no depende de la cantidad de reservas, y
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
* **Versionado:** el documento guarda la versión del último cambio aplicado. Se usa para detectar desvíos y como
  `ETag` de la API (ADR-0041).
* Los viajes archivados no están en el documento (ADR-0045), así que su tamaño queda acotado.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón CQRS (separación de modelos de lectura y escritura), en su variante con un solo almacén | Tablas normalizadas para escribir; documento por usuario para leer | QA-2 |
| Patrón *Materialized View* | El documento del panel es una vista precalculada | QA-2, QA-5 |
| Táctica *mantener múltiples copias de los datos* (performance) | Segunda representación de los mismos datos, optimizada para leer | QA-2 |
| Táctica *reducir la sobrecarga computacional* (performance) | Se elimina el armado del panel en cada lectura | QA-2, QA-5 |

### Consequences

* Good, because la lectura del panel es una búsqueda por clave dentro del shard del usuario (ADR-0042): su latencia es
  estable aunque crezcan las reservas.
* Good, because hay coherencia fuerte: no existe un momento en que la reserva cambió y el panel todavía no.
* Good, because no agrega ningún componente de infraestructura.
* Bad, because cada escritura hace más trabajo (cambio + documento + outbox).
* Bad, because hay dos representaciones de los mismos datos; un error de programación puede desincronizarlas. Se
  mitiga con el único escritor, la versión y la reconstrucción.

### Confirmation

* Revisión de la [vista de módulos](../02-views/module-view.md): solo el proyector escribe `panel_por_usuario`.
* Prototipo: el endpoint del panel responde con una lectura por clave; un cambio manual y una novedad aplicada
  actualizan el documento en la misma transacción; regenerar el panel desde las tablas da el mismo resultado.
* Prueba de carga del panel contra QA-2 en el escenario de pico.

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
| Drivers | QA-2, QA-5, QA-1 |
| Vistas afectadas | [module-view](../02-views/module-view.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0001](0001-nucleo-modular-con-procesos-separados.md), [0027](0027-publicacion-del-nucleo.md), [0041](0041-cache-local-y-notificador.md), [0042](0042-particion-de-la-base-por-usuario.md), [0045](0045-ciclo-de-vida-y-archivado-de-viajes.md) |
| Código del prototipo | `prototype/` |
