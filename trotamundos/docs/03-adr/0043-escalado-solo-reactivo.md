---
status: "accepted"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: ""
informed: "Tomas Lateana"
---

# Escalado automático solo reactivo, con capacidad mínima de disponibilidad

> El manejo de la demanda que excede la capacidad, que antes formaba parte de esta ADR, se separó en
> [ADR-0047](0047-priorizacion-y-degradacion-ante-sobrecarga.md).

## Context and Problem Statement

El enunciado dice que se **esperan** picos de domingo a lunes y de jueves a viernes, y picos impredecibles ante
disrupciones de viaje. Agregar una instancia tarda en arrancar (se supone de 1 a 3 minutos; depende de la
plataforma que se elija al implementar). Hay que decidir cuándo se agrega capacidad a los procesos sin estado
(núcleo, notificador, ingesta).

## Decision Drivers

* QA-5 Escalabilidad: pico de 5 veces el promedio cumpliendo QA-1 y QA-2.
* QA-2 Latencia web: el panel debe seguir respondiendo en el pico.
* CON-5 (suposición): Trotamundos es una startup con recursos limitados; no se paga capacidad ociosa sin evidencia de
  que se va a usar.

## Considered Options

* A1. Programado por calendario para los picos esperados, más reactivo para las disrupciones
* A2. Solo reactivo, por métricas
* A3. Sobredimensionar de forma permanente para 5 veces el promedio

## Decision Outcome

Chosen option: "A2. Solo reactivo", because paga capacidad solo cuando hay demanda real (CON-5) y un único mecanismo
cubre picos esperados e impredecibles (QA-5). El costo es que los picos esperados también pasan por el tiempo de
arranque; ese riesgo se acepta y se mitiga con el escalado temprano y la priorización de ADR-0047.

**Por qué no se agrega capacidad por calendario, aunque el enunciado nombra los días de pico:**

* Los días de pico son una **expectativa** del enunciado, no una garantía: nada asegura que ocurran todas las
  semanas, con la misma intensidad, ni en todas las regiones (cada región tiene su calendario, feriados y zona
  horaria).
* Levantar instancias en días fijos significa pagar capacidad que puede quedar ociosa (CON-5).
* Si en operación las métricas muestran picos regulares y el escalado reactivo llega tarde, se agrega escalado
  programado **con datos reales**, como complemento. Es una revisión que solo puede hacerse con el sistema en uso.

Reglas:

* **Capacidad mínima = la que exige la disponibilidad:** al menos una instancia de cada proceso por zona de falla
  (QA-4, ADR-0003). No se reserva capacidad extra para picos.
* **Escalado temprano:** se agregan instancias cuando el uso llega al 60 %, no al 100 %. Así, mientras arrancan las
  instancias nuevas, la capacidad disponible absorbe hasta 1,67 veces la carga del momento (100 / 60). El 60 % es un
  parámetro inicial a ajustar con la operación (suposición, derivada del tiempo de arranque supuesto).
* **Métrica por proceso:** solicitudes por segundo y latencia del panel para el núcleo; conexiones abiertas para el
  notificador; antigüedad de la cola para la ingesta.
* **Lo que no escala por esta regla:**
  * El consumo de novedades en el núcleo: la iteración 2 fija 8 shards con un solo consumidor activo cada uno, para
    no perder el orden por usuario (`specs/ingestion-operations.md`). Agregar instancias del núcleo no agrega
    consumidores; cambiar la cantidad de shards es una decisión que se coordina con la iteración 2.
  * La base: las particiones (ADR-0042) no pueden agregar capacidad en minutos, porque crecer implica mover datos.
    Se dimensionan para el pico y se amplían de forma planificada.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *aumentar recursos* (performance) | Escalado automático por métricas de cada proceso | QA-5 |
| Táctica *mantener múltiples copias del cómputo* (performance) | Instancias sin estado detrás de la puerta de entrada | QA-5, QA-2 |

### Consequences

* Good, because no se paga capacidad ociosa en días que quizás no tengan pico.
* Good, because el mismo mecanismo cubre picos esperados e impredecibles.
* Bad, because un aumento brusco de más de 1,67 veces la carga del momento supera la capacidad hasta que arrancan las
  instancias nuevas. En esos minutos QA-2 **puede incumplirse**, aun con la priorización de ADR-0047. **Riesgo
  aceptado**; si en operación ocurre de forma regular, se agrega escalado programado con datos reales.

### Confirmation

Prueba de carga con un escalón de carga creciente: medir cuánto tarda en estar lista la capacidad nueva y la latencia
de `GET /panel` durante ese tiempo. El prototipo local no simula escalado automático: se documenta.

## Pros and Cons of the Options

### A1. Programado más reactivo

* Good, because si el pico esperado ocurre, la capacidad ya está lista.
* Bad, because los días de pico son una expectativa, no una garantía para todas las semanas y regiones: se paga
  capacidad que puede quedar ociosa (CON-5).
* Bad, because hay que mantener un calendario por región; para las disrupciones igual hace falta el reactivo.
* Neutral, because puede agregarse después como complemento si la operación muestra picos regulares.

### A2. Solo reactivo

* Good, because paga solo lo que se usa y es un único mecanismo.
* Bad, because todos los picos pasan por el tiempo de arranque.

### A3. Sobredimensionar

* Good, because nunca falta capacidad hasta 5 veces el promedio.
* Bad, because se paga el pico todo el tiempo (CON-5) y una disrupción mayor a 5 veces tampoco se cubre.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | QA-5, QA-2, CON-5 |
| Vistas afectadas | [deployment-view](../02-views/deployment-view.md) |
| Specs | — |
| ADRs relacionadas | [0003](0003-despliegue-por-regiones-con-region-de-origen.md), [0028](0028-rabbitmq-y-politicas.md), [0042](0042-particion-de-la-base-por-usuario.md), [0047](0047-priorizacion-y-degradacion-ante-sobrecarga.md) |
| Código del prototipo | — |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #6](https://github.com/TadeoBrun1/TPE_software/pull/6),
merge `54122ee` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
