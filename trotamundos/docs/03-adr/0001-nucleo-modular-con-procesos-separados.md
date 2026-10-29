---
status: "accepted"
date: 2026-10-27
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Núcleo como monolito modular, con ingesta y analítica como procesos separados

## Context and Problem Statement

Trotamundos tiene tres cargas de trabajo con comportamientos muy distintos:

* la **consulta y gestión** de viajes por parte de los viajeros (muchas lecturas cortas, con picos fuertes);
* la **ingesta** de reservas desde correos y sistemas de terceros (trabajo continuo, en segundo plano, que depende de
  sistemas externos que fallan o se demoran);
* la **analítica** del equipo de datos (consultas pesadas y largas).

Hay que decidir cómo se divide el sistema en elementos de ejecución para que esas cargas escalen y fallen por
separado, sin partir en pedazos un dominio (viajes, reservas, permisos) que necesita consistencia.

## Decision Drivers

* QA-5 Escalabilidad: 2 millones de usuarios activos semanales y picos de 5 veces el promedio; cada carga debe
  poder crecer por su cuenta.
* QA-4 Disponibilidad: si falla la ingesta o la analítica, los viajeros tienen que poder seguir viendo sus viajes.
* QA-1 Frescura: la ingesta debe poder agregar capacidad para cumplir los 5 minutos sin afectar la consulta.
* QA-9 Evolucionabilidad: agregar un medio de transporte (trenes, autobuses) sin modificar los existentes.
* RF-05 Ciclo de vida del viaje: asociar una reserva a un viaje, cambiar su estado y archivar el viaje son
  operaciones sobre datos muy relacionados que deben quedar consistentes.

## Considered Options

* A. Monolito modular en un único despliegue
* B. Núcleo como monolito modular, con ingesta y analítica como procesos separados
* C. Microservicios por capacidad (viajes, reservas, usuarios, compartición, ingesta, analítica)
* D. Funciones por evento (serverless)

## Decision Outcome

Chosen option: "B. Núcleo como monolito modular, con ingesta y analítica como procesos separados", because separa
las tres cargas que más difieren (y las que tienen modos de falla distintos) y mantiene juntos, en un mismo proceso
y una misma transacción, los datos del dominio que deben ser consistentes.

Estructura resultante:

* **Núcleo:** un único desplegable, organizado en módulos (viajes y ciclo de vida, reservas, usuarios y
  preferencias, compartición). Es el único dueño del estado oficial de viajes y reservas. No guarda estado de
  sesión en memoria, de modo que se pueden agregar instancias detrás de un balanceador.
* **Ingesta:** proceso separado que sondea correos y consulta a terceros. Tiene un **adaptador por proveedor** y
  traduce todo a un **modelo canónico de reserva**. No escribe en la base del núcleo: le entrega novedades
  (ver ADR-0002).
* **Analítica:** proceso separado que no comparte recursos con la consulta. Cómo se alimenta y dónde guarda los
  datos se decide en la iteración 4 (resuelto en ADR-0064).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón monolito modular | Núcleo con módulos de responsabilidad clara y dependencias controladas | RF-05, QA-9 |
| Táctica *dividir módulo* / *aumentar cohesión* (modificabilidad) | Ingesta y analítica salen del núcleo porque cambian y escalan por motivos distintos | QA-5, QA-9 |
| Táctica *mantener múltiples copias del cómputo* e *introducir concurrencia* (performance) | Núcleo sin estado, con varias instancias detrás de un balanceador | QA-5 |
| Táctica *degradación elegante* (disponibilidad) | Si la ingesta cae, la consulta sigue respondiendo con los últimos datos | QA-4 |
| Patrón *Adapter* + *Canonical Data Model*; tácticas *encapsular* y *adaptar la interfaz* (integrabilidad) | Un adaptador por proveedor traduce su API estándar al modelo canónico | QA-9, CON-1 |
| Táctica *restringir dependencias* (modificabilidad) | La ingesta no conoce el esquema de la base del núcleo | QA-9 |

La posible separación entre lectura y escritura dentro del núcleo (para QA-2) no se decide acá: se analiza en la
iteración 3, sobre el núcleo que define esta ADR.

### Consequences

* Good, because la consulta, la ingesta y la analítica escalan con recursos propios.
* Good, because la consulta sigue sirviendo datos, aunque algo viejos, si la ingesta falla.
* Good, because las operaciones de viajes y reservas son transacciones locales, sin coordinación distribuida.
* Good, because los módulos del núcleo tienen límites claros y permiten extraer un servicio más adelante si alguno
  necesita escalar por separado.
* Bad, because hay varios procesos que se comunican y pueden fallar por separado (se resuelve en ADR-0002).
* Bad, because el núcleo escala como una unidad: si un módulo necesita mucho más que el resto, se escala todo.
* Bad, because hay que vigilar que los módulos del núcleo no se acoplen entre sí con el tiempo.

### Confirmation

* Revisión de la [vista de módulos](../02-views/module-view.md): ningún módulo del núcleo depende de la ingesta y
  los adaptadores no dependen entre sí.
* Prueba en el prototipo: con la ingesta detenida, la consulta de itinerarios sigue respondiendo.

## Pros and Cons of the Options

### A. Monolito modular en un único despliegue

* Good, because es la estructura con menos piezas y sin comunicación entre procesos.
* Bad, because todas las cargas escalan juntas: para absorber un pico de ingesta hay que escalar también la consulta
  y al revés (QA-5).
* Bad, because una consulta analítica pesada o un error en la ingesta afecta a los viajeros (QA-4).

### B. Núcleo como monolito modular, con ingesta y analítica como procesos separados

* Good, because cada carga escala y falla por separado.
* Good, because el dominio que necesita consistencia queda en un solo proceso.
* Bad, because exige comunicación entre procesos y manejo de fallas parciales.

### C. Microservicios por capacidad

* Good, because da la mayor independencia de escala y de despliegue por capacidad.
* Bad, because viajes, reservas y compartición forman un dominio muy cohesivo: separarlos obliga a coordinar
  transacciones entre servicios (sagas) para operaciones cotidianas como asociar una reserva a un viaje (RF-05).
* Bad, because armar el panel de un viajero requiere componer datos de varios servicios en cada consulta, lo que
  suma latencia (QA-2).
* Neutral, because las cargas que realmente necesitan escalar por separado (ingesta y analítica) ya quedan
  separadas en la opción B.

### D. Funciones por evento (serverless)

* Good, because escala automáticamente y encaja con el trabajo por eventos de la ingesta.
* Bad, because el arranque en frío de las funciones agrega latencia variable a la consulta (QA-2, QA-3).
* Bad, because el sondeo continuo de millones de buzones choca con los límites de duración de las funciones.
* Bad, because ata el diseño a los servicios de un proveedor de nube (afecta QA-9).
* Neutral, because puede reconsiderarse para partes de la ingesta en la iteración 2.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 1, [iteration-1-structure](../01-add/iteration-1-structure.md) |
| Drivers | CRN-1, QA-5, QA-4, QA-1, QA-9, RF-05 |
| Vistas afectadas | [module-view](../02-views/module-view.md), [cc-view](../02-views/cc-view.md) |
| Specs | — |
| ADRs relacionadas | [0002](0002-mensajeria-persistente-con-publicacion-suscripcion.md), [0003](0003-despliegue-por-regiones-con-region-de-origen.md), [0004](0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) |
| Código del prototipo | `prototype/nucleo/`, `prototype/ingesta/` y `prototype/notificador/` (procesos separados); prueba `test_consultas_con_la_ingesta_detenida` |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #3](https://github.com/TadeoBrun1/TPE_software/pull/3),
merge `05a8fd7` del 2026-10-27. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
