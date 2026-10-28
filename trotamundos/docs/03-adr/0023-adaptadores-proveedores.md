---
status: "proposed"
date: 2026-10-27
decision-makers: "Tomas Lateana; revisión cruzada pendiente"
consulted: "Asistencia de ChatGPT/Codex"
informed: "Revisión cruzada mediante el PR de iteración 2"
---

# Encapsular fuentes externas detrás de puertos y adaptadores

## Context and Problem Statement

Los proveedores difieren en autenticación, paginación, campos y estados. El acceso al buzón y el formato de una confirmación emitida por un hotel son responsabilidades independientes.

## Decision Drivers

* RF-03 y QA-6: intercambio correcto
* QA-9: evolución como condicionante
* CON-1/CON-2: contratos externos existentes

## Considered Options

* Condicionales de proveedor dispersos en el flujo
* Puertos comunes y adaptadores específicos
* Formato de un proveedor como modelo interno

## Decision Outcome

Chosen option: **Puertos comunes y adaptadores específicos**. Definir puertos de acceso y adaptadores por proveedor. Separar adaptador de buzón de extractores por emisor/formato. Normalizar datos, preservando referencias y versión externa cuando existan.

Errores se clasifican en temporales, cuota, autorización o datos. No inventar zonas horarias/referencias ausentes. El formato común y sus reglas mínimas se revisan con el núcleo antes de implementar. Integración futura no se considera cumplida solo por dibujar una interfaz.

### Patrones y tácticas

* Patrón o mecanismo: Ports and Adapters, Adapter y Canonical Data Model.
* Tácticas: Tailor interface y Adhere to standards: traducir contratos externos sin acoplar dominio.

### Consequences

* Favorable: Concentra cambios externos y permite simuladores por contrato.
* Desfavorable: Hay que mantener correspondencias y excepciones sin ocultar diferencias importantes.

### Confirmation

Dos simuladores con campos/estados distintos deben producir el contrato común; agregar otro adaptador sin modificar reglas de dominio existentes. Medición de esfuerzo de QA-9 pendiente.

## Pros and Cons of the Options

### Condicionales de proveedor dispersos en el flujo

* A favor: Pocas abstracciones iniciales.
* En contra: Cada incorporación obliga a revisar varias etapas.

### Puertos comunes y adaptadores específicos

* A favor: Concentra cambios externos y permite simuladores por contrato.
* En contra: Hay que mantener correspondencias y excepciones sin ocultar diferencias importantes.

### Formato de un proveedor como modelo interno

* A favor: Mapeo inicial reducido para esa fuente.
* En contra: Acopla núcleo y otras integraciones a un contrato externo ajeno.

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

### RF-06 y evolución

El adaptador de agencia pertenece al módulo saliente de asistencia del núcleo y usa un puerto distinto del acceso
entrante de ingesta; ver [ADR-0026](0026-integracion-agencia.md). Ningún módulo importa adaptadores del otro proceso.
