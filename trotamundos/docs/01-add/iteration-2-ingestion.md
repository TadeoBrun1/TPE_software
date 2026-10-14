# Iteración 2 — Ingesta de reservas

**Responsable:** `<A>`
**Fecha:** `<inicio>` a `<fin>`
**Estado:** Pendiente
**Rango de ADRs:** 0020 a 0039 (ver [CONTRIBUTING](../../CONTRIBUTING.md))

> Solo A edita este archivo. Si algo de acá afecta a la iteración 3, anotarlo en [impact-log.md](impact-log.md).

---

## Paso 2 — Objetivo de la iteración

Diseñar cómo las reservas entran al sistema, desde el correo del usuario y desde sistemas de terceros, con la
frescura exigida y con acceso seguro a los correos.

### Drivers seleccionados

| ID | Descripción | Prioridad |
|---|---|---|
| RF-01 | Procesamiento de correo | Alta |
| RF-02 | Filtros y whitelists | Media |
| RF-03 | Integración con terceros | Alta |
| QA-1 | Frescura de actualizaciones (5 min) | H, H |
| QA-6 | Interoperabilidad | H, M |
| QA-8 | Seguridad de acceso a correos | H, M |
| CRN-3 | Errores de ingesta y reintentos | — |

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
| `<contenedor de ingesta definido en la iteración 1>` |  |

## Paso 4 — Conceptos de diseño elegidos

| Concepto elegido | Justificación | Alternativas descartadas | ADR |
|---|---|---|---|
|  |  |  | ADR-0020 |

Candidatos a considerar (no son decisiones): wrapper o adaptador por proveedor, pipes y filtros para el procesamiento
de correos, cola de mensajes, reintentos con backoff, monitoreo y heartbeat, validación de entrada, mínimo privilegio
en el acceso a correos, throttling hacia terceros.

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
| QA-1 |  |  |
| QA-6 |  |  |
| QA-8 |  |  |

### Impacto en otras iteraciones

<!-- Especialmente iteración 3: modelo de datos de reservas, eventos publicados, carga sobre el almacenamiento. -->

### ¿Se sigue iterando?

### Prototipo

| Qué parte implementa | Spec | ADRs |
|---|---|---|
|  |  |  |
