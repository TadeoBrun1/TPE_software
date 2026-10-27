# Proceso ADD (Attribute-Driven Design)

**Qué es:** descripción del método que seguimos, en versión corta. Es la referencia de proceso del repo y también el
archivo que se le entrega a la IA cuando se usa (ver [ai/prompts.md](../../ai/prompts.md)).
**Base:** ADD 3.0 (Bass, Clements y Kazman, cap. 20) y el enfoque del paper adjunto al TPE.

## Preparación (una sola vez)

1. **Revisar entradas (paso 1 de ADD):** propósito del diseño, funcionalidad primaria, QAs, restricciones y concerns,
   todo priorizado. Ver [../00-requirements/](../00-requirements/).
2. **Modelo de dominio:** ver [../02-views/domain-model.md](../02-views/domain-model.md).
3. **Plan de iteraciones:** ver [iteration-plan.md](iteration-plan.md).

## Cada iteración repite los pasos 2 a 7

### Paso 2 — Establecer el objetivo de la iteración

Se eligen los drivers que se atacan en esta iteración (de la lista priorizada). Una iteración ataca un conjunto
acotado y coherente.

### Paso 3 — Elegir los elementos del sistema a refinar

En la 1ra iteración el elemento es el sistema completo. Después se refinan elementos que ya existen (contenedores o
componentes).

### Paso 4 — Elegir conceptos de diseño que satisfacen los drivers

Un concepto de diseño puede ser un patrón (arquitectura de referencia, patrón arquitectónico, de diseño o de
despliegue), una táctica o un componente externo (framework o recurso de nube). Se registra en una tabla:

| Concepto elegido | Justificación | Alternativas descartadas |
|---|---|---|

Las decisiones importantes se convierten en **ADR**.

### Paso 5 — Instanciar elementos, asignar responsabilidades y definir interfaces

Se adaptan los conceptos elegidos al sistema: se crean o cambian elementos, se asignan responsabilidades y se
definen los contratos entre elementos. Se actualizan los diagramas. Se registra en una tabla:

| Decisión de instanciación | Justificación |
|---|---|

Los contratos nuevos o modificados se escriben primero en [../../specs/](../../specs/) (spec-driven).

### Paso 6 — Esbozar vistas y registrar decisiones

Se actualizan las vistas de [../02-views/](../02-views/) y se completan las ADRs de [../03-adr/](../03-adr/).
Este paso se hace mientras se instancia: instanciar casi siempre implica dibujar.

### Paso 7 — Analizar el diseño actual y decidir si se sigue iterando

Se verifica, driver por driver, si el objetivo de la iteración se cumplió: estado (cumplido, parcial, no cumplido),
riesgos y qué queda pendiente. Técnicas sugeridas: Scenario Walkthrough y Risk Storming (Keeling, actividades 37 y 35).
Se revisa también el [registro de impactos](impact-log.md).

## Principios que usamos

- Una iteración deja un diseño parcialmente refinado; nunca se intenta diseñar todo de una vez.
- Cada decisión tiene rationale y alternativas descartadas ("paths not taken").
- Los drivers no se modifican durante ADD; si hay que cambiarlos, se justifica por PR de ambos.
- El plazo del TPE y el tamaño del grupo no son criterio de decisión de la arquitectura: solo acotan el alcance del
  prototipo.
- En el paso 4 se eligen arquitecturas de referencia, patrones y tácticas con su nombre (Bass); las tecnologías
  concretas se deciden después.
- Cuando se usa IA, las decisiones críticas (estilo arquitectónico, base de datos, cómo se distribuye el sistema) las
  confirma una persona: los modelos pueden cambiar de opinión entre corridas.
