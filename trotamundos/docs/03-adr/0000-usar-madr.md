---
status: "accepted"
date: 2026-10-14
decision-makers: "<A>, <B>"
---

# Usar MADR para registrar las decisiones de arquitectura

## Context and Problem Statement

El enunciado exige documentar las decisiones de diseño con ADRs en formato MADR. Hace falta un formato fijo y una
convención común para que las decisiones de las cuatro iteraciones sean consistentes y trazables.

## Decision Drivers

* CON-2: ADRs en formato MADR.
* CRN-5: trazabilidad entre drivers, decisiones, vistas, specs y código.
* Trabajo en paralelo de dos personas.

## Considered Options

* MADR con una ADR por archivo en `docs/03-adr/`
* Plantilla de Nygard (título, contexto, decisión, estado, consecuencias)
* Registrar las decisiones solo dentro de los documentos de iteración

## Decision Outcome

Chosen option: "MADR con una ADR por archivo", because es el formato pedido, incluye las alternativas
consideradas y sus pros y contras, y permite enlazar cada decisión desde iteraciones y vistas.

### Consequences

* Good, because cada decisión queda con contexto, alternativas y consecuencias.
* Good, because los bloques de numeración evitan conflictos entre ramas.
* Bad, because escribir ADRs completas lleva tiempo, y hay que ser selectivos con lo que es realmente arquitectónico.

## More Information

Convenciones en [README](README.md) y [CONTRIBUTING](../../CONTRIBUTING.md).
