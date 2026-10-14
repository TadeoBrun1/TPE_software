# Iteración 1 — Estructura general del sistema

**Responsable:** Ambos
**Fecha:** `<inicio>` a `<fin>`
**Estado:** Pendiente
**Rango de ADRs:** 0001 a 0019 (ver [CONTRIBUTING](../../CONTRIBUTING.md))

---

## Paso 2 — Objetivo de la iteración

Establecer la estructura inicial del sistema: estilo arquitectónico, división en elementos de alto nivel y
estrategia general de despliegue, de modo que las iteraciones siguientes puedan refinar cada parte por separado.

### Drivers seleccionados

| ID | Descripción | Prioridad |
|---|---|---|
| CRN-1 | Estructura inicial del sistema | Alta |
| QA-5 | Escalabilidad (a nivel de estructura) | H, H |
| QA-9 | Evolucionabilidad (a nivel de estructura) | M, M |
| CON-7 | Integración con terceros por APIs estándar | Restricción |

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
| Sistema Trotamundos (completo) | En la 1ra iteración el sistema entero es el único elemento |

## Paso 4 — Conceptos de diseño elegidos

> Decisiones críticas: las toman las dos personas juntas. Si se usa IA, se confirman a mano.

| Concepto elegido | Justificación | Alternativas descartadas | ADR |
|---|---|---|---|
| `<estilo: por ejemplo monolito modular o microservicios>` |  |  | ADR-0001 |
| `<comunicación asíncrona / bus de eventos>` |  |  | ADR-0002 |
| `<separación de la carga analítica>` |  |  | ADR-0003 |
| `<estrategia de despliegue multirregión>` |  |  | ADR-0004 |

Candidatos a considerar (de Bass y Keeling, no son decisiones): SOA o microservicios, publish-subscribe, CQRS,
puertos y adaptadores para integraciones, balanceo de carga, caché.

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
| [Modelo de dominio](../02-views/domain-model.md) | Versión inicial |
| [Vista de módulos](../02-views/module-view.md) | Versión inicial |
| [Vista C&C](../02-views/cc-view.md) | Versión inicial |
| [Vista de despliegue](../02-views/deployment-view.md) | Versión inicial |

| ADR | Título | Estado |
|---|---|---|
| 0001 |  | Propuesta |

## Paso 7 — Análisis

| Driver | Estado | Riesgos o pendientes |
|---|---|---|
| CRN-1 |  |  |
| QA-5 |  |  |
| QA-9 |  |  |

### Impacto en otras iteraciones

Esta iteración define los **elementos compartidos** que las siguientes no deben romper en silencio: contenedores,
modelo de datos de reservas, bus de eventos. Listarlos acá cuando estén definidos.

| Elemento compartido | Usado por iteración |
|---|---|
|  |  |

### ¿Se sigue iterando?

Sí: iteraciones 2 y 3 en paralelo.

### Prototipo

| Qué parte implementa | Spec | ADRs |
|---|---|---|
| Esqueleto de servicios y contratos mínimos | `specs/` | 0001 |
