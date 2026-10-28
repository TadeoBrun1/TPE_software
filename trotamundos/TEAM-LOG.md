# Registro de trabajo del equipo

Una fila por aporte relevante. Sirve para que la evolución del trabajo y la labor de cada integrante sean visibles
(criterio del enunciado). Complementa el historial de commits y PRs, no lo reemplaza.

| Fecha | Integrante | Qué hizo | Enlace (PR / archivo) |
|---|---|---|---|
| 2026-10-14 | `Tadeo Brun` + `Tomas Lateana` | Esqueleto del repo y plantillas | `README.md` |
| 2026-10-15 | `Tadeo Brun` | Revision y correccion de QAs con skill /test-Qa | `quality-attribute-scenarios.md` |
| 2026-10-27 | `Tadeo Brun` | Revision y correccion de restricciones y concerns | `constraints-concerns.md` |
| 2026-10-27 | `Tadeo Brun` | Correccion de los links de la portada y el menu lateral de la wiki para que apunten al repo | `wiki/Home.md`, `wiki/_Sidebar.md` |
| 2026-10-27 | `Tadeo Brun` | Revision y correccion de requerimientos funcionales | `functional-rqmts.md` |
| 2026-10-27 | `Tadeo Brun` + `Tomas Lateana` | Iteracion 1 de ADD y ADRs 0001 a 0004 | `iteration-1-structure.md`, `docs/03-adr/` |
| 2026-10-27 | `Tadeo Brun` | Revisión de la iteración 1: arquitectura de referencia, patrones y tácticas, se elimina la ADR del almacén analítico y se renumeran las ADRs (0001 a 0004), vistas C&C, despliegue y módulos | `iteration-1-structure.md`, `docs/03-adr/`, `docs/02-views/` |
| 2026-10-27 | `Tomas Lateana` | Iteración 2 (ingesta): pasos 2 a 7, ADRs 0020 a 0028, vista y secuencias de ingesta, contratos en `specs/` y plan de validación del prototipo. Preparado con asistencia de ChatGPT/Codex (ver `ai/prompts.md`) | `iteration-2-ingestion.md`, `docs/03-adr/0020` a `0028`, `specs/` |
| 2026-10-28 | `Tadeo Brun` | Revisión de coherencia de los requerimientos: estados actualizados a COMPLETADO, QA-10 alineado con la región de origen, tabla de restricciones corregida | `docs/00-requirements/` |
| 2026-10-28 | `Tomas Lateana` | Corrección de la iteración 2 según la revisión cruzada: avisos como vía principal y cálculo de carga de sondeo (ADR-0020), ADRs 0025 a 0027 completas, asistencia como módulo del núcleo (ADR-0026), patrones y tácticas en el paso 4, impact-log, vistas de módulos y dominio, diagramas de secuencia y nombres de tácticas | `iteration-2-ingestion.md`, `docs/03-adr/`, `docs/02-views/`, `impact-log.md` |
| 2026-10-28 | `Tadeo Brun` | Iteración 3 (consulta y escala): pasos 2 a 7, ADRs 0040 a 0045, API de itinerarios v1 y evento `trip.changed.v1`, vistas C&C, despliegue, módulos, dominio y secuencias SEQ-3, SEQ-4 y SEQ-6 | `iteration-3-query-scale.md`, `docs/03-adr/0040` a `0045`, `specs/`, `docs/02-views/` |
| 2026-10-28 | `Tadeo Brun` | Correcciones de la iteración 3 tras una auditoría independiente: evento `panel.changed.v1` y cola por instancia (ADR-0046), ADR-0042 comparada con la base de ADR-0003, monitor en tres zonas, CON-5, separación de ADRs (0046, 0047, 0048), reglas de reservas sin fechas, borradas y reactivación, nombres de tácticas según Bass | `iteration-3-query-scale.md`, `docs/03-adr/`, `specs/`, `docs/02-views/`, `constraints-concerns.md` |
| 2026-10-28 | `Tadeo Brun` | Wiki: portada y menú lateral con el proceso ADD centralizado en una página con links a las iteraciones 1 a 4, plan y registro de impactos; links rotos corregidos | `wiki/Home.md`, `wiki/_Sidebar.md`, `docs/01-add/ADD.md`, `docs/WIKI.md` |
| 2026-10-28 | `Tomas Lateana` (revisión) + `Tadeo Brun` (correcciones) | Revisión cruzada de la iteración 3: orden SSE y reconexión, escrituras con una sola copia en la base, concurrencia por usuario en el panel, deduplicación de push y colas del notificador, tamaño del panel, aperturas sin caché en QA-3 | `iteration-3-query-scale.md`, ADRs 0040, 0041, 0042 y 0046, `sequence-views.md`, `itinerary-api.v1.yaml`, `ingestion-operations.md` |
|  |  |  |  |
