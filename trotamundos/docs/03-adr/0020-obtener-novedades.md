---
status: "proposed"
date: 2026-10-27
decision-makers: "Tomas Lateana; revisión cruzada pendiente"
consulted: "Asistencia de ChatGPT/Codex"
informed: "Revisión cruzada mediante el PR de iteración 2"
---

# Obtener novedades con sondeo configurable y avisos disponibles

## Context and Problem Statement

RF-01 exige sondear correo y RF-03 integrar APIs externas. No todas las fuentes ofrecen notificaciones ni cuotas iguales; QA-1 mide generación a visualización, no solo detección.

## Decision Drivers

* RF-01 y RF-03: obtención de novedades
* QA-1: frescura
* QA-6: interoperabilidad
* CRN-3: fallos y límites externos

## Considered Options

* Solo sondeo periódico
* Solo notificaciones
* Sondeo configurable con avisos cuando existan

## Decision Outcome

Opción propuesta: **Sondeo configurable con avisos cuando existan**. Mantener sondeo de correo y consultas por proveedor; aprovechar avisos donde existan y prever reconciliación. Un aviso puede requerir otra consulta. No fijar intervalos iguales para millones de cuentas sin cuota y carga.

Planificador configurable por vinculación, ejecución coordinada, consultas incrementales si la API las ofrece y receptor que guarda avisos antes de confirmarlos. Quotas y espera indicada por proveedor prevalecen sobre reintentos agresivos.

### Consequences

* Favorable: Adapta la obtención a cada fuente y permite reconciliar avisos faltantes.
* Desfavorable: Hay que coordinar cursores, cuotas y duplicados entre caminos.
* Las comprobaciones de cumplimiento se realizan en el paso 7/prototipo, no se declaran ejecutadas.

### Confirmation

Comparar detección/cola/aplicación/visualización con QA-1, simular avisos repetidos/perdidos y límites de solicitudes. Proveedor concreto y presupuesto temporal siguen pendientes.

## Pros and Cons of the Options

### Solo sondeo periódico

* A favor: Permite consultar fuentes sin notificaciones.
* En contra: Puede consumir cuota sin novedades y agrega espera de detección.

### Solo notificaciones

* A favor: Reduce sondeo y puede detectar rápido.
* En contra: Depende de capacidades externas y no cumple por sí solo el sondeo exigido.

### Sondeo configurable con avisos cuando existan

* A favor: Adapta la obtención a cada fuente y permite reconciliar avisos faltantes.
* En contra: Hay que coordinar cursores, cuotas y duplicados entre caminos.

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

### Entrada de notificaciones

Los avisos de terceros entran por la entrada global y el API Gateway regional, según ADR-0003/0004.
El receptor de ingesta no se expone directamente. Ver [ADR-0025](0025-enrutamiento-de-avisos.md).
