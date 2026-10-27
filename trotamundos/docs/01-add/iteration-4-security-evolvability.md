# Iteración 4 — Seguridad, compartición, i18n, analítica y evolucionabilidad

**Responsable:** Ambos
**Fecha:** `<inicio>` a `<fin>`
**Estado:** Pendiente
**Rango de ADRs:** 0060 a 0079 (ver [CONTRIBUTING](../../CONTRIBUTING.md))

---

## Paso 2 — Objetivo de la iteración

Resolver lo que cruza todo el sistema: compartir itinerarios de forma segura, operar en varios países, permitir
la analítica pesada sin afectar a los usuarios y dejar la arquitectura lista para nuevos medios de transporte.

### Drivers seleccionados

| ID | Descripción | Prioridad |
|---|---|---|
| RF-07 | Analítica de datos | Media |
| RF-08 | Compartir itinerarios | Media |
| QA-7 | Seguridad de itinerarios compartidos | M, M |
| QA-9 | Evolucionabilidad | M, M |
| QA-10 | Usabilidad e internacionalización | M, H |
| CRN-2 | Registro de eventos y monitoreo | — |

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
|  |  |

## Paso 4 — Conceptos de diseño elegidos

| Concepto elegido | Justificación | Alternativas descartadas | ADR |
|---|---|---|---|
| Almacén analítico propio alimentado por eventos de dominio (heredada de la iteración 1) | Ver ADR | Ver ADR | [ADR-0060](../03-adr/0060-almacen-analitico-separado.md) (propuesta) |

Candidatos a considerar (no son decisiones): autenticación y autorización delegadas, control de acceso por
itinerario, auditoría, almacén analítico separado y réplica de lectura, puntos de extensión o plug-ins para nuevos
transportes, internacionalización por recursos externos, residencia de datos por región.

## Paso 5 — Instanciación

| Decisión de instanciación | Justificación |
|---|---|
|  |  |

### Contratos nuevos o modificados

| Contrato | Archivo en `specs/` | Cambio |
|---|---|---|
|  |  |  |

## Paso 6 — Vistas actualizadas y ADRs creadas

| Vista | Qué cambió |
|---|---|
|  |  |

| ADR | Título | Estado |
|---|---|---|
|  |  |  |

## Paso 7 — Análisis

| Driver | Estado | Riesgos o pendientes |
|---|---|---|
| QA-7 |  |  |
| QA-9 |  |  |
| QA-10 |  |  |

### Evaluación final de la arquitectura

Antes de entregar, repasar todos los escenarios (H, H) con Scenario Walkthrough y hacer una sesión de Risk Storming
sobre la vista C&C y la de despliegue.

### Impacto en otras iteraciones

### ¿Se sigue iterando?

### Prototipo

| Qué parte implementa | Spec | ADRs |
|---|---|---|
|  |  |  |
