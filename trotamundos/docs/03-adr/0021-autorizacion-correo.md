---
status: "proposed"
date: 2026-10-27
decision-makers: "Tomas Lateana; revisión cruzada pendiente"
consulted: "Asistencia de ChatGPT/Codex"
informed: "Revisión cruzada mediante el PR de iteración 2"
---

# Acceso delegado al correo con mínimo privilegio y revocación

## Context and Problem Statement

Ingesta consulta información personal. Identificarse en Trotamundos no autoriza leer el buzón y una whitelist no limita necesariamente lo que permite leer la API externa.

## Decision Drivers

* QA-8: acceso autorizado
* CRN-4: secretos/configuración
* RF-01/RF-02: correo y filtros

## Considered Options

* Guardar contraseña del buzón
* Autorización delegada del proveedor
* Solo correos reenviados manualmente

## Decision Outcome

Chosen option: **Autorización delegada del proveedor**. Usar autorización delegada mediante OAuth 2.0 donde el proveedor lo admita, con el menor permiso suficiente. Seleccionar proveedores compatibles y concretar el flujo/alcances en su contrato, sin pedir contraseñas como alternativa silenciosa.

El gestor comprueba habilitación al iniciar consultas, coordina renovaciones y mantiene secretos fuera de eventos/logs. Desvincular bloquea nuevos accesos y trabajo aún no publicado según política explícita; no cancela retroactivamente solicitudes ni elimina reservas. La confirmación local de revocación debe coordinarse con el inicio de consultas/publicación, no solo cambiar una bandera leída mucho antes.

### Patrones y tácticas

* Patrón o mecanismo: Protocolo OAuth 2.0 (mecanismo).
* Tácticas: Authorize actors, Limit access y Revoke access: controlar autorización, alcance y revocación.

### Consequences

* Favorable: Evita recibir la contraseña y permite permisos/renovación según contrato externo.
* Desfavorable: Requiere tokens protegidos, coordinación de renovación y revocación.

### Confirmation

Simular vinculación válida, expiración, renovación inválida, revocación con trabajo pendiente y consulta ya iniciada; inspeccionar datos conservados. Se necesita revisión de seguridad y contrato de proveedor antes de una integración real.

## Pros and Cons of the Options

### Guardar contraseña del buzón

* A favor: Puede permitir acceso en mecanismos que aún la admiten.
* En contra: Credencial sensible y permisos potencialmente amplios; compatibilidad no asumida.

### Autorización delegada del proveedor

* A favor: Evita recibir la contraseña y permite permisos/renovación según contrato externo.
* En contra: Requiere tokens protegidos, coordinación de renovación y revocación.

### Solo correos reenviados manualmente

* A favor: Evita consultar directamente el buzón.
* En contra: No satisface por sí solo la incorporación por sondeo de correo autorizada.

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

### Propiedad de la configuración

El núcleo administra usuario, región, filtros y vinculaciones. Ingesta administra cursores, trabajos y secretos
protegidos. La vigencia se obtiene por una interfaz interna con coordinación de revocación; no mediante lectura
directa de tablas ni una segunda autoridad de permisos. OAuth de correo no decide la autenticación de la app.

### Protocolo refinado de vigencia

[ingestion-authorization.md](../../specs/ingestion-authorization.md) fija estados/revisiones, inicio de operaciones
y barrera de desvinculación. La app solo confirma éxito cuando la autoridad coordinó el sellado; llamadas ya
iniciadas no se cancelan retroactivamente. La implementación debe probar carreras, no asumirlas resueltas por un flag.
