---
status: "accepted"
date: 2026-11-22
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Ranking de ofertas por características, aprendido del feedback, con un modelo regional versionado

## Context and Problem Statement

Con las ofertas alternativas en la mano (ADR-0082), hay que decidir cuáles se muestran y en qué orden, y cómo el
feedback del viajero (aceptar, rechazar, ajustar parámetros) refina el modelo, como pide el enunciado
(*human-in-the-loop*). Las ofertas de una disrupción son casi siempre nuevas (otro vuelo, otro hotel) y muchos
viajeros tienen poco historial, así que el método tiene que funcionar sin datos previos de ese viajero ni de esa
oferta.

## Decision Drivers

* RF-09.3 y QA-13: reordenar en 2 s respetando los límites explícitos; el feedback entra al modelo en 24 h.
* QA-15: versiones nuevas del modelo con despliegue para el 5 % y vuelta atrás en 5 minutos.
* QA-11: el ranking no puede atrasar las sugerencias.
* CON-3 (suposición): los datos de entrenamiento no salen de la región. CON-5 (suposición): sin cómputo ocioso.

## Considered Options

* A. Ranking por características aprendido del feedback, con personalización por usuario y exploración
* B. Filtrado colaborativo ("usuarios parecidos eligieron esto")
* C. Híbrido: ranking por características más una señal colaborativa
* D. Reglas fijas (más barato, misma aerolínea, horario más cercano), sin aprendizaje

## Decision Outcome

Chosen option: "A. Ranking por características aprendido del feedback", because describe cada oferta por lo que el
viajero valora (precio, duración, escalas, horario, proveedor) y no por su identidad, así que funciona con ofertas
nuevas y con viajeros sin historial; aprende de cada aceptación o rechazo, y sus versiones se pueden comparar y
volver atrás sin tocar otros procesos.

Reglas:

* **Dos etapas:** primero se filtran las ofertas que violan un límite explícito del viajero (precio máximo, máximo
  de escalas, franja horaria, proveedores excluidos); después se ordenan las restantes. Ningún orden puede saltear
  un límite explícito (QA-13).
* **Características de cada oferta**, relativas a la reserva cancelada y al perfil: precio relativo a la banda del
  perfil, duración, escalas, diferencia de horario con la reserva original, demora de llegada, si es el mismo
  proveedor, afinidad del perfil con ese proveedor o cadena, y coincidencia de noches para alojamiento. No incluyen
  datos personales: el vector describe la oferta para ese viajero.
* **Puntaje:** probabilidad estimada de aceptación con un modelo lineal logístico: pesos del modelo regional más un
  ajuste por viajero que se guarda en su perfil. Un viajero sin historial usa solo los pesos regionales.
* **Se muestran 3 sugerencias** (suposición). Con probabilidad 0,1 (suposición), una de las tres sale de fuera de las
  tres mejores, para no aprender solo de lo que ya se mostraba (exploración *epsilon-greedy*). Se registra la
  posición de cada sugerencia mostrada para corregir el sesgo de posición al entrenar.
* **Feedback inmediato (human-in-the-loop):** aceptar o rechazar ajusta en el momento el ajuste por viajero con un
  paso de descenso por gradiente; ajustar un parámetro cambia el filtro. En ambos casos las sugerencias pendientes
  de ese viaje se reordenan y se devuelven en la misma respuesta (QA-13, 2 s).
* **Entrenamiento por lotes, diario y por región:** un trabajo programado en la región entrena los pesos regionales
  con el feedback de la región (aceptadas como positivas, rechazadas como negativas, ponderadas por posición). Usa
  cómputo solo mientras corre (CON-5) y los datos no salen de la región (CON-3). El feedback de un día entra en el
  modelo de esa noche (QA-13, 24 h).
* **Registro de versiones del modelo:** cada versión entrenada guarda sus pesos, la fecha, los datos usados y su
  evaluación con el feedback reservado para prueba. Solo se activa si no empeora la tasa de aceptación estimada de la
  versión actual. Una versión nueva arranca como *canario* para el 5 % de los viajeros, asignados por un hash estable
  del `userId`; si su tasa de aceptación cae más de un 10 % relativo con una muestra mínima, se vuelve atrás
  automáticamente. Volver atrás es cambiar qué versión está activa: no hay que desplegar código (QA-15).
* **Modelos regionales independientes:** cada región aprende de sus viajeros; no se combinan datos entre regiones.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón de recomendación en dos etapas (candidatos y ranking) | Filtro por límites explícitos y luego orden por puntaje | QA-13 |
| Táctica *mantener un modelo del usuario* (usabilidad) | Ajuste por viajero y preferencias explícitas en el perfil | QA-13, RF-09.3 |
| Táctica *apoyar la iniciativa del usuario* (usabilidad) | Ajustar parámetros cambia el filtro y reordena en el momento | QA-13 |
| Exploración *epsilon-greedy* (bandit) | Una de cada diez listas incluye una oferta fuera de las mejores | RF-09.3 |
| Táctica *diferir el enlace* (modificabilidad) | La versión activa del modelo se elige en tiempo de ejecución desde el registro | QA-15 |
| Tácticas *escalonar los despliegues* y *volver atrás* (desplegabilidad), patrón *Canary Release* | Versión nueva para el 5 %; vuelta atrás automática si empeora | QA-15 |
| Táctica *programar recursos* (performance) | Entrenamiento por lotes en un trabajo programado | CON-5 |

### Consequences

* Good, because funciona desde el primer viajero y con ofertas que nunca se vieron.
* Good, because las versiones del modelo se prueban con una parte de los viajeros y se descartan sin desplegar código.
* Good, because un modelo lineal es barato de servir y fácil de explicar ("más barato y sin escalas").
* Bad, because un modelo lineal no captura combinaciones complejas de preferencias; cambiar a otro tipo de modelo es
  posible detrás del mismo registro de versiones, pero exige reentrenar (QA-15 lo cubre).
* Bad, because no aprovecha lo que eligen viajeros parecidos: queda como evolución (opción C) si el feedback acumulado
  lo justifica.
* Bad, because la tasa de aceptación depende también de qué ofertas hay en cada disrupción: comparar versiones exige
  una muestra mínima, y un canario puede tardar en decidir.

### Confirmation

Pruebas del prototipo con datos sintéticos: viajeros con preferencias ocultas generan feedback simulado y el modelo
entrenado supera al orden fijo por precio en tasa de aceptación; ninguna sugerencia viola un límite explícito; un
rechazo reordena en la misma respuesta; una versión que empeora vuelve atrás sola.

## Pros and Cons of the Options

### A. Ranking por características aprendido

* Good, because no depende de la identidad de la oferta ni de tener muchos viajeros parecidos.
* Bad, because hay que elegir y mantener las características.

### B. Filtrado colaborativo

* Good, because descubre preferencias que no están en las características.
* Bad, because sufre con viajeros nuevos y ofertas nuevas, que en una cancelación son casi todas.

### C. Híbrido

* Good, because suma lo mejor de A y B.
* Bad, because es el doble de modelo para entrenar, versionar y explicar sin evidencia todavía de que haga falta.

### D. Reglas fijas

* Good, because es simple y predecible.
* Bad, because no aprende del feedback: no cumple el human-in-the-loop del enunciado.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 5, [iteration-5-recommendation](../01-add/iteration-5-recommendation.md) |
| Drivers | RF-09.3, QA-11, QA-13, QA-15, CON-3, CON-5 |
| Contratos | [recommendation.md](../../specs/recommendation.md) |
| Código del prototipo | `prototype/recomendacion/modelo/` |
