---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (revisión cruzada pendiente en el PR de la iteración 4)"
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

* **Login:** la app envía el email a la entrada global (por HTTPS). La entrada global calcula
  `HMAC(clave_directorio, email normalizado)`, con una clave que solo tiene la entrada global, y la busca en el
  directorio global mínimo, que devuelve la región de origen; el login sigue en el proveedor de identidad de esa
  región. El directorio guarda solo `HMAC(email) → región`. Como el cálculo se hace del lado del servidor y la clave
  no es pública, no se puede revertir con un diccionario ni usar desde afuera para averiguar si un email tiene cuenta
  (la consulta tiene límite de tasa y responde igual exista o no la cuenta: si no existe, deriva al proveedor de la
  región del país que indica la app, donde se puede crear). Una cuenta nueva se crea en la región que corresponde a
  su país y registra su HMAC en el directorio.
* **El directorio frente a CON-3:** el HMAC de un email es un seudónimo, y un seudónimo sigue siendo dato personal
  para normativas como el GDPR. Se acepta por proporcionalidad: es el mínimo indispensable para saber a qué región
  derivar el login (un identificador y una región por usuario, sin historia ni contenido), con el mismo criterio que
  el directorio de suscripciones de ADR-0025. Es distinto de copiar historiales de viajes a un almacén global, que
  ADR-0064 descarta.
* **Tokens:** el proveedor emite un token de acceso firmado de 15 minutos y un token de renovación de 30 días que se
  puede revocar. El token de acceso lleva `userId`, `homeRegion` y `emailHmac` (HMAC del email verificado con una
  clave común a los proveedores de todas las regiones, que usa ADR-0061 para atar una invitación a su destinatario
  sin mover emails entre regiones). La puerta de entrada valida firma y vencimiento con las claves públicas de los
  proveedores, que guarda en caché; no consulta al proveedor en cada solicitud.
* **Enrutamiento:** la entrada global elige la región por `homeRegion` del token (sin validar la firma, solo para
  elegir); una solicitud sin token se enruta por el prefijo de región del recurso (tarjetas para redes, tickets SSE,
  ADR-0062 y ADR-0063) o, en el login, por el directorio. La puerta de entrada de la región sí valida la firma.
* **Token de otra región:** la puerta de entrada rechaza (`401`) un token cuyo `homeRegion` no es el suyo, **salvo**
  que la solicitud le llegue por el canal mTLS desde la puerta de entrada de otra región (ADR-0062) y se refiera a un
  recurso con el prefijo de su región (viajes e invitaciones). En ese caso valida la firma con las claves del
  proveedor de la región del token. El permiso sobre el recurso lo decide el núcleo (ADR-0061).
* **Revocación:** cerrar sesión o bloquear una cuenta comprometida revoca el token de renovación. El token de acceso
  vigente sigue sirviendo hasta 15 minutos (riesgo aceptado). El permiso sobre un viaje compartido no depende del
  token: se verifica en cada lectura (ADR-0061).
* **SSE:** el navegador no permite enviar el encabezado `Authorization` en una conexión SSE. La app pide con su token
  un ticket (`POST /panel/events/ticket`) y abre `GET /panel/events?ticket=...`. El ticket está firmado por la
  puerta de entrada, lleva el prefijo de la región, el `userId` y un vencimiento de 30 s, y solo sirve para abrir la
  conexión de avisos; se valida sin estado compartido entre las instancias de la puerta. No se controla el uso único:
  reusarlo dentro de esos 30 s solo abre otra conexión de avisos del mismo usuario, que no lleva datos de reservas
  (ADR-0046). No queda en los logs.
* El proveedor de identidad se despliega en cada región con instancias en al menos dos zonas (ADR-0003). El
  directorio global se replica en varias regiones, como la entrada global.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *autenticar actores* (seguridad) | Token firmado por el proveedor de identidad en cada solicitud | QA-7 |
| Táctica *limitar el acceso* (seguridad) | Solo la puerta de entrada acepta solicitudes externas, y solo con token válido | QA-7 |
| Táctica *revocar el acceso* (seguridad, reaccionar a ataques) | Bloqueo de una cuenta comprometida: se revoca su token de renovación | QA-7 |
| Táctica *limitar la exposición* (seguridad) | El directorio guarda solo un HMAC calculado en el servidor; vida corta del token de acceso | QA-7, CON-3 |
| Patrón *Federated Identity* / token firmado (OpenID Connect) | El proveedor emite, la puerta valida sin consultar | QA-5 |
| Táctica *redundant spare* (disponibilidad) | Un proveedor por región, con instancias en dos zonas | QA-4 |

### Consequences

* Good, because la puerta de entrada y el núcleo siguen sin estado de sesión (QA-5).
* Good, because los emails y credenciales quedan en la región de origen (CON-3).
* Good, because si cae la identidad de una región, solo sus usuarios no pueden iniciar sesión ni renovar el token;
  quienes ya tienen un token de acceso siguen hasta que venza (a lo sumo 15 minutos).
* Good, because es un estándar: permite agregar más adelante login con Google o Apple sin cambiar la arquitectura.
* Bad, because un token de acceso revocado sigue valiendo hasta 15 minutos.
* Bad, because el directorio global guarda un seudónimo de cada usuario fuera de su región (se acepta por
  proporcionalidad, ver la regla) y hay que custodiar su clave.
* Bad, because el directorio es necesario para iniciar sesión en un dispositivo nuevo: si cae en todas las regiones a
  la vez, nadie puede iniciar sesión desde cero (es el mismo punto de falla que se le marca a B2, acotado al login).
  Se mitiga replicándolo en varias regiones y con la app recordando la región del último login.
* Bad, because un ticket SSE copiado sirve para abrir otra conexión de avisos durante 30 s (sin datos de reservas).
* Bad, because cambiar la región de origen de un usuario exige mover su identidad y actualizar el directorio.

### Confirmation

Prototipo: un proveedor de identidad local emite tokens; la puerta de entrada rechaza un token vencido, uno con firma
inválida y uno de otra región que no llega por el canal entre regiones; acepta uno de otra región que llega por ese
canal; un ticket SSE vencido no abre la conexión.

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

* Good, because respeta CON-3 para emails y credenciales, y aísla por región las fallas del login y de la renovación.
* Bad, because necesita el directorio global (un seudónimo por usuario) para el login en un dispositivo nuevo, y ese
  directorio es un punto de falla para ese caso.

### B2. Uno global

* Good, because es más simple.
* Bad, because guarda emails y credenciales de todos los usuarios en un solo lugar (CON-3) y, si cae, nadie puede
  iniciar sesión ni renovar tokens en ninguna región: afecta también a quien ya tenía sesión, no solo a quien entra
  desde un dispositivo nuevo.

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
