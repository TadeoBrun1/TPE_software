# Plan de iteraciones

**Qué es:** qué iteraciones haremos, con qué objetivo y en qué orden.
**Mantiene:** ambos. **Estado:** PROPUESTA para discutir.

El enunciado pide 4 iteraciones como mínimo. Las dos primeras reglas de ordenamiento son: la 1ra estructura el
sistema, y las siguientes atacan los drivers de mayor prioridad, empezando por lo que sostiene el negocio.

## Plan

| # | Objetivo | Drivers | Responsable |
|---|---|---|---|
| 1 | Arquitectura de referencia, estructura general y despliegue de alto nivel | CRN-1, RF-01, RF-03, RF-05, QA-1, QA-4, QA-5, QA-9, QA-10 (parte multirregión), a nivel de estructura; aplican CON-1, CON-2, CON-3 | Ambos |
| 2 | Ingesta de reservas desde correo y terceros: frescura, interoperabilidad y acceso seguro a correos | RF-01, RF-02, RF-03, QA-1, QA-6, QA-8, CRN-3, CRN-4 | `<A>` |
| 3 | Consulta de itinerarios: latencia, disponibilidad y escala ante picos | RF-04, RF-05, QA-2, QA-3, QA-4, QA-5 | `<B>` |
| 4 | Seguridad de compartición, internacionalización, analítica sin afectar a los usuarios y evolucionabilidad | RF-07, RF-08, QA-7, QA-9, QA-10, CRN-2 | Ambos |
| 5 (opcional) | Opción avanzada (A o B) y refinamientos si sobra tiempo | A definir | A definir |

Cada fila enlaza a su documento:
[1](iteration-1-structure.md) ·
[2](iteration-2-ingestion.md) ·
[3](iteration-3-query-scale.md) ·
[4](iteration-4-security-evolvability.md)

## Dependencias entre iteraciones (zonas de riesgo)

| Entre | Dependencia | Cómo se maneja |
|---|---|---|
| 2 y 3 | La ingesta escribe lo que la consulta lee: el modelo de datos de reservas es compartido | Se define en la iteración 1 y se cambia solo con aviso (ver [impact-log.md](impact-log.md)) |
| 2 y 3 | Ambas usan el bus o cola de eventos | Contrato en `specs/asyncapi/` revisado por ambos |
| 3 y 4 | La analítica pesada puede degradar la consulta | La iteración 1 la separa como proceso (ADR-0001); el almacén se decide en la 4 (ADR-0060) |

## Cambios al plan

Anotar acá cualquier cambio con fecha y razón.

| Fecha | Cambio | Razón |
|---|---|---|
| 2026-10-27 | Se agrega la parte multirregión de QA-10 a la iteración 1 | Es la justificación real del despliegue por regiones (ADR-0004) |
| 2026-10-27 | ADR-0003 (almacén analítico) pasa a la iteración 4 como ADR-0060 | Su driver principal, RF-07, pertenece a la iteración 4 |
| 2026-10-27 | Se quita el cronograma | El plazo del TPE no es criterio de diseño; el avance se sigue en el TEAM-LOG |
