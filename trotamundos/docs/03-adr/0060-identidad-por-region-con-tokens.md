---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (revisión cruzada en el PR de la iteración 4)"
informed: ""
---

# Autenticación con un proveedor de identidad por región y tokens de vida corta

## Context and Problem Statement

La puerta de entrada "valida la identidad de quien llama" (ADR-0004), pero no está definido cómo. Además, la entrada
global necesita conocer la región de origen del usuario para enrutar cada solicitud (ADR-0003), y la identidad
guarda datos personales (email). Hay que decidir cómo se autentica el viajero, dónde vive su identidad y cómo se
autentica la conexión SSE del notificador (ADR-0046).

## Decision Drivers

* QA-7 Seguridad: saber con certeza quién pide cada itinerario, para poder rechazar a quien no fue designado.
* QA-5 Escalabilidad: validar la identidad en cada solicitud sin consultar un servicio central ni guardar sesiones.
* QA-4 Disponibilidad: la falla de la identidad de una región no debe impedir el acceso en las demás.
* CON-3 (suposición): los datos personales quedan en la región de origen.
* ADR-0003: la entrada global enruta por región de origen.

## Considered Options

Cómo se autentica:

* A1. Proveedor de identidad separado (OpenID Connect / OAuth 2.0) con tokens de acceso firmados de vida corta y
  token de renovación
* A2. Login propio dentro del módulo `usuarios` del núcleo
* A3. Sesiones guardadas en el servidor, con cookie de sesión

Dónde vive la identidad:

* B1. Un proveedor de identidad por región, más un directorio global mínimo para encontrar la región en el login
* B2. Un proveedor de identidad global

## Decision Outcome

Chosen options: "A1. Proveedor de identidad con tokens de vida corta" y "B1. Uno por región con directorio global
mínimo", because la puerta de entrada valida cada token localmente (sin red ni sesiones), los datos personales
quedan en la región del usuario y la falla de una región no afecta el login de las otras.

Reglas:

* **Login:** la app envía a la entrada global un hash del email. El directorio global mínimo traduce ese hash a la
  región de origen; la entrada global deriva el login al proveedor de identidad de esa región. El directorio guarda
  solo `hash(email) → región`, sin datos personales legibles (mismo criterio que el directorio de suscripciones de
  ADR-0025). Una cuenta nueva se crea en la región que corresponde al país del usuario y registra su hash ahí.
* **Tokens:** el proveedor emite un token de acceso firmado de 15 minutos, con `userId` y `homeRegion`, y un token de
  renovación de 30 días que se puede revocar. La puerta de entrada valida firma y vencimiento con las claves públicas
  del proveedor, que guarda en caché; no consulta al proveedor en cada solicitud.
* **Enrutamiento:** la entrada global lee `homeRegion` del token (sin validar la firma, solo para elegir región); la
  puerta de entrada de esa región sí valida la firma, y si la región no coincide rechaza la solicitud.
* **Revocación:** cerrar sesión o bloquear una cuenta revoca el token de renovación. El token de acceso vigente sigue
  sirviendo hasta 15 minutos (riesgo aceptado). Para revocar el acceso a un viaje compartido no hace falta esperar:
  el permiso se verifica en cada lectura (ADR-0061).
* **SSE:** el navegador no permite enviar el encabezado `Authorization` en una conexión SSE. La app pide con su token
  un ticket de un solo uso (`POST /panel/events/ticket`, válido 30 s) y abre `GET /panel/events?ticket=...`. El
  ticket no sirve para otra cosa y no queda en los logs.
* El proveedor de identidad se despliega en cada región con instancias en al menos dos zonas (ADR-0003).

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *autenticar actores* (seguridad) | Token firmado por el proveedor de identidad en cada solicitud | QA-7 |
| Táctica *limitar el acceso* (seguridad) | Solo la puerta de entrada acepta solicitudes externas, y solo con token válido | QA-7 |
| Táctica *revocar el acceso* (seguridad) | Revocación del token de renovación; vida corta del token de acceso | QA-7 |
| Patrón *Federated Identity* / token firmado (OpenID Connect) | El proveedor emite, la puerta valida sin consultar | QA-5 |
| Táctica *redundant spare* (disponibilidad) | Un proveedor por región, con instancias en dos zonas | QA-4 |

### Consequences

* Good, because la puerta de entrada y el núcleo siguen sin estado de sesión (QA-5).
* Good, because los emails y credenciales quedan en la región de origen (CON-3).
* Good, because si cae la identidad de una región, solo sus usuarios no pueden iniciar sesión; quienes ya tienen
  token siguen usando el sistema hasta que venza.
* Good, because es un estándar: permite agregar más adelante login con Google o Apple sin cambiar la arquitectura.
* Bad, because un token de acceso revocado sigue valiendo hasta 15 minutos.
* Bad, because hay un directorio global más que operar (aunque sin datos personales legibles).
* Bad, because cambiar la región de origen de un usuario exige mover su identidad y actualizar el directorio.

### Confirmation

Prototipo: un proveedor de identidad local emite tokens; la puerta de entrada rechaza un token vencido, uno con firma
inválida y uno de otra región; un ticket SSE sirve una sola vez.

## Pros and Cons of the Options

### A1. Proveedor de identidad con tokens

* Good, because valida localmente y es estándar.
* Bad, because es un componente más, crítico para el login.

### A2. Login propio en el núcleo

* Good, because es un componente menos.
* Bad, because mezcla el manejo de credenciales con el dominio de viajes, y cada cambio de login toca el núcleo.

### A3. Sesiones en el servidor

* Good, because la revocación es inmediata.
* Bad, because cada solicitud consulta un almacén de sesiones compartido y el núcleo deja de ser sin estado
  (ADR-0001, QA-5).

### B1. Uno por región

* Good, because respeta CON-3 y aísla fallas por región.
* Bad, because necesita el directorio global para el login.

### B2. Uno global

* Good, because es más simple.
* Bad, because guarda los emails de todos los usuarios en un solo lugar (CON-3) y, si cae, nadie puede iniciar sesión
  en ninguna región.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 4, [iteration-4-security-evolvability](../01-add/iteration-4-security-evolvability.md) |
| Drivers | QA-7, QA-5, QA-4, CON-3 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md), [deployment-view](../02-views/deployment-view.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0003](0003-despliegue-por-regiones-con-region-de-origen.md), [0004](0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md), [0025](0025-enrutamiento-de-avisos.md), [0046](0046-notificador-de-cambios-del-panel.md), [0061](0061-comparticion-con-cuenta-y-auditoria.md) |
| Código del prototipo | `prototype/` |
