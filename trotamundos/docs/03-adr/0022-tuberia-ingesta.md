---
status: "proposed"
date: 2026-10-27
decision-makers: "Tomas Lateana; revisión cruzada pendiente"
consulted: "Asistencia de ChatGPT/Codex"
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

Opción propuesta: **Tubería de etapas internas**. Selección → extracción → normalización → validación → registro durable/publicación, como componentes internos de ingesta, sin un microservicio por etapa.

El procesamiento entrega un evento válido, descarte justificado o caso pendiente. Solo almacenar contenido necesario con permisos/retención. Correo usa reglas de remitentes y pertinencia; APIs usan su contrato de origen. No confundir remitente permitido con contenido auténtico o seguro.

### Consequences

* Favorable: Permite cambiar/probar etapas y clasificar resultados.
* Desfavorable: Exige acordar entradas, salidas y errores.
* Las comprobaciones de cumplimiento se realizan en el paso 7/prototipo, no se declaran ejecutadas.

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
| Relación con 1/3 | [Impactos](../01-add/impact-log.md); base de 1 publicada en main, revisión de integración pendiente |
| ADR relacionadas | [Índice](README.md), ADR-0020 a 0024 |
| Prototipo | [Alcance](../../prototype/README.md); implementación pendiente |
