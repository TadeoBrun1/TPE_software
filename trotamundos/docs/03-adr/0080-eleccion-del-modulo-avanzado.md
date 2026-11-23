---
status: "accepted"
date: 2026-11-22
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Módulo avanzado de la segunda entrega: sistema de recomendación (opción A)

## Context and Problem Statement

El enunciado obliga a incorporar al menos uno de dos módulos avanzados para la segunda entrega: la opción A, un
sistema de recomendación que sugiera proactivamente alternativas de alojamiento, transporte o rutas con
optimización *human-in-the-loop*, o la opción B, un asistente virtual de primer nivel que gestione reprogramaciones,
consultas de estado y problemas menores, y derive a la agencia los casos complejos. ¿Cuál se incorpora, considerando
lo que cada una exige de la arquitectura ya diseñada (iteraciones 1 a 4) y lo que cuesta mantenerla en el futuro?

Elegir el módulo es una decisión de alcance: las dos opciones son válidas para el sistema. Esta ADR registra la
elección y la comparación; las decisiones de diseño del módulo están en ADR-0081 a ADR-0084.

## Decision Drivers

* Requerimientos avanzados del enunciado (selección obligatoria para la segunda entrega).
* Compatibilidad con las ADRs existentes, en especial ADR-0002, ADR-0004, ADR-0026, ADR-0044, ADR-0064 y ADR-0065.
* Esfuerzo de incorporación y de evolución futura (pruebas, escala en picos, seguridad, costo de operación).
* CON-3 (suposición): datos personales en la región del usuario. CON-5 (suposición): sin capacidad ociosa.

## Considered Options

* A. Sistema de recomendación con optimización human-in-the-loop
* B. Asistente virtual (chatbot) de primer nivel con un modelo de lenguaje local
* A y B

## Decision Outcome

Chosen option: "A. Sistema de recomendación", because se suma a la arquitectura como un consumidor nuevo de eventos
sin tocar el núcleo (ADR-0002), no compromete la latencia del panel (QA-2) y, una vez incorporado, escala y opera
con costo bajo: las sugerencias se calculan ante eventos y el modelo se entrena por lotes. El equipo la consideró
además la opción más útil para el viajero; ese juicio de valor es una suposición aceptada por el equipo, y no se usa como criterio de
arquitectura. Los costos que trae (un almacén de perfiles, una fuente externa de ofertas
y reglas nuevas) se resuelven con decisiones propias en esta misma iteración.

Alcance acordado por el equipo (RF-09): sugiere **alojamiento y transporte** (las rutas de varios tramos quedan
fuera), se dispara **ante una cancelación o disrupción** (las opciones de disparador están en ADR-0081), y aceptar una sugerencia la deja como **reserva propuesta**
con el enlace a la oferta del proveedor, sin comprar ni emitir reservas (fuera del alcance del sistema).

Se registra también un factor de alcance que no se usa para justificar decisiones de diseño: el equipo tiene más
experiencia en prompting y en integración con modelos de lenguaje, lo que bajaba el riesgo de implementar la opción B
en el prototipo.

### Consequences

* Good, because el módulo se agrega como un proceso más por región, con su cola y su almacén, y el núcleo solo suma
  la reserva propuesta.
* Good, because la recomendación por lotes y ante eventos escala con los picos sin cómputo continuo.
* Bad, because necesita un almacén nuevo de perfiles por usuario y región (ADR-0064 impide usar la analítica) y
  una fuente externa de ofertas que el sistema no tenía.
* Bad, because obliga a definir reglas nuevas: qué es aceptar sin comprar, retención del perfil, push proactivo y
  entrenamiento por región.
* Neutral, because la derivación a la agencia (RF-06, ADR-0026) sigue diseñada pero sin implementar en el prototipo.

### Confirmation

La [iteración 5](../01-add/iteration-5-recommendation.md) diseña el módulo con ADR-0081 a ADR-0084 y el prototipo lo
implementa con pruebas de RF-09 y de los escenarios QA-11 a QA-17.

## Pros and Cons of the Options

Niveles estimados por el equipo (**suposición**): 🟢 bajo, 🟡 medio, 🔴 alto.

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. Recomendación** | • Se suma como consumidor nuevo de eventos, sin tocar el núcleo (ADR-0002)<br>• No afecta la latencia del panel (QA-2); entra como prioridad baja (ADR-0047)<br>• Ya estaba prevista en ADR-0064 y en el registro de impactos | • Necesita un almacén nuevo de perfiles por usuario y región (ADR-0064, CON-3)<br>• Necesita un catálogo externo de ofertas, que no existía (CON-1, CON-2)<br>• Hay que definir qué es "aceptar" sin entrar en la compra, que está fuera de alcance<br>• Reglas nuevas: retención del perfil (ADR-0045), push proactivo (ADR-0046), un modelo por región |
| **B. Asistente virtual** | • Reusa la derivación a la agencia (RF-06, ADR-0026)<br>• Las reprogramaciones vuelven por el flujo de novedades y respetan el dueño por campo (ADR-0044)<br>• El modelo local mantiene los datos en la región (CON-3)<br>• Completa RF-06 en el prototipo | • El backend genera texto: necesita una excepción a ADR-0004 y ADR-0065, como la de ADR-0063<br>• Riesgo de prompt injection con datos que vienen de correos (QA-7)<br>• Las conversaciones son datos personales: retención y logs (ADR-0067)<br>• Capacidad de cómputo del modelo por región y escalado lento (ADR-0043, CON-5)<br>• Reprogramar directo con el proveedor sería una integración de escritura nueva (ADR-0023) |

| Aspecto | A. Recomendación | B. Asistente virtual |
|---|---|---|
| Incorporarlo al diseño | 🔴 Alto: almacén nuevo, catálogo externo, ciclo de entrenamiento y reglas nuevas | 🟡 Medio: reusa ADR-0026; suma excepciones y seguridad |
| Implementarlo en el prototipo (factor de alcance, no criterio de arquitectura) | 🔴 Alto: datos sintéticos, modelo, catálogo simulado y ciclo de feedback | 🟡 Medio: módulo de asistencia (ya diseñado) y un bot con modelo local |
| Impacto en lo ya hecho | 🟢 Bajo: proceso aparte y endpoints nuevos | 🟡 Medio: excepciones a ADR-0004 y ADR-0065, herramientas sobre la API del núcleo |
| Cambiar el modelo en el futuro | 🟡 Medio: hay que reentrenar y puede cambiar el formato del perfil | 🟢 Bajo: el modelo se reemplaza detrás de un puerto |
| Agregar capacidades nuevas | 🟡 Medio: un tipo de sugerencia nuevo suele pedir otra fuente de datos | 🟢 Bajo: se agrega una herramienta al bot |
| Probar los cambios | 🟡 Medio: métricas sobre datos históricos | 🔴 Alto: respuestas no deterministas y regresiones de prompts |
| Escalar con los picos | 🟢 Bajo: se calcula ante eventos y se sirve como datos | 🔴 Alto: cada mensaje consume cómputo, y los picos (disrupciones) son cuando más se usa el chat |
| Seguridad y privacidad | 🟡 Medio: perfilado del usuario y consentimiento | 🔴 Alto: prompt injection, conversaciones con datos personales, acciones en nombre del usuario |
| Dependencia de sistemas externos | 🔴 Alto: catálogo de ofertas nuevo | 🟢 Bajo: la agencia ya estaba contemplada (🟡 si reprograma directo con el proveedor) |
| Costo de operación | 🟢 Bajo: entrenamiento por lotes | 🔴 Alto: cómputo continuo para responder |

### A y B

* Good, because cubre los dos módulos.
* Bad, because duplica el trabajo de diseño y de prototipo sin que el enunciado lo pida ("al menos uno").

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 5, [iteration-5-recommendation](../01-add/iteration-5-recommendation.md) |
| Drivers | Requerimientos avanzados del enunciado, RF-09 |
| Requerimientos | [functional-rqmts.md](../00-requirements/functional-rqmts.md) |
| Decisiones del módulo | ADR-0081, ADR-0082, ADR-0083, ADR-0084 |
