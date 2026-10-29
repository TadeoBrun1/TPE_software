---
status: "accepted"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: ""
informed: "Tomas Lateana"
---

# Partición de la base operativa por usuario en varios nodos, cada uno con réplica sincrónica

## Context and Problem Statement

ADR-0003 fijó para cada región una base con réplica sincrónica en otra zona y conmutación automática, y que la región
de origen forma parte de la clave de partición. No fijó si la región usa **un solo** par primaria/réplica o **varios**.
Hay que decidirlo, junto con cómo se detectan las fallas y qué pasa cuando cae una zona.

Estimación de carga (suposición a partir de QA-5, a validar con pruebas): con 2 millones de usuarios activos por
semana y hasta 50 cargas del panel por usuario y semana, la lectura **global** promedio es de unas 165 solicitudes/s,
y con el pico de 5 veces (que ya incluye las disrupciones), unas 830/s. La iteración 2 usa como hipótesis de prueba
50 a 250 novedades/s **por región**. Con estas cifras, un solo par primaria/réplica por región alcanza en
rendimiento. Por eso la decisión **no** se toma por volumen de lecturas sino por disponibilidad.

## Decision Drivers

* QA-4 Disponibilidad: máximo 5 minutos por mes de inactividad no planificada, con detección en 30 s y redirección en
  60 s. Cada conmutación de la base consume parte de ese presupuesto para todos los usuarios afectados.
* QA-5 Escalabilidad: 15 millones de cuentas y sus reservas, sin rediseño cuando crece una región.
* ADR-0040: todos los datos de un usuario (tablas, panel y outbox) deben confirmarse en una transacción local.
* CON-3 (suposición): los datos no salen de la región de origen.

## Considered Options

* A. Un solo par primaria/réplica sincrónica por región (la base que dejó ADR-0003)
* B. Particiones por usuario repartidas en varios nodos, cada nodo con su primaria y su réplica sincrónica
* C. Base SQL distribuida que se particiona, replica y conmuta sola

## Decision Outcome

Chosen option: "B. Particiones por usuario en varios nodos", because cada falla de la base afecta solo a los usuarios
del nodo caído y no a toda la región, lo que reduce la inactividad que sufre cada usuario frente al presupuesto
mensual de QA-4, y porque mantiene todos los datos de un usuario en un solo nodo (la transacción de ADR-0040 sigue
siendo local).

Reglas:

* La base de cada región se divide en **particiones lógicas** (por ejemplo 256) según un hash del identificador de
  usuario. Las particiones lógicas se reparten en **nodos físicos**; al principio pocos nodos, cada uno con muchas
  particiones. Para crecer se mueven particiones a nodos nuevos sin cambiar la función de partición.
* La **unidad de falla es el nodo**, no la partición: si un nodo cae, se afectan todos los usuarios de las
  particiones que tiene. Con pocos nodos al principio, el aislamiento es limitado.
* Cada nodo tiene una **primaria** en una zona y una **réplica sincrónica** en otra; una escritura se confirma cuando
  está en las dos. Las primarias de los distintos nodos se reparten entre zonas.
* **Detección:** un monitor consulta a cada primaria cada 5 s (*ping/echo*); tras 6 consultas sin respuesta (30 s)
  la declara caída.
* **Conmutación:** el monitor promueve la réplica, aísla a la primaria anterior para que no siga aceptando escrituras
  y actualiza el ruteo de particiones del núcleo. Objetivo: servicio restablecido en 60 s, sin pérdida de escrituras
  confirmadas.
* **Monitor sin punto único de falla:** tres instancias, una en cada zona (A, B y la zona C que ya existe por el
  broker, ADR-0028). Una promoción necesita el acuerdo de dos de las tres, lo que evita que dos réplicas se promuevan
  a la vez (*split-brain*).
* **Escrituras cuando un nodo se queda con una sola copia.** Pasa en dos casos: (a) cae la primaria y se promueve
  la réplica, o cae una zona entera; (b) cae solo la réplica y la primaria sigue viva. En ambos casos no hay segunda
  copia que confirme, y hay que elegir entre bloquear las escrituras hasta tener réplica (más durabilidad, pero los
  usuarios del nodo no pueden escribir durante minutos u horas) o seguir aceptándolas con una sola copia.
  **Política elegida: se siguen aceptando escrituras con durabilidad reducida**, porque QA-4 pide que el servicio
  siga disponible, y bloquear escrituras durante toda la reconstrucción consumiría el presupuesto mensual de 5
  minutos muchas veces. Concretamente:
  * la confirmación sincrónica se suspende para ese nodo (el monitor lo marca como "con una sola copia");
  * se crea de inmediato una réplica nueva (en la zona C si cayó una zona entera, o en la misma zona si solo cayó la
    réplica); mientras se copia, recibe las escrituras nuevas en forma asincrónica;
  * cuando la réplica nueva alcanza a la primaria, se vuelve a exigir la confirmación en las dos copias;
  * el tiempo en esa situación se mide y genera alerta.

  Así, los "60 s" restablecen el **servicio**; la **durabilidad completa** se recupera cuando termina la copia. Si
  durante esa ventana falla también la única copia que queda, se pierden las escrituras confirmadas que todavía no
  llegaron a la réplica nueva (riesgo aceptado y registrado).
* Todo lo de un usuario (viajes, reservas, `panel_por_usuario`, outbox, control de novedades) vive en su partición.
* Relación con el consumo de novedades (iteración 2): los 8 shards de RabbitMQ y las particiones de la base usan
  funciones de hash distintas. No hace falta alinearlas, porque cada novedad es de un solo usuario y se aplica en
  una transacción de la partición de ese usuario.

Qué **no** cubre: la pérdida simultánea de dos zonas o de la región entera (riesgo de región ya aceptado). No se
recupera desde otra región porque las otras regiones no tienen estos datos (ADR-0003, CON-3).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Sharding* | Particiones lógicas por hash de usuario en varios nodos | QA-4, QA-5 |
| Táctica *redundant spare* (disponibilidad), con el patrón *active redundancy* (*hot spare*) | Réplica sincrónica que recibe cada escritura y toma el control si falla la primaria | QA-4 |
| Tácticas *ping/echo* y *monitor* (disponibilidad) | El monitor consulta a cada primaria y decide la promoción | QA-4 |
| Táctica *reconfiguration* (disponibilidad) | Se actualiza el ruteo de particiones tras la promoción | QA-4 |
| Táctica *aumentar recursos* (performance) | Nodos nuevos a los que se mueven particiones | QA-5 |

### Consequences

* Good, because una falla de la base afecta a una fracción de los usuarios (los del nodo caído) y no a toda la región.
* Good, because la región crece agregando nodos, sin cambiar la función de partición.
* Good, because la réplica sincrónica evita perder escrituras confirmadas.
* Bad, because al principio, con pocos nodos, el aislamiento es limitado: cada nodo tiene una fracción grande de los
  usuarios.
* Bad, because mover particiones entre nodos es una operación delicada que hay que automatizar.
* Bad, because las consultas que cruzan usuarios tocan varios nodos. El caso conocido es un itinerario compartido
  (iteración 4): la lectura se hace en la partición del dueño del viaje.
* Bad, because cuando un nodo queda con una sola copia (cae la primaria, la réplica o una zona), hay una ventana con
  durabilidad reducida hasta reconstruir la réplica: el servicio sigue, pero una segunda falla en esa ventana pierde
  datos.

### Confirmation

* Revisión de la [vista de despliegue](../02-views/deployment-view.md).
* Prototipo: 256 particiones lógicas repartidas en dos nodos (dos bases del mismo motor), con ruteo por hash de
  usuario. La conmutación entre zonas, el monitor y la suspensión de la confirmación sincrónica se documentan, pero
  no se simulan en el prototipo local.
* En una prueba de infraestructura: apagar solo la réplica y verificar que la primaria sigue aceptando escrituras;
  apagar la primaria y verificar la promoción en 60 s; medir cuánto dura la reconstrucción.

## Pros and Cons of the Options

### A. Un solo par primaria/réplica por región

* Good, because es la más simple: no hay ruteo de particiones ni movimiento de datos, y cumple la coherencia de
  ADR-0040 y los tiempos de detección y conmutación.
* Bad, because cada falla de la primaria deja sin escrituras ni lecturas a **todos** los usuarios de la región durante
  la conmutación: cada falla consume el presupuesto mensual de QA-4 de todos a la vez.
* Bad, because crecer la región exige agrandar una sola máquina hasta su límite.

### B. Particiones en varios nodos

* Good, because aísla fallas por nodo y crece agregando nodos.
* Bad, because requiere ruteo, movimiento de particiones y un monitor más elaborado.

### C. SQL distribuida

* Good, because particiona, replica y conmuta sola.
* Bad, because ata el diseño a un producto concreto y cada escritura paga consenso entre réplicas.
* Neutral, because es una forma válida de implementar la opción B si se elige un producto así al implementar.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | QA-4, QA-5, CON-3 |
| Vistas afectadas | [deployment-view](../02-views/deployment-view.md), [cc-view](../02-views/cc-view.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | — |
| ADRs relacionadas | [0003](0003-despliegue-por-regiones-con-region-de-origen.md), [0028](0028-rabbitmq-y-politicas.md), [0040](0040-modelo-de-lectura-del-panel.md), [0043](0043-escalado-solo-reactivo.md) |
| Código del prototipo | `prototype/nucleo/datos/ruteo.py` (256 particiones en dos nodos) |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #6](https://github.com/TadeoBrun1/TPE_software/pull/6),
merge `54122ee` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
