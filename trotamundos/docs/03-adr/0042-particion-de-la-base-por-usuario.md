---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: ""
informed: "Tomas Lateana"
---

# Partición de la base operativa por usuario, con réplica sincrónica por partición

## Context and Problem Statement

ADR-0003 decidió que cada región guarda los datos de sus usuarios y que la región de origen forma parte de la clave de
partición, pero no cómo se organiza la base **dentro** de una región. Hay que decidir cómo escala esa base con la
cantidad de cuentas y cómo se limita el efecto de una falla.

Estimación de carga (suposición a partir de QA-5, a validar con pruebas): con 2 millones de usuarios activos por
semana y hasta 50 cargas del panel por usuario y semana (abrir la app o la web, recargar, volver a la pantalla), la lectura global promedio es de unas 165 solicitudes/s, y con el pico de
5 veces, unas 830/s; una disrupción grande suma algunos cientos por segundo. Las escrituras vienen de la ingesta
(la iteración 2 estima 50 a 250 novedades/s por región) y de los cambios manuales. Con estas cifras una sola base por
región alcanza **hoy** en rendimiento; la decisión se toma por crecimiento y, sobre todo, por aislamiento de fallas.

## Decision Drivers

* QA-5 Escalabilidad: 15 millones de cuentas y crecimiento sin rediseño.
* QA-4 Disponibilidad: detección en 30 s y redirección en 60 s; una falla de la base no debe dejar sin servicio a
  toda la región.
* ADR-0040: todos los datos de un usuario (tablas, panel y outbox) deben poder confirmarse en una transacción local.
* CON-3 (suposición): los datos no salen de la región de origen.

## Considered Options

* A. Una base primaria por región, con réplicas de lectura
* B. Particiones (*shards*) por usuario, cada una con primaria y réplica sincrónica en otra zona
* C. Base SQL distribuida que se particiona y replica sola

## Decision Outcome

Chosen option: "B. Particiones por usuario con réplica sincrónica", because mantiene todos los datos de un usuario en
una sola partición (la transacción de ADR-0040 sigue siendo local), escala agregando particiones y hace que una falla
afecte solo a los usuarios de una partición.

Reglas:

* La base de cada región se divide en **particiones lógicas** (por ejemplo 256) según un hash del identificador de
  usuario. Al principio, varias particiones lógicas comparten un mismo nodo físico; para crecer se mueven particiones
  lógicas a nodos nuevos, sin cambiar la función de partición.
* Cada nodo físico tiene una **primaria** en una zona y una **réplica sincrónica** en otra zona: una escritura se
  confirma cuando está en las dos.
* Un monitor de salud consulta cada primaria (heartbeat). Si no responde en 30 s, promueve la réplica a primaria y el
  núcleo actualiza su tabla de ruteo de particiones. Objetivo: servicio restablecido en 60 s, sin pérdida de datos.
* Después de una conmutación se crea una réplica nueva para volver a tener dos copias.
* Todo lo de un usuario (viajes, reservas, `panel_por_usuario`, outbox, control de novedades) vive en su partición.

Qué **no** cubre: la pérdida simultánea de las dos copias (dos zonas o la región entera). Es el riesgo de falla de
región ya registrado; las particiones lo acotan a los usuarios afectados, pero no lo resuelven. No se recupera desde
otra región porque las otras regiones no tienen estos datos (ADR-0003, CON-3).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Sharding* | Particiones lógicas por hash de usuario | QA-5 |
| Táctica *redundancia pasiva* (disponibilidad) | Réplica sincrónica que toma el control si falla la primaria | QA-4 |
| Táctica *monitoreo / heartbeat* (disponibilidad) | Detección de primarias caídas en 30 s | QA-4 |
| Táctica *aumentar recursos* (performance) | Mover particiones lógicas a nodos nuevos | QA-5 |

### Consequences

* Good, because escalar es agregar nodos y mover particiones, sin rediseñar ni cambiar la función de partición.
* Good, because una falla afecta a una parte de los usuarios, y solo durante la conmutación (QA-4).
* Good, because la réplica sincrónica evita perder escrituras confirmadas.
* Bad, because mover particiones entre nodos es una operación delicada que hay que automatizar.
* Bad, because las consultas que cruzan usuarios tocan varias particiones. El caso conocido es un itinerario
  compartido (iteración 4): la lectura se hace en la partición del dueño del viaje.
* Bad, because la réplica sincrónica suma la latencia entre zonas a cada escritura (normalmente pocos milisegundos).

### Confirmation

* Revisión de la [vista de despliegue](../02-views/deployment-view.md).
* Prototipo: dos particiones lógicas en un mismo motor de base, con ruteo por hash de usuario. La conmutación entre
  zonas se documenta, pero no se simula en el prototipo local.

## Pros and Cons of the Options

### A. Primaria por región con réplicas de lectura

* Good, because es la más simple y no requiere ruteo de particiones.
* Bad, because las réplicas de lectura van atrasadas: un usuario que cambia una reserva puede no verla al recargar,
  lo que rompe la coherencia de ADR-0040.
* Bad, because la primaria es un punto único para todas las escrituras de la región, y su falla afecta a todos.

### B. Particiones por usuario con réplica sincrónica

* Good, because escala, aísla fallas y mantiene la transacción local.
* Bad, because requiere ruteo y movimiento de particiones.

### C. SQL distribuida

* Good, because particiona, replica y conmuta sola.
* Bad, because ata el diseño a un producto concreto y cada escritura paga consenso entre réplicas.
* Neutral, because es una forma válida de implementar la opción B si se elige un producto así al implementar.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | QA-5, QA-4, CON-3 |
| Vistas afectadas | [deployment-view](../02-views/deployment-view.md), [cc-view](../02-views/cc-view.md) |
| Specs | — |
| ADRs relacionadas | [0003](0003-despliegue-por-regiones-con-region-de-origen.md), [0040](0040-modelo-de-lectura-del-panel.md), [0043](0043-escalado-reactivo-y-degradacion.md) |
| Código del prototipo | `prototype/` |
