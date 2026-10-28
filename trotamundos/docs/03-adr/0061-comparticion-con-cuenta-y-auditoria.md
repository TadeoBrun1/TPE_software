---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (revisión cruzada pendiente en el PR de la iteración 4)"
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
  pendiente, guarda el email y su `emailHmac` (con la clave común de ADR-0060) y envía al email un enlace con un
  secreto que vence en 7 días. Si la persona no tiene cuenta, la crea en su propia región con ese email (ADR-0060).
* **Aceptar:** la persona inicia sesión y acepta con ese secreto (`POST /shares/{shareId}/accept`). El núcleo acepta
  solo si el `emailHmac` del token (email verificado por el proveedor de identidad de la región de quien acepta)
  coincide con el de la invitación. Así, aunque el enlace se reenvíe antes de aceptarlo, otra cuenta no puede
  aceptarlo, y no hace falta mover emails entre regiones. Desde la aceptación el permiso queda atado al `userId`.
  Aceptar dos veces con la misma cuenta no tiene efecto (idempotente).
* **Permiso:** solo lectura del viaje y sus reservas. La vista compartida no incluye las notas del dueño ni los
  códigos de reserva de los proveedores; los esquemas de `details` no pueden tener códigos ni datos personales
  (ADR-0066).
* **Quitar el permiso:** el dueño quita el permiso (`DELETE /trips/{tripId}/shares/{shareId}`) o cancela una
  invitación pendiente; tiene efecto en la siguiente lectura, porque el permiso se verifica siempre. Archivar el viaje
  mantiene los permisos; eliminarlo (ADR-0045) los borra junto con el email del invitado.
* **Control en el núcleo:** toda solicitud del núcleo sobre un viaje que no es del usuario del token pasa por el
  módulo `comparticion`, sea por `GET /shared/trips/{tripId}` o por cualquier otro endpoint (por ejemplo
  `GET /trips/{tripId}` con el identificador de un viaje ajeno). En `/shared/trips/{tripId}`, `comparticion`
  verifica que el usuario tenga un permiso vigente; en los endpoints del dueño (`/trips/...`, `/bookings/...`) un
  viaje ajeno se rechaza siempre, aunque haya permiso, porque el permiso es solo de lectura por la vista compartida.
  El rechazo es `404`, igual que si el viaje no existiera, para no revelar que existe.
* **Auditoría de todos los caminos** ([access-audit.md](../../specs/access-audit.md)), en un registro de solo
  agregado, antes de responder:
  * el núcleo de la región del dueño registra cada acceso a un viaje ajeno, permitido o rechazado, y cada
    invitación, aceptación (o intento) y quita de permiso;
  * la puerta de entrada registra en el registro de su región los rechazos que ocurren antes de llegar al núcleo del
    dueño sobre recursos de compartición: sin token o con token inválido, región del identificador inexistente y
    región del dueño que no responde.

  Si el registro no se puede escribir, la solicitud se rechaza (`503`) y la puerta deja el evento en sus logs
  estructurados con una alerta (ADR-0067). El rechazo está garantizado siempre; el registro, salvo que fallen a la vez
  el registro de auditoría y los logs de la región (riesgo residual aceptado).
* El registro de auditoría no guarda datos del itinerario ni emails, se conserva 1 año (suposición, mismo plazo que
  ADR-0045) y lo consulta el equipo de seguridad. El dueño ve el estado de cada invitación (pendiente, aceptada,
  vencida).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *autorizar actores* (seguridad) | Permiso por viaje y persona, verificado en cada lectura; aceptación atada al email invitado; el dueño puede quitar el permiso | QA-7 |
| Táctica *auditar* (seguridad, recuperarse de ataques) | Registro de solo agregado de todos los accesos, permitidos o rechazados, desde el núcleo y desde la puerta de entrada | QA-7 |
| Táctica *detectar intrusiones* (seguridad) | Alerta ante un aumento de rechazos sobre un mismo viaje o de un mismo actor | QA-7 |
| Táctica *limitar la exposición* (seguridad) | Solo lectura; `404` en lugar de `403`; sin notas ni códigos de reserva | QA-7 |

### Consequences

* Good, because el permiso es de la persona, no del enlace: reenviarlo no da acceso, ni antes ni después de aceptar.
* Good, because revocar tiene efecto inmediato.
* Good, because cada intento queda registrado, permitido o rechazado, también los que no llegan al núcleo.
* Bad, because quien recibe el viaje necesita una cuenta con el mismo email al que se lo invitó: si usa otro email,
  el dueño tiene que invitar ese.
* Bad, because el email del invitado queda guardado en la región del dueño (lo cargó el dueño) hasta que se revoca
  el permiso o se elimina el viaje.
* Bad, because cada lectura de un viaje compartido escribe en el registro de auditoría; si el registro falla, la
  lectura se rechaza (se prioriza QA-7 sobre la disponibilidad de esa operación).
* Bad, because el `emailHmac` del token depende de una clave común a todas las regiones, que hay que custodiar.

### Confirmation

Prototipo y pruebas: el dueño invita, la persona acepta y ve el viaje; otra cuenta con el enlace reenviado no puede
aceptarlo antes ni leerlo después (`404`); una solicitud sin token y una a `GET /trips/{tripId}` con un viaje ajeno
también se rechazan; tras quitar el permiso, la persona recibe `404`; cada intento aparece en el registro de
auditoría.

## Pros and Cons of the Options

### A1. Con cuenta propia

* Good, because el acceso queda atado a una identidad verificada.
* Bad, because exige cuenta.

### A2. Enlace secreto

* Good, because no exige cuenta.
* Bad, because cualquiera que reciba el enlace reenviado entra: no garantiza "personas designadas" (QA-7).

### A3. Enlace más código por email

* Good, because verifica la identidad sin cuenta.
* Bad, because agrega un envío de código por email en cada acceso, y sin cuenta no hay dónde guardar la lista de
  viajes compartidos con esa persona.

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
