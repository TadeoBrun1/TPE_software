---
status: "accepted"
date: 2026-10-27
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Despliegue multirregión con región de origen por usuario

## Context and Problem Statement

El enunciado pide que el sistema sea de uso global, accesible en todo momento (máximo 5 minutos por mes de
inactividad no planificada) y "preparado arquitectónicamente para operar en el mercado internacional
(multirregión)". Hay que decidir la estrategia general de despliegue: en cuántas regiones corre el sistema, cómo se
reparten los datos entre ellas y cómo se tolera la falla de una parte de la infraestructura.

## Decision Drivers

* QA-10 (parte multirregión): el sistema debe poder operar en varias regiones y atender a cada usuario desde su
  región de origen, cumpliendo QA-2 y QA-3 aunque esté de viaje. Es un requisito explícito del enunciado.
* QA-4 Disponibilidad: la falla de una instancia o de una zona no debe interrumpir el servicio (estímulo del
  escenario), dentro de un presupuesto de 5 minutos por mes.
* CON-3 (**suposición**): los datos personales se guardan según la normativa de la región del usuario. Si se
  descarta, la decisión sigue siendo válida por QA-10 y QA-4, pero pierde uno de sus argumentos.

Beneficio esperado, que **no** es driver de esta iteración y se valida en la iteración 3: menor latencia de red
para usuarios lejanos (QA-2, QA-3).

## Considered Options

* A. Una sola región con varias zonas de falla
* B. Una región activa con varias zonas, más una región pasiva de recuperación
* C. Una región primaria para escrituras, con réplicas de lectura en todas las regiones
* D. Varias regiones activas; cada usuario tiene una región de origen que guarda sus datos y atiende su tráfico

## Decision Outcome

Chosen option: "D. Región de origen por usuario", because es la única opción que cumple el requisito multirregión
(QA-10) sin replicar los datos personales en todas las regiones (CON-3) y sin conflictos de escritura: cada usuario
escribe siempre en una sola región.

Reglas:

* Cada usuario tiene una **región de origen**, asignada al crear la cuenta según su país.
* Dentro de cada región, todos los procesos (puerta de entrada, núcleo, ingesta, broker y base de datos) tienen
  instancias en **al menos dos zonas de falla**. Esto es lo que cubre el escenario QA-4.
* La base de datos de cada región tiene una réplica sincrónica en otra zona, con conmutación automática.
* La **entrada global** de tráfico es redundante y dirige cada solicitud a la región de origen del usuario. Dentro de
  la región, la puerta de entrada (ADR-0004) reparte la carga entre instancias.
* La región de origen forma parte de la clave de partición de los datos.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón de despliegue por celdas (*Deployment Stamps*, Azure Architecture Center) | Cada región es una copia completa e independiente del sistema que atiende a un subconjunto de usuarios | QA-10, QA-4 |
| Táctica *redundant spare* (disponibilidad), con todas las instancias activas | Instancias en varias zonas atendiendo tráfico al mismo tiempo | QA-4 |
| Tácticas *ping/echo* y *monitor* (disponibilidad) | El balanceador detecta instancias o zonas que no responden y deja de enviarles tráfico | QA-4 |
| Táctica *redundant spare* (disponibilidad), patrón *active redundancy* (*hot spare*) | Réplica sincrónica de la base en otra zona, que toma el control si falla la primaria | QA-4 |
| Partición de datos por usuario (*sharding*) | La región de origen es parte de la clave de partición | QA-10, CON-3 |

Queda sin resolver, y se trata en otras iteraciones:

* Usuarios que viajan fuera de su región: se siguen atendiendo desde su región de origen; si la latencia no
  alcanza, se revisa en la iteración 3.
* Itinerarios compartidos con personas de otra región (RF-08): iteración 4 (resuelto en ADR-0062).
* La parte de idiomas y formatos de QA-10: iteración 4 (resuelto en ADR-0065).
* Las notificaciones de terceros sobre una reserva no traen la región del usuario: hay que ubicarla a partir de la
  reserva (iteración 2).
* La falla de una región completa: no está en el estímulo de QA-4, así que esta ADR no diseña recuperación entre
  regiones. Se analiza en la iteración 3; si se agrega, el respaldo debe quedar en la misma jurisdicción (CON-3).

### Consequences

* Good, because el sistema queda preparado para sumar regiones sin cambiar la estructura: sumar una región es
  desplegar una celda más.
* Good, because la falla de una instancia o zona no corta el servicio, y la falla de una región solo afecta a sus
  usuarios.
* Good, because los datos personales quedan en la región del usuario.
* Bad, because multiplica la infraestructura: cada región tiene todos los procesos.
* Bad, because si cae una región completa, sus usuarios quedan sin servicio hasta que se recupere; se acepta por
  ahora porque ese evento no está en el escenario de QA-4 (ver riesgos de la iteración 1).
* Bad, because la analítica global necesita juntar datos de todas las regiones (se decide en la iteración 4: solo
  almacenes regionales y agregados exportados a mano, ADR-0064).

### Confirmation

Revisión de la [vista de despliegue](../02-views/deployment-view.md). El prototipo simula dos regiones completas que
solo se comunican por el canal entre puertas; la falla de una instancia del núcleo no se simula (hay una por región).

## Pros and Cons of the Options

### A. Una sola región con varias zonas

* Good, because es la opción más simple y cubre el estímulo de QA-4 (falla de instancia o zona).
* Bad, because no cumple el requisito multirregión del enunciado (QA-10).
* Bad, because guarda los datos de todos los usuarios en una sola jurisdicción (CON-3).

### B. Región activa más región pasiva de recuperación

* Good, because cubre además la falla de una región completa con poco costo.
* Bad, because en operación normal todo el tráfico va a una sola región: no es una operación multirregión real
  (QA-10) y todos los datos siguen en una jurisdicción (CON-3).

### C. Región primaria con réplicas de lectura en todas las regiones

* Good, because acerca las lecturas a los usuarios.
* Bad, because copia los datos personales de todos los usuarios en todas las regiones (CON-3).
* Bad, because todas las escrituras viajan a la región primaria, que sigue siendo un único punto crítico.

### D. Región de origen por usuario

* Good, because cumple QA-10 y CON-3, y cubre QA-4 dentro de cada región.
* Bad, because es la opción más compleja de construir y operar.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 1, [iteration-1-structure](../01-add/iteration-1-structure.md) |
| Drivers | QA-10 (multirregión), QA-4, CON-3 (suposición) |
| Vistas afectadas | [deployment-view](../02-views/deployment-view.md) |
| Specs | `specs/openapi/` |
| ADRs relacionadas | [0001](0001-nucleo-modular-con-procesos-separados.md), [0004](0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) |
| Código del prototipo | `prototype/entrada/`, `prototype/sistema.py` y `prototype/docker-compose.yml` (dos regiones) |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #3](https://github.com/TadeoBrun1/TPE_software/pull/3),
merge `05a8fd7` del 2026-10-27. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
