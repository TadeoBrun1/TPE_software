# Plan de iteraciones

**Qué es:** qué iteraciones haremos, con qué objetivo y en qué orden.
**Mantiene:** ambos. **Estado:** PROPUESTA para discutir.

El enunciado pide 4 iteraciones como mínimo. Las dos primeras reglas de ordenamiento son: la 1ra estructura el
sistema, y las siguientes atacan los drivers de mayor prioridad, empezando por lo que sostiene el negocio.

## Plan

| # | Objetivo | Drivers | Responsable |
|---|---|---|---|
| 1 | Arquitectura de referencia, estructura general y despliegue de alto nivel | CRN-1, RF-01, RF-03, RF-05, QA-1, QA-4, QA-5, QA-9, QA-10 (parte multirregión), a nivel de estructura; aplican CON-1, CON-2, CON-3, CON-4 | Ambos |
| 2 | Ingesta de reservas desde correo y terceros: frescura, interoperabilidad y acceso seguro a correos | RF-01, RF-02, RF-03, RF-06, QA-1, QA-6, QA-8, CRN-3, CRN-4 | Tomas Lateana |
| 3 | Consulta de itinerarios: latencia, disponibilidad y escala ante picos; aplicación de novedades en el núcleo | RF-04, RF-05, QA-2, QA-3, QA-4, QA-5; etapas de núcleo y cliente de QA-1; QA-6 del lado consumidor | Tadeo Brun |
| 4 | Seguridad de compartición, internacionalización, analítica sin afectar a los usuarios y evolucionabilidad | RF-07, RF-08, QA-7, QA-9, QA-10, CRN-2, interoperabilidad con redes sociales | Ambos |
| 5 (opcional) | Opción avanzada (A o B) y refinamientos si sobra tiempo; candidato: mitigar el riesgo de QA-1 a escala | A definir | A definir |

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
| 3 y 4 | La analítica pesada puede degradar la consulta | La iteración 1 la separa como proceso (ADR-0001); la 4 le da un almacén propio por región alimentado por eventos (ADR-0064) |

## Cambios al plan

Anotar acá cualquier cambio con fecha y razón.

| Fecha | Cambio | Razón |
|---|---|---|
| 2026-10-27 | Se agrega la parte multirregión de QA-10 a la iteración 1 | Es la justificación real del despliegue por regiones (ADR-0003) |
| 2026-10-27 | Se elimina la ADR del almacén analítico (era la 0003) y se renumeran las siguientes: despliegue pasa a 0003 y arquitectura de referencia a 0004 | El driver del almacén, RF-07, pertenece a la iteración 4 |
| 2026-10-27 | RF-06 (agencia de viajes) se asigna a la iteración 2 | No estaba asignado a ninguna iteración |
| 2026-10-27 | Se agrega CON-4 (capacidades nativas en móvil) a las restricciones de la iteración 1 | Es un requisito del enunciado que no estaba capturado en ningún driver |
| 2026-10-27 | Se quita el cronograma | El plazo del TPE no es criterio de diseño; el avance se sigue en el TEAM-LOG |
| 2026-10-28 | La iteración 3 incluye la aplicación de novedades en el núcleo | El consumidor de novedades y RF-04 viven en el núcleo, que refina esta iteración |
| 2026-10-28 | QA-1 a escala (avisos perdidos) se registra como riesgo aceptado; candidato para la iteración 5 | Decisión de alcance de la iteración 3 |
| 2026-10-28 | Se agrega CON-5 (startup con recursos limitados) como suposición | La auditoría de la iteración 3 marcó que el argumento de costo de ADR-0043 no estaba en los requerimientos |
| 2026-10-28 | Se corrigen los nombres de tácticas de disponibilidad en las iteraciones 1 y 3 según Bass, 4ta edición (*redundant spare*, *ping/echo*) | Auditoría de la iteración 3 |
| 2026-10-28 | La iteración 4 agrega la interoperabilidad con redes sociales a sus drivers | El enunciado la pide junto con la compartición y no estaba asignada |
| 2026-10-28 | El recorrido de QA-9 usa un medio que no existe (ferry) en lugar de trenes | `train` ya está en el vocabulario de tipos desde la iteración 2 |
