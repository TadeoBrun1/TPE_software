# Uso de IA en el trabajo

Este archivo explica cómo se usó la IA para producir la arquitectura de Trotamundos: con qué contexto, con qué
prompts y, sobre todo, qué controles humanos se aplicaron. El flujo parte del paper "Better Together" adjunto al TPE,
adaptado a los nombres de archivo de este repo. Los aportes de cada integrante se registran en el
[TEAM-LOG](../TEAM-LOG.md).

## Cómo se trabajó

La IA se usó como asistente del proceso ADD, no como quien decide. Cada iteración siguió los mismos pasos:

1. **Contexto fijo.** La IA recibió la [persona de arquitecto](architect-persona.md), el proceso ADD y los drivers
   del repositorio (ver la tabla de abajo). Así, sus propuestas respetan las restricciones técnicas y no usan el
   plazo del TPE ni el tamaño del grupo como criterio de diseño.
2. **Alternativas en lugar de respuestas.** Para cada problema de la iteración, la IA planteó qué había que resolver
   y entre dos y cuatro alternativas, con sus ventajas, desventajas y los drivers que afectan. No se usaron matrices
   de decisión.
3. **Decisión humana.** El integrante responsable de la iteración eligió la alternativa que mejor se adecuaba a los
   drivers, o pidió más explicación antes de elegir. Las decisiones críticas siempre las tomó una persona, porque el
   paper mostró que los modelos cambian de opinión entre corridas.
4. **Redacción.** Con las decisiones tomadas, la IA redactó los pasos 2 a 7 de ADD, las ADRs en formato MADR, los
   contratos en `specs/` y las vistas. Las cifras que la IA no podía justificar con el enunciado quedaron marcadas
   como suposiciones, indicando de qué dato parten.
5. **Auditoría independiente.** Un segundo agente de IA, en un contexto aparte y sin la conversación en la que se
   tomaron las decisiones, auditó la iteración como lo haría un profesor: coherencia entre ADRs, vistas y
   contratos; drivers mal cubiertos; tácticas mal nombradas; suposiciones sin marcar. Se le indicó que las
   decisiones elegidas tienen trade-offs y que no debía juzgar cuál era "la mejor", sino si estaban bien aplicadas.
6. **Decisiones sobre los hallazgos.** Los hallazgos que cambiaban el comportamiento del sistema volvieron al
   integrante para que eligiera cómo resolverlos. Los errores de coherencia se corrigieron directamente.
7. **Revisión cruzada.** El otro integrante revisó la iteración en el pull request. Sus observaciones se evaluaron,
   se aplicaron las que correspondían y se registraron a su nombre en el TEAM-LOG.
8. **Verificación.** Antes de cada commit se validaron los contratos (sintaxis, referencias y esquemas), los links
   y el render de los diagramas Mermaid. Validar los contratos no demuestra el comportamiento del sistema: nada se
   marca como probado ni aprobado sin evidencia real.

## Uso por etapa

En todas las etapas se usaron asistentes de IA de uso general. Para los requisitos se usaron además *skills*:
instrucciones reutilizables que le indican al asistente cómo hacer una tarea concreta siguiendo la bibliografía de
la materia.

| Etapa | Responsable | Uso de la IA | Controles humanos |
|---|---|---|---|
| Requisitos (`docs/00-requirements/`) | Tadeo Brun | Generación y revisión de los escenarios de calidad con el template SEI de 6 partes (`/generador-qas`, `/test-qas`), árbol de utilidad (`/arbol-utilidad`) y revisión de restricciones, conceptos y requerimientos funcionales con los marcos de Bass, Clements y Kazman (`/bass-software-architecture`) y de Keeling (`/keeling-design-it`) | Cada cambio de estado y de contenido lo confirmó el integrante |
| Iteración 1 — Estructura general | Ambos; revisión de Tadeo Brun | Primera versión de los pasos de ADD y de las ADRs 0001 a 0004 con la persona de arquitecto; después, auditoría en rol de profesor que llevó a marcar arquitectura de referencia, patrones y tácticas, a quitar la matriz de decisión y a eliminar una ADR | Las decisiones de la revisión las tomó Tadeo Brun |
| Iteración 2 — Ingesta | Tomas Lateana | Redacción por pasos de la iteración, las ADRs 0020 a 0028, las vistas de ingesta y los contratos; consulta de documentación oficial (Gmail, Microsoft Graph, RabbitMQ, SEI) | Revisión cruzada de Tadeo Brun, también asistida por IA; correcciones aplicadas por Tomas Lateana |
| Iteración 3 — Consulta y escala | Tadeo Brun | Alternativas para cada decisión, redacción de pasos, ADRs 0040 a 0048, API de itinerarios y vistas; auditoría independiente en un contexto aparte | Decisiones elegidas por Tadeo Brun y confirmadas con Tomas Lateana; revisión cruzada de Tomas Lateana |
| Iteración 4 — Seguridad y evolución | Tadeo Brun y Tomas Lateana | Alternativas para cada decisión, redacción de pasos, ADRs 0060 a 0067, contratos y vistas; auditoría independiente en un contexto aparte | Decisiones y respuestas a los hallazgos de la auditoría tomadas por ambos integrantes |

## Archivos que se le dan a la IA como contexto

| Archivo | Rol |
|---|---|
| `ai/architect-persona.md` | Persona fija |
| `docs/01-add/ADD.md` | Descripción del proceso |
| `docs/00-requirements/architectural-drivers.md` y los archivos que enlaza | Entradas priorizadas |
| `docs/architecture.md` | Documento central que se va modificando |
| `docs/01-add/iteration-plan.md` | Plan acordado |
| `docs/01-add/impact-log.md` | Acuerdos entre iteraciones |

## Prompts

Los prompts 1 a 5 son los del paper, adaptados al repo. Los prompts 6 y 7 resumen el modo de trabajo que se usó en
las iteraciones.

**1. Revisar entradas**

```
Revisá docs/00-requirements/architectural-drivers.md y los documentos que enlaza.
Verificá que los requerimientos sean consistentes y que entiendas las prioridades.
Hacé preguntas de aclaración si hace falta.
```

**2. Modelo de dominio**

```
Considerá los drivers y creá un modelo de dominio en docs/02-views/domain-model.md.
Representalo con un diagrama de clases en Mermaid e incluí una tabla que describa cada elemento.
```

**3. Plan de iteraciones**

```
Considerá las prioridades de los requerimientos y el modelo de dominio. Creá un plan de iteraciones
siguiendo docs/01-add/ADD.md. Para cada iteración, indicá el objetivo principal. La primera debe estructurar
el sistema; las siguientes atacan los drivers de mayor prioridad, y los requerimientos que sostienen el
negocio van en las primeras. Presentalo como tabla con número, objetivo y drivers, en docs/01-add/iteration-plan.md.
```

**4. Ejecutar una iteración**

```
Vamos a ejecutar los pasos de ADD descritos en docs/01-add/ADD.md. Seguilos exactamente como están
descritos. Ejecutá un solo paso por vez y esperá mi devolución antes de continuar. Respondé en Markdown.
Esta es la iteración: N. Usá la plantilla docs/01-add/iteration-template.md.
```

**5. ADR de una decisión**

```
Redactá una ADR en formato MADR, usando docs/03-adr/adr-template.md, para la decisión <X> de la iteración N.
Incluí al menos dos alternativas descartadas con sus pros y contras y la trazabilidad a los drivers.
```

**6. Decidir por alternativas**

```
Para la iteración N, decime qué hay que evaluar y resolver. Para cada punto, dame entre dos y cuatro
alternativas que se ajusten al problema, con sus ventajas, desventajas y los drivers que afectan. Yo elijo la
opción; no tomes decisiones por tu cuenta. Marcá como suposición todo dato que no salga del enunciado o de los QA.
```

**7. Auditoría independiente**

```
Sos un auditor de arquitectura (rol: profesor que corrige un trabajo práctico). Solo lectura: no modifiques
archivos. Revisá la iteración N en la rama <rama> contra el enunciado, los requisitos y las iteraciones
anteriores. Las decisiones ya están tomadas y tienen trade-offs: no juzgues si son las mejores, sino si están
bien aplicadas. Buscá contradicciones entre ADRs, vistas y contratos; drivers mal cubiertos; tácticas mal
nombradas según Bass (4ta ed.); suposiciones sin marcar; documentos desactualizados. Ordená los hallazgos por
gravedad e indicá si cada uno es un error o una decisión discutible.
```

## Reglas de uso

1. **Las decisiones de arquitectura las toma una persona.** La IA propone alternativas y redacta; el integrante
   responsable elige.
2. **Todo lo que produce la IA lo revisa una persona** antes del pull request, y el otro integrante lo revisa en el
   pull request.
3. **Cada iteración pasa por una auditoría independiente**, en un contexto aparte, antes de la revisión cruzada.
4. **Los números que la IA no puede justificar son suposiciones** hasta validarlos, y se marcan como tales con su
   origen.
5. **No se atribuyen a los integrantes pruebas, mediciones ni aprobaciones que no ocurrieron.** El estado de cada
   documento dice qué está diseñado, qué está revisado y qué falta validar.
6. **Los aportes se registran a nombre de quien los hizo** en el TEAM-LOG, incluidas las revisiones cruzadas.

## 2026-10-28 — Preparación de script para correcciones de iteración 4

Tomas solicitó un script para aplicar las observaciones de revisión sobre iteracion4, commit a141983. La asistencia
preparó perfil JWT, proyección compartida sin details, auditoría de todas las rutas, enrutamiento por método,
recepción analítica idempotente, período de claves, medición temporal y cobertura de telemetría, y precisiones de
persistencia, tránsito y seudonimización. Se prueban formato y aplicación sobre una copia. La revisión humana de
estas propuestas y la implementación del prototipo siguen pendientes; no se atribuye aceptación nueva al equipo.
