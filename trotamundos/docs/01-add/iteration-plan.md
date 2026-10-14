# Plan de iteraciones

**Qué es:** qué iteraciones haremos, con qué objetivo y en qué orden.
**Mantiene:** ambos. **Estado:** PROPUESTA para discutir.

El enunciado pide 4 iteraciones como mínimo. Las dos primeras reglas de ordenamiento son: la 1ra estructura el
sistema, y las siguientes atacan los drivers de mayor prioridad, empezando por lo que sostiene el negocio.

## Plan

| # | Objetivo | Drivers | Responsable |
|---|---|---|---|
| 1 | Estructura general del sistema, estilo arquitectónico y deployment de alto nivel | CRN-1, QA-5, QA-9 (a nivel de estructura), CON-7 | Ambos |
| 2 | Ingesta de reservas desde correo y terceros: frescura, interoperabilidad y acceso seguro a correos | RF-01, RF-02, RF-03, QA-1, QA-6, QA-8, CRN-3 | `<A>` |
| 3 | Consulta de itinerarios: latencia, disponibilidad y escala ante picos | RF-04, RF-05, QA-2, QA-3, QA-4, QA-5, CRN-4 | `<B>` |
| 4 | Seguridad de compartición, internacionalización, analítica sin afectar a los usuarios y evolucionabilidad | RF-07, RF-08, QA-7, QA-9, QA-10, CRN-2 | Ambos |
| 5 (opcional) | Opción avanzada (A o B) y refinamientos si sobra tiempo | A definir | A definir |

Cada fila enlaza a su documento:
[1](iteration-1-structure.md) ·
[2](iteration-2-ingestion.md) ·
[3](iteration-3-query-scale.md) ·
[4](iteration-4-security-evolvability.md)

## Cronograma sugerido (10 días)

| Días | Qué | Cómo |
|---|---|---|
| 1 y 2 | Contexto, RF, QAs, árbol de utilidad, modelo de dominio, iteración 1 | Juntos |
| 3 a 6 | Iteraciones 2 y 3, y esqueleto del prototipo | En paralelo, cada uno con su iteración |
| 7 y 8 | Iteración 4 y completar el prototipo | Juntos |
| 9 | Integración, revisión cruzada, `architecture.md`, vistas finales | Juntos |
| 10 | Chequeo de trazabilidad y entrega | Juntos |

Si sobra tiempo, se hace la iteración 5.

## Dependencias entre iteraciones (zonas de riesgo)

| Entre | Dependencia | Cómo se maneja |
|---|---|---|
| 2 y 3 | La ingesta escribe lo que la consulta lee: el modelo de datos de reservas es compartido | Se define en la iteración 1 y se cambia solo con aviso (ver [impact-log.md](impact-log.md)) |
| 2 y 3 | Ambas usan el bus o cola de eventos | Contrato en `specs/asyncapi/` revisado por ambos |
| 3 y 4 | La analítica pesada puede degradar la consulta | Separar la carga analítica (decidirlo en la iteración 1 o 3, validarlo en la 4) |

## Cambios al plan

Anotar acá cualquier cambio con fecha y razón.

| Fecha | Cambio | Razón |
|---|---|---|
|  |  |  |
