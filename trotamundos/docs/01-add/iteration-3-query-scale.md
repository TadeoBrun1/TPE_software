# Iteración 3 — Consulta, latencia, disponibilidad y escala

**Responsable:** `<B>`
**Fecha:** `<inicio>` a `<fin>`
**Estado:** Pendiente
**Rango de ADRs:** 0040 a 0059 (ver [CONTRIBUTING](../../CONTRIBUTING.md))

> Solo B edita este archivo. Si algo de acá afecta a la iteración 2, anotarlo en [impact-log.md](impact-log.md).

---

## Paso 2 — Objetivo de la iteración

Diseñar cómo el viajero consulta y gestiona sus viajes con baja latencia, alta disponibilidad y capacidad de escalar
ante picos de tráfico.

### Drivers seleccionados

| ID | Descripción | Prioridad |
|---|---|---|
| RF-04 | Gestión manual de reservas | Media |
| RF-05 | Ciclo de vida del viaje (agrupar y archivar) | Alta |
| QA-2 | Latencia web (800 ms) | H, M |
| QA-3 | Primer despliegue móvil (1,4 s) | M, M |
| QA-4 | Disponibilidad (5 min/mes) | H, H |
| QA-5 | Escalabilidad y picos | H, H |
| CRN-4 | Despliegue y entornos | — |

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
| `<contenedor de consulta definido en la iteración 1>` |  |

## Paso 4 — Conceptos de diseño elegidos

| Concepto elegido | Justificación | Alternativas descartadas | ADR |
|---|---|---|---|
|  |  |  | ADR-0040 |

Candidatos a considerar (no son decisiones): CQRS y modelo de lectura, caché y réplicas de datos, balanceo de carga,
autoescalado, redundancia activa o pasiva, detección de fallas, despliegue multirregión, CDN, paginación y carga
incremental para móvil, tareas programadas para archivar viajes completados.

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
| QA-2 |  |  |
| QA-4 |  |  |
| QA-5 |  |  |

### Impacto en otras iteraciones

<!-- Especialmente iteración 2: cómo llegan los datos al modelo de lectura, consistencia, frescura. -->

### ¿Se sigue iterando?

### Prototipo

| Qué parte implementa | Spec | ADRs |
|---|---|---|
|  |  |  |
