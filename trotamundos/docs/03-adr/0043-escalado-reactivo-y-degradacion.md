---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: ""
informed: "Tomas Lateana"
---

# Escalado automático solo reactivo, y priorización y degradación ante sobrecarga

## Context and Problem Statement

El enunciado describe picos predecibles (domingo a lunes y jueves a viernes) y picos impredecibles ante disrupciones
de viaje, cuando muchos usuarios abren el panel a la vez y además llegan muchas novedades. Agregar instancias tarda
de 1 a 3 minutos en arrancar. Hay que decidir cuándo se agrega capacidad y qué pasa con la demanda que llega antes
de que esa capacidad esté lista.

## Decision Drivers

* QA-5 Escalabilidad: pico de 5 veces el promedio cumpliendo QA-1 y QA-2.
* QA-2 Latencia web: el panel debe seguir respondiendo en el pico.
* QA-4 Disponibilidad: una sobrecarga no debe convertirse en una caída.

## Considered Options

Cuándo agregar capacidad:

* A1. Programado por calendario para los picos conocidos, más reactivo para las disrupciones
* A2. Solo reactivo, por métricas
* A3. Sobredimensionar de forma permanente para 5 veces el promedio

Qué hacer con la demanda que sobra:

* B1. Limitar por cliente, priorizar la lectura del panel y degradar el resto
* B2. Solo limitar por cliente, sin distinguir operaciones
* B3. Encolar todas las solicitudes hasta que haya capacidad

## Decision Outcome

Chosen options: "A2. Solo reactivo" y "B1. Limitar, priorizar y degradar", because se paga capacidad solo cuando
hay demanda real, un único mecanismo cubre picos predecibles e impredecibles, y la priorización protege lo más
importante para el viajero (ver su panel) durante los minutos en que la capacidad nueva todavía no está.

**Por qué no se agrega capacidad por calendario (A1), aunque el enunciado nombra los días de pico:**

* El enunciado dice que se **esperan** picos de domingo a lunes y de jueves a viernes. Es una expectativa, no una
  garantía: nada asegura que ocurran todas las semanas, con la misma intensidad, ni en todas las regiones (cada
  región tiene su calendario, sus feriados y su zona horaria).
* Trotamundos es una startup con recursos limitados. Levantar instancias "por las dudas" en días fijos significa
  pagar capacidad que puede quedar ociosa; escalar cuando la carga sube paga solo lo que se usa.
* Si en operación las métricas muestran picos regulares y el escalado reactivo llega tarde, se agrega escalado
  programado **con datos reales**. Ese cambio no modifica esta decisión de fondo: se suma como complemento. Es una
  revisión que solo puede hacerse con el sistema en uso.

**Escalado (A2):**

* Núcleo, notificador e ingesta escalan por separado, cada uno con su métrica: solicitudes por segundo y latencia
  del panel para el núcleo, conexiones abiertas para el notificador, antigüedad de la cola para la ingesta y el
  consumidor de novedades.
* **Capacidad mínima = la que exige la disponibilidad:** al menos una instancia de cada proceso por zona de falla
  (QA-4, ADR-0003). No se reserva capacidad extra para picos.
* **Escalado temprano:** se agregan instancias cuando el uso llega al 60 %, no al 100 %, para que el 40 % restante
  cubra los minutos de arranque. Es un parámetro a ajustar con la operación.
* **Excepción, la base:** las particiones (ADR-0042) no pueden agregar capacidad en minutos, porque crecer implica
  mover datos. Por eso se dimensionan para el pico y se amplían de forma planificada.

**Sobrecarga (B1):**

| Tipo de operación | Prioridad | Si no hay capacidad |
|---|---|---|
| Leer el panel (`GET /panel`) | Alta | Se atiende |
| Cambios manuales (RF-04) | Media | Se atienden si hay lugar; si no, `503` con `Retry-After` |
| Operaciones secundarias (viajes anteriores, asistencia) | Baja | `429` con `Retry-After` |
| Novedades de la ingesta | — | Esperan en el broker y se aplican al bajar la carga |
| App móvil | — | Muestra su caché local (ADR-0041) |

* La puerta de entrada aplica un límite de solicitudes por cliente y la clasificación por prioridad.
* Las novedades que esperan en el broker consumen el margen de 40 s de QA-1; si el atraso supera ese margen, se
  registra como incumplimiento potencial de QA-1 durante el pico, no se oculta.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *aumentar recursos* (performance) | Escalado automático por métricas de cada proceso | QA-5 |
| Táctica *administrar las solicitudes de trabajo* (performance) | Límite por cliente en la puerta de entrada | QA-5, QA-4 |
| Táctica *priorizar eventos* (performance) | El panel se atiende antes que las operaciones secundarias | QA-2 |
| Táctica *degradación elegante* (disponibilidad) | Operaciones de baja prioridad rechazadas con reintento; app con caché | QA-4 |
| Táctica *limitar la respuesta a eventos* (performance) | Las novedades esperan en el broker en lugar de saturar el núcleo | QA-5 |
| Patrón *Rate Limiting* / *Load Shedding* | Puerta de entrada | QA-5 |

### Consequences

* Good, because el mismo mecanismo cubre picos predecibles e impredecibles.
* Good, because en el peor momento el viajero sigue viendo su panel.
* Good, because no se paga capacidad ociosa en días que quizás no tengan pico.
* Bad, because los picos predecibles también pasan por los minutos de arranque: dependen del escalado temprano y de
  la priorización. **Riesgo aceptado**; si en operación no alcanza, se agrega escalado programado con datos reales.
* Bad, because durante un pico fuerte QA-1 puede atrasarse para algunas actualizaciones.

### Confirmation

* Prueba de carga con un escalón de 5 veces el promedio: el 95 % de `GET /panel` sigue en 800 ms o menos mientras
  arrancan instancias nuevas.
* Prueba de sobrecarga: las operaciones de baja prioridad reciben `429` y el panel sigue respondiendo.

## Pros and Cons of the Options

### A1. Programado más reactivo

* Good, because si el pico ocurre, la capacidad ya está lista.
* Bad, because los días de pico son una expectativa del enunciado, no una garantía para todas las semanas y regiones:
  se paga capacidad que puede quedar ociosa.
* Bad, because hay que mantener un calendario por región; para las disrupciones igual hace falta el reactivo.
* Neutral, because puede agregarse después como complemento si la operación muestra picos regulares.

### A3. Sobredimensionar

* Good, because nunca falta capacidad hasta 5 veces el promedio.
* Bad, because se paga el pico todo el tiempo y una disrupción mayor a 5 veces tampoco se cubre.

### B2. Solo limitar

* Good, because es simple y protege al núcleo.
* Bad, because un usuario puede quedarse sin ver su panel justo durante la disrupción.

### B3. Encolar todo

* Good, because no rechaza nada.
* Bad, because las consultas del panel superarían los 800 ms mientras esperan (QA-2).

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 3, [iteration-3-query-scale](../01-add/iteration-3-query-scale.md) |
| Drivers | QA-5, QA-2, QA-4 |
| Vistas afectadas | [deployment-view](../02-views/deployment-view.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) (respuestas `429` y `503`) |
| ADRs relacionadas | [0004](0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md), [0028](0028-rabbitmq-y-politicas.md), [0041](0041-cache-local-y-notificador.md), [0042](0042-particion-de-la-base-por-usuario.md) |
| Código del prototipo | `prototype/` |
