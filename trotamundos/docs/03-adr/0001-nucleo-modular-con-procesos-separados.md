---
status: "proposed"
date: 2026-10-27
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Núcleo modular con ingesta y analítica como procesos separados

## Context and Problem Statement

Las consultas de los viajeros, la importación de datos externos y los análisis tienen cargas muy distintas. Hay que
elegir cómo dividir el sistema para que escalen y fallen por separado, sin superar lo que un equipo de dos personas
puede construir y operar en el plazo del TPE.

## Decision Drivers

* QA-5 Escalabilidad: picos de 5 veces el promedio con 2 millones de usuarios activos semanales.
* QA-4 Disponibilidad: 5 minutos de inactividad no planificada por mes; la consulta no debe caer si falla otra carga.
* QA-1 Frescura: la ingesta debe poder crecer sin afectar la consulta.
* QA-9 Evolucionabilidad: agregar un medio de transporte sin modificar los existentes.
* Viabilidad: 2 personas, 10 días y un prototipo local.

## Considered Options

* A. Monolito modular en un único despliegue
* B. Núcleo modular, con ingesta y analítica como procesos separados
* C. Microservicios por capacidad
* D. Funciones por evento (serverless)

## Decision Outcome

Chosen option: "B. Núcleo modular, con ingesta y analítica como procesos separados", because separa las tres cargas
que más difieren sin pagar el costo operativo de muchos servicios.

El núcleo administra viajes, reservas, permisos y consultas. Sus módulos tienen responsabilidades distintas, pero se
construyen como una misma aplicación. Esa aplicación tiene **dos perfiles de despliegue** con el mismo código: uno de
consulta (lecturas) y otro de gestión (escrituras), para que una falla en la validación de reservas no tire las
lecturas.

### Consequences

* Good, because la consulta, la ingesta y la analítica escalan con recursos propios.
* Good, because la consulta sigue sirviendo datos, aunque algo viejos, si la ingesta falla.
* Good, because los módulos permiten extraer un servicio más adelante si hace falta.
* Bad, because hay varios procesos y hay que manejar su comunicación y sus fallos (ver ADR-0002).
* Bad, because el núcleo sigue siendo una unidad de código grande: hay que cuidar los límites entre módulos.

### Confirmation

Revisión de la vista de módulos (sin dependencias cruzadas entre módulos) y prueba en el prototipo: con la ingesta
detenida, la consulta responde.

## Pros and Cons of the Options

### A. Monolito modular en un único despliegue

* Good, because es lo más simple de construir y operar.
* Bad, because todas las cargas escalan juntas y una falla las afecta a todas (QA-5, QA-4).

### B. Núcleo modular, con ingesta y analítica como procesos separados

* Good, because cada carga escala y falla por separado.
* Good, because es viable para el equipo.
* Bad, because exige mensajería y manejo de fallos parciales.

### C. Microservicios por capacidad

* Good, because da la mayor independencia de escala y despliegue.
* Bad, because multiplica la operación, las comunicaciones y los contratos para dos personas y 10 días.

### D. Funciones por evento (serverless)

* Good, because escala muy bien la ingesta.
* Bad, because el prototipo local no lo demuestra y ata el diseño a una plataforma.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 1, [iteration-1-structure](../01-add/iteration-1-structure.md) |
| Drivers | CRN-1, QA-5, QA-4, QA-1, QA-9 |
| Vistas afectadas | [module-view](../02-views/module-view.md), [cc-view](../02-views/cc-view.md) |
| Specs | — |
| ADRs relacionadas | [0002](0002-mensajeria-persistente-con-publicacion-suscripcion.md), [0003](0003-almacen-analitico-separado.md), [0004](0004-despliegue-por-regiones-con-region-de-origen.md) |
| Código del prototipo | `prototype/` |
