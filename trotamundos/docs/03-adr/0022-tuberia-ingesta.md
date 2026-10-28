---
status: "accepted"
date: 2026-10-27
decision-makers: "Tomas Lateana"
consulted: "Asistencia de IA"
informed: "Revisión cruzada mediante el PR de iteración 2"
---

# Procesar novedades mediante etapas internas separadas

## Context and Problem Statement

Obtener un mensaje no significa tener una reserva válida. Selección, interpretación y normalización son cambios distintos y deben distinguir un descarte legítimo de un error de extracción.

## Decision Drivers

* RF-01/RF-02: correo y filtros
* RF-03 y QA-6: formatos externos
* QA-8: tratamiento limitado de datos

## Considered Options

* Rutina única de consulta y procesamiento
* Tubería de etapas internas
* Servicio por etapa

## Decision Outcome

Chosen option: **Tubería de etapas internas**. Selección → extracción → normalización → validación → registro durable/publicación, como componentes internos de ingesta, sin un microservicio por etapa.

El procesamiento entrega un evento válido, descarte justificado o caso pendiente. Solo almacenar contenido necesario con permisos/retención. Correo usa reglas de remitentes y pertinencia; APIs usan su contrato de origen. No confundir remitente permitido con contenido auténtico o seguro.

### Patrones y tácticas

* Patrón o mecanismo: Pipes and Filters.
* Tácticas: Increase cohesion: selección, extracción, normalización y validación como responsabilidades separadas.

### Consequences

* Favorable: Permite cambiar/probar etapas y clasificar resultados.
* Desfavorable: Exige acordar entradas, salidas y errores.

### Confirmation

Casos por etapa: correo irrelevante, remitente permitido con formato desconocido, dato temporal inválido y reserva mínima válida. No descartar en silencio una reserva que no se sabe interpretar.

## Pros and Cons of the Options

### Rutina única de consulta y procesamiento

* A favor: Arranque pequeño y menos interfaces internas.
* En contra: Mezcla acceso, filtros, extracción y publicación.

### Tubería de etapas internas

* A favor: Permite cambiar/probar etapas y clasificar resultados.
* En contra: Exige acordar entradas, salidas y errores.

### Servicio por etapa

* A favor: Despliegue y escalado separados.
* En contra: Agrega comunicación y recuperación distribuida sin necesidad medida.

## More Information

| Elemento | Enlace |
|---|---|
| Iteración | [2 — Ingesta](../01-add/iteration-2-ingestion.md) |
| Drivers | [Requisitos y escenarios](../00-requirements/architectural-drivers.md) |
| Vistas | [Ingesta](../02-views/ingestion-view.md), [secuencias](../02-views/ingestion-sequences.md) |
| Contrato | [Semántica](../../specs/ingestion-contract.md), [AsyncAPI](../../specs/asyncapi/booking-change-detected.v1.yaml) |
| Relación con 1/3 | [Impactos](../01-add/impact-log.md); base integrada y coordinada mediante PRs #3, #4, #6 y #7; validación de implementación pendiente |
| ADR relacionadas | [Índice](README.md), ADR-0020 a 0024 |
| Prototipo | [Alcance](../../prototype/README.md); implementación pendiente |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #4](https://github.com/TadeoBrun1/TPE_software/pull/4),
merge `0801315` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
