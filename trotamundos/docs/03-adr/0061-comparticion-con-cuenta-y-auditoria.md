---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (revisión cruzada en el PR de la iteración 4)"
informed: ""
---

# Compartición de viajes con personas designadas con cuenta, control en el núcleo y auditoría

## Context and Problem Statement

RF-08 pide compartir un itinerario con personas designadas, y QA-7 exige que el 100 % de los accesos de personas no
designadas se rechace y quede registrado. Hay que decidir cómo se identifica a la persona designada, dónde se
controla el permiso y cómo se registran los intentos.

## Decision Drivers

* QA-7: rechazar y registrar el 100 % de los accesos no designados.
* RF-08: compartir un viaje con personas específicas.
* ADR-0001: las reglas de negocio (quién comparte qué con quién) viven en el núcleo.
* ADR-0060: cada solicitud trae una identidad verificada.

## Considered Options

Cómo se identifica la persona designada:

* A1. Con cuenta propia de Trotamundos: el dueño invita por email y la persona acepta con su cuenta
* A2. Enlace secreto: quien tenga el link ve el viaje
* A3. Enlace más código de un solo uso enviado al email designado, sin cuenta

Dónde se controla el permiso:

* B1. En el módulo `comparticion` del núcleo, con registro de auditoría
* B2. En la puerta de entrada

## Decision Outcome

Chosen options: "A1. Con cuenta propia" y "B1. En el núcleo, con auditoría", because el permiso queda atado a una
identidad verificada (reenviar un link no da acceso) y las reglas siguen en el núcleo.

Reglas:

* **Invitar:** el dueño indica el email de la persona (`POST /trips/{tripId}/shares`). El núcleo crea una invitación
  pendiente y envía al email un enlace con un secreto de un solo uso que vence en 7 días. Si la persona no tiene
  cuenta, la crea (en su propia región, ADR-0060).
* **Aceptar:** la persona inicia sesión y acepta con ese secreto (`POST /shares/{shareId}/accept`). Desde ese momento
  el permiso queda atado a su `userId`: el enlace ya no sirve para nadie más, aunque se reenvíe. Aceptar dos veces
  con la misma cuenta no tiene efecto (idempotente).
* **Permiso:** solo lectura del viaje y sus reservas. La vista compartida no incluye las notas del dueño ni los
  códigos de reserva de los proveedores.
* **Revocar:** el dueño quita el permiso (`DELETE /trips/{tripId}/shares/{shareId}`) o cancela una invitación
  pendiente; tiene efecto en la siguiente lectura, porque el permiso se verifica siempre. Archivar el viaje mantiene
  los permisos; eliminarlo (ADR-0045) los borra junto con el email del invitado.
* **Control:** en cada lectura (`GET /shared/trips/{tripId}`), el módulo `comparticion` verifica que el `userId` del
  token tenga un permiso vigente sobre ese viaje. Si no, responde `404`, igual que si el viaje no existiera, para no
  revelar que existe.
* **Auditoría:** cada acceso a un viaje compartido, permitido o rechazado, y cada invitación, aceptación y revocación
  se escriben en un registro de auditoría de solo agregado, en la región del dueño del viaje, con: quién, qué viaje,
  cuándo, resultado y región desde la que llegó la solicitud
  ([access-audit.md](../../specs/access-audit.md)). El registro se escribe antes de responder; si no se puede
  escribir, la solicitud se rechaza con `503`. Así ningún acceso queda sin registrar (QA-7).
* El registro de auditoría no guarda datos del itinerario, se conserva 1 año (suposición, mismo plazo que ADR-0045)
  y solo lo consulta el equipo de seguridad; el dueño ve quién aceptó sus invitaciones.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *autorizar actores* (seguridad) | Permiso por viaje y persona, verificado en cada lectura | QA-7 |
| Táctica *auditar* (seguridad, recuperarse de ataques) | Registro de solo agregado de todos los accesos, permitidos o rechazados | QA-7 |
| Táctica *limitar la exposición* (seguridad) | Solo lectura; `404` en lugar de `403`; sin notas ni códigos de reserva | QA-7 |
| Táctica *revocar el acceso* (seguridad) | El dueño quita el permiso con efecto inmediato | QA-7 |

### Consequences

* Good, because el permiso es de la persona, no del enlace: reenviarlo no da acceso.
* Good, because revocar tiene efecto inmediato.
* Good, because cada intento queda registrado, permitido o rechazado.
* Bad, because quien recibe el viaje necesita una cuenta.
* Bad, because el email del invitado queda guardado en la región del dueño (lo cargó el dueño) hasta que se revoca
  el permiso o se elimina el viaje.
* Bad, because cada lectura de un viaje compartido escribe en el registro de auditoría; si el registro falla, la
  lectura se rechaza (se prioriza QA-7 sobre la disponibilidad de esa operación).

### Confirmation

Prototipo y pruebas: el dueño invita, la persona acepta y ve el viaje; otro usuario con el mismo enlace recibe `404`
y queda registrado; tras revocar, la persona recibe `404`; cada intento aparece en el registro de auditoría.

## Pros and Cons of the Options

### A1. Con cuenta propia

* Good, because el acceso queda atado a una identidad verificada.
* Bad, because exige cuenta.

### A2. Enlace secreto

* Good, because no exige cuenta.
* Bad, because cualquiera que reciba el enlace reenviado entra: no garantiza "personas designadas" (QA-7).

### A3. Enlace más código por email

* Good, because verifica la identidad sin cuenta.
* Bad, because agrega envío de códigos en cada acceso, y la persona no puede recibir avisos de cambios.

### B1. En el núcleo

* Good, because las reglas de compartición quedan junto con el resto del dominio.
* Bad, because la solicitud llega al núcleo antes de rechazarse.

### B2. En la puerta de entrada

* Good, because rechaza antes.
* Bad, because la puerta tendría que conocer reglas del dominio (quién compartió qué), que ADR-0001 asignó al núcleo.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 4, [iteration-4-security-evolvability](../01-add/iteration-4-security-evolvability.md) |
| Drivers | QA-7, RF-08 |
| Vistas afectadas | [module-view](../02-views/module-view.md), [domain-model](../02-views/domain-model.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml), [access-audit.md](../../specs/access-audit.md) |
| ADRs relacionadas | [0001](0001-nucleo-modular-con-procesos-separados.md), [0045](0045-ciclo-de-vida-y-archivado-de-viajes.md), [0060](0060-identidad-por-region-con-tokens.md), [0062](0062-lectura-de-viajes-compartidos-entre-regiones.md) |
| Código del prototipo | `prototype/` |
