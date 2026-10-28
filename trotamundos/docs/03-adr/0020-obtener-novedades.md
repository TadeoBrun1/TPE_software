---
status: "proposed"
date: 2026-10-28
decision-makers: "Tomas Lateana; revisión cruzada pendiente en PR #4"
consulted: "Revisión de Tadeo Brun y asistencia de ChatGPT/Codex"
---

# Obtener correo mediante avisos y reconciliación adaptable

## Context and Problem Statement

Sondear 15 millones de buzones cada 60 segundos exige al menos 250.000 consultas/s globales, antes de paginación,
lectura de mensajes y reintentos. Usar 2 millones de usuarios semanales como si fueran buzones conectados daría
33.333 consultas/s; esa equivalencia no es un dato del enunciado. Las novedades por segundo no dimensionan el sondeo.
RF-01 conserva el sondeo autorizado. QA-1 exige cinco minutos de extremo a extremo y QA-5 exige escala.
Gmail y Microsoft Graph ofrecen avisos de cambios, pero requieren suscripciones vigentes y recuperación de avisos
perdidos. IMAP IDLE mantiene conexiones: no equivale a un webhook sin coste por buzón.

## Decision Drivers

* RF-01 y RF-03: obtener correo y novedades de terceros
* QA-1 y QA-5: frescura y carga total de detección
* QA-6: procesar el 99,9 % de mensajes válidos sin pérdida ni duplicación
* QA-8 y CRN-3: acceso autorizado, cuotas y recuperación

## Considered Options

* A. Sondeo uniforme cada 60 segundos
* B. Solo avisos del proveedor
* C. Avisos como vía principal y sondeo incremental de reconciliación

## Decision Outcome

Chosen option: **C. Avisos como vía principal y sondeo incremental de reconciliación**. Cada proveedor capaz de enviar avisos
los utiliza también para correo. El receptor persiste trabajo, agrupa avisos por vinculación y dispara consultas
incrementales desde el cursor confirmado. El planificador renueva suscripciones antes del vencimiento, distribuye
renovaciones y mantiene sondeo de respaldo. El gestor detiene suscripciones y accesos tras revocación.

Se aplican *Event-Driven Consumer* al canal de avisos y consumo periódico al trabajo de reconciliación. Este último
es análogo a *Polling Consumer*; consultar una API de buzón no convierte automáticamente toda la integración en ese
patrón de mensajería. Se limitan concurrencia y demanda por proveedor; los adaptadores respetan `Retry-After`.

[Políticas operativas](../../specs/ingestion-operations.md) calcula consultas, renovaciones y capacidad, y distingue
el perfil adaptable de una garantía de QA-1 a escala. Si faltan avisos, sondeos de 15 minutos o 6 horas no cumplen
cinco minutos. Mantener QA-1 a escala exige recuperación acotada para todas las cuentas y cuotas suficientes;
la aprobación de esta ADR no modifica el requisito.

### Consequences

* Good, because se evita consultar todos los buzones cada minuto en funcionamiento normal y se recuperan huecos mediante cursores.
* Bad, because avisos y reconciliación requieren estado de suscripción, cuotas, paginación y deduplicación.
* Bad, because el perfil de menor frecuencia reduce coste a cambio de frescura durante avisos perdidos; ese conflicto queda abierto en QA-1.

### Confirmation

Simular avisos perdidos y duplicados, suscripción vencida, cursor inválido y recuperación completa. Medir consultas/s,
renovaciones/s, conexiones y demora por proveedor. Exigir el presupuesto de 120 s de detección antes de afirmar
QA-1; incluir cuentas inactivas en la prueba, sin cambiar silenciosamente el alcance.

## Pros and Cons of the Options

### A. Sondeo uniforme cada 60 segundos

* Good, because funciona sin soporte de avisos.
* Bad, because consume cuota aun sin cambios y el coste global calculado no está respaldado por capacidad externa.

### B. Solo avisos del proveedor

* Good, because evita sondeos vacíos en condiciones normales.
* Bad, because un aviso perdido o una suscripción vencida puede dejar un buzón sin recuperar.

### C. Avisos como vía principal y sondeo incremental de reconciliación

* Good, because combina detección por avisos con recuperación incremental y prioridades.
* Bad, because el coste de respaldo sigue existiendo y las frecuencias largas no garantizan QA-1.

## More Information

[Contrato regional](../../specs/notification-routing.md) · [Operación](../../specs/ingestion-operations.md).
Fuentes: [Gmail push](https://developers.google.com/workspace/gmail/api/guides/push),
[Microsoft Graph](https://learn.microsoft.com/en-us/graph/outlook-change-notifications-overview),
[ciclo de vida Graph](https://learn.microsoft.com/en-us/graph/change-notifications-lifecycle-events).
