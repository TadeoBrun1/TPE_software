---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Reserva con campos comunes y un bloque de detalles con esquema propio por tipo

## Context and Problem Statement

QA-9 exige agregar un medio de transporte nuevo en 10 días-persona o menos, sin modificar el código de los medios
existentes. La iteración 2 ya aísla cada proveedor detrás de un adaptador (ADR-0023), pero cada medio tiene datos
propios (andén, vagón, asiento, puerta de embarque, número de habitación) y falta decidir cómo se representan en el
modelo de reserva, en el panel y en la API sin que cada medio nuevo obligue a cambiar el núcleo.

## Decision Drivers

* QA-9: agregar un medio sin tocar el código de los existentes, en 10 días-persona o menos.
* RF-05: el panel y la lógica de viajes trabajan igual para todos los medios.
* Spec-driven: los datos de cada medio deben estar definidos en un contrato.

## Considered Options

* A. Campos comunes a todos los medios y un bloque `detalles` con esquema propio por tipo, versionado en `specs/`
* B. Tipos fijos por medio, con sus campos propios en el modelo
* C. Solo campos comunes; lo específico en una nota de texto

## Decision Outcome

Chosen option: "A. Campos comunes más detalles por tipo", because la lógica del núcleo (viajes, asignación por
fechas, archivado, panel) usa solo los campos comunes, y lo propio de cada medio vive en un esquema aparte.

Reglas:

* **Campos comunes:** tipo, estado, inicio y fin con su zona horaria, lugar (y lugar de llegada en los traslados, por
  ejemplo el código del aeropuerto o la estación), precio, proveedor y referencia, notas. Son los únicos que usan los módulos `viajes`, `reservas` y `panel`, y alcanzan para mostrar
  cualquier reserva en una vista genérica.
* **Tipo como código abierto:** `type` es un código (`flight`, `hotel`, `car`, `train`, `bus`, ...) y no una lista
  cerrada en los contratos. Un cliente que recibe un tipo que no conoce lo muestra con la vista genérica, así que
  agregar un tipo no rompe a las versiones viejas de la app.
* **Detalles:** un bloque `details` con el identificador de su esquema (por ejemplo `train.v1`) y sus campos. Cada
  esquema es un archivo en `specs/schemas/`. El módulo `esquemas-detalles` del núcleo carga los archivos registrados
  en su configuración al arrancar (no se compilan dentro del código), valida el bloque contra su esquema, y el núcleo
  lo guarda tal cual sin interpretarlo; el panel lo devuelve y el cliente lo muestra según el esquema. Un bloque con
  un esquema que el núcleo no conoce, o que no lo cumple, se rechaza (`400` en la API; la novedad queda para revisión
  en la ingesta).
* **Qué no va en `details`:** códigos de reserva, números de billete, nombres de pasajeros ni otros datos personales.
  Esos datos van en los campos comunes (`providerReference`, notas), que la vista compartida y la analítica ya
  filtran (ADR-0061, ADR-0064). Así, el bloque se puede mostrar en un viaje compartido sin que el núcleo lo
  interprete.
* **Agregar un medio nuevo** (recorrido de QA-9 con un medio que hoy no existe, por ejemplo ferry):
  1. esquema `specs/schemas/details-ferry.v1.json` y el código `ferry` en la lista de tipos conocidos del contrato;
  2. adaptador del proveedor en la ingesta (ADR-0023), que produce los campos comunes y los detalles;
  3. registrar el esquema en el núcleo (configuración: identificador y archivo), sin cambiar código de sus módulos;
  4. vista del detalle en los clientes y textos en los catálogos (ADR-0065).

  No cambia el código de vuelos, hoteles, autos, trenes ni autobuses, ni la lógica de viajes del núcleo. El
  esfuerzo estimado (suposición): 1 día el esquema y su registro, 4 a 6 días el adaptador, 2 días las vistas de los
  clientes y 1 día de pruebas; entre 8 y 10 días-persona. Si el proveedor no tiene API y llega solo por correo, el
  adaptador es un extractor de correos nuevo y puede superar el límite (riesgo).
* **Versionado:** todo cambio en un esquema, incluso agregar un campo opcional, crea una versión nueva (`ferry.v2`),
  porque los esquemas no admiten campos extra. Un identificador (`ferry.v1`) siempre designa el mismo contenido. Las
  versiones conviven mientras haya reservas con la anterior; un adaptador manda la versión nueva recién cuando el
  núcleo la tiene registrada.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *abstraer servicios comunes* (modificabilidad) | Campos comunes que usa toda la lógica del núcleo | QA-9 |
| Táctica *encapsular* (modificabilidad) | Lo propio de cada medio queda en su bloque de detalles | QA-9 |
| Táctica *diferir el enlace* (modificabilidad) | Los esquemas se registran por configuración y se cargan al arrancar; el de cada bloque se elige por su identificador | QA-9 |
| Táctica *restringir dependencias* (modificabilidad) | El núcleo y el panel no dependen de los campos propios de cada medio | QA-9 |
| Táctica *adherir a estándares* (integrabilidad) | Esquemas en JSON Schema dentro de `specs/` | QA-9 |

### Consequences

* Good, because agregar un medio es agregar un esquema, un adaptador y vistas, sin tocar la lógica del núcleo.
* Good, because cada medio tiene su contrato versionado (spec-driven).
* Bad, because el núcleo no puede hacer reglas de negocio sobre los detalles (por ejemplo, avisar un cambio de andén
  como cambio importante) sin conocer ese esquema.
* Bad, because los clientes tienen que agregar la vista de cada medio nuevo; hasta entonces lo muestran genérico.
* Bad, because abrir el tipo en los contratos cambia la versión 0.1.0 de `booking.change.detected.v1` (contrato de
  diseño de la iteración 2, sin consumidores en producción).

### Confirmation

Prueba de QA-9: agregar el medio "ferry" en el prototipo con un adaptador simulado, su esquema y su vista, y
verificar con el historial de cambios que no se modificó código de los otros medios ni de los módulos `viajes`,
`reservas` y `panel`. Registrar el esfuerzo real.

## Pros and Cons of the Options

### A. Campos comunes más detalles por tipo

* Good, because aísla lo propio de cada medio.
* Bad, because el núcleo no razona sobre los detalles.

### B. Tipos fijos por medio

* Good, because el modelo es estricto y el núcleo conoce todos los campos.
* Bad, because cada medio nuevo toca el núcleo, la API y el panel: no cumple "sin modificar el código existente".

### C. Solo campos comunes

* Good, because es lo más simple.
* Bad, because se pierden datos útiles para el viajero (andén, asiento).

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 4, [iteration-4-security-evolvability](../01-add/iteration-4-security-evolvability.md) |
| Drivers | QA-9, RF-05 |
| Vistas afectadas | [domain-model](../02-views/domain-model.md), [module-view](../02-views/module-view.md) |
| Specs | [details-train.v1.json](../../specs/schemas/details-train.v1.json), [details-flight.v1.json](../../specs/schemas/details-flight.v1.json), [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml), [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml) |
| ADRs relacionadas | [0023](0023-adaptadores-proveedores.md), [0040](0040-modelo-de-lectura-del-panel.md), [0065](0065-internacionalizacion-en-el-cliente.md) |
| Código del prototipo | `prototype/` |
