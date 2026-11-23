---
status: "accepted"
date: 2026-11-22
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Eliminación de la cuenta: borrado inmediato en el núcleo y aviso por evento al resto de los procesos

## Context and Problem Statement

El enunciado no pide eliminar cuentas, pero dos decisiones lo dejaron pendiente. ADR-0081 dice que el perfil de
recomendación se borra "cuando se elimina su cuenta" y que ese borrado todavía no estaba diseñado. ADR-0064 dice
que retener los hechos analíticos al eliminar una cuenta debe validarse. Además, los datos de un usuario ya no
viven en un solo lugar:

* el núcleo guarda los viajes, las reservas, el panel, las invitaciones, los marcadores y las vinculaciones;
* la ingesta guarda la configuración técnica de las vinculaciones, los cursores y el trabajo pendiente;
* el proveedor de identidad guarda las credenciales y los tokens de renovación;
* el directorio global guarda el HMAC del email;
* el notificador guarda los dispositivos;
* la recomendación guarda el perfil y el feedback;
* la analítica guarda hechos seudonimizados;
* la auditoría guarda registros con el usuario como actor.

Hay que decidir cómo se entera cada proceso, cuándo se borra y qué pasa con lo que no es del usuario en forma
directa.

## Decision Drivers

* QA-14: el viajero borra sus datos y se borran en 24 h o menos (para el perfil de recomendación).
* CON-3 (suposición): los datos personales quedan en la región de origen y no se conservan más de lo necesario.
* QA-7: la auditoría de accesos es la evidencia de seguridad y solo se agrega.
* ADR-0001 y ADR-0002: cada proceso es dueño de sus datos y se comunican por publicación/suscripción.
* ADR-0060: los tokens de acceso duran 15 minutos y la puerta los valida sin consultar al proveedor de identidad.

## Considered Options

Cómo se enteran los procesos:

* A1. Evento `account.deleted.v1` publicado por el núcleo
* A2. Orquestación desde el núcleo, que llama a cada proceso y espera su confirmación
* A3. Conciliación diaria contra una lista de cuentas eliminadas

Cuándo se borra:

* B1. En el momento, sin vuelta atrás
* B2. Con un período de gracia de 30 días en el que la cuenta se puede recuperar

Qué pasa con la analítica y la auditoría:

* C1. Se conservan hasta que vence su retención
* C2. Se borra lo que se pueda ubicar y la auditoría seudonimiza al actor

## Decision Outcome

Chosen options: "A1. Evento `account.deleted.v1`", "B1. En el momento" y "C2. Se borra lo que se pueda", because el
evento usa el mismo mecanismo que el resto del sistema (outbox del núcleo, una cola por consumidor, recepción
idempotente) sin que el núcleo conozca a cada proceso. El borrado inmediato es lo más simple y se alinea con el plazo
de QA-14. Borrar lo que se puede ubicar reduce lo retenido a dos cosas: lo que el sistema ya no puede asociar al
usuario (hechos analíticos de períodos con la clave destruida) y la evidencia de seguridad, que queda seudonimizada.

Reglas:

* **Pedido:** `DELETE /account` por la puerta de entrada, ruta local de prioridad media. Exige un inicio de sesión
  de hace 5 minutos o menos (reclamo `auth_time` del token, suposición). Un token renovado conserva el momento del
  login original; si no es reciente, responde `401 reauthentication_required` y la app vuelve a pedir la contraseña.
* **Núcleo, en una transacción de la partición del usuario:**
  * borra sus viajes, reservas, panel, avisos, invitaciones que hizo, marcadores, vinculaciones, claves de
    idempotencia, controles de entrada y sus eventos en la outbox;
  * deja una **marca de cuenta eliminada** (identificador y fecha);
  * escribe `account.deleted.v1` en la outbox.
* **Núcleo, al consumir su propio evento** (cola `core.accounts`): quita los permisos que el usuario tenía sobre
  viajes de otros usuarios de la región (índice por persona invitada) y seudonimiza al actor en el registro de
  auditoría de la región. Son operaciones idempotentes: si el proceso cae o la auditoría falla, el mensaje se
  reentrega y se repiten.
* **Marca de cuenta eliminada:** dura 30 días (suposición), más que la vida de los mensajes en las colas. Mientras
  existe:
  * un token de acceso que siga vigente recibe `401 account_deleted` y no vuelve a crear el perfil;
  * las novedades, los hechos y las aceptaciones atrasadas de ese usuario se descartan.

  La recomendación y la analítica tienen su propia marca, por el mismo motivo. Como varias instancias consumen la
  misma cola sin orden por usuario, cada escritura vuelve a revisar la marca, y un barrido periódico quita lo que un
  hecho procesado en paralelo con la baja haya dejado. La tarea diaria borra las marcas vencidas.
* **Consumidores de `account.deleted.v1`** (cola quorum propia o enlace nuevo, recepción idempotente). Cada uno borra
  lo suyo en 24 h o menos:

  | Proceso | Cola | Qué borra |
  |---|---|---|
  | Proveedor de identidad | `identity.accounts` | Credenciales, tokens de renovación y la entrada `HMAC(email) → región` del directorio global, antes que la cuenta (si el directorio no responde, se reintenta) |
  | Ingesta | `ingestion.accounts` | Vinculaciones con su configuración técnica, cursores, trabajo pendiente, avisos, resultados y novedades del usuario en la outbox; en el sistema real revoca además las autorizaciones delegadas (ADR-0021) |
  | Notificador | `notifier.push` y colas de instancia | Dispositivos de push y registro de push enviados; la instancia con la conexión SSE envía `account-deleted` y la cierra |
  | Núcleo | `core.accounts` | Permisos del usuario sobre viajes de otros usuarios de la región; seudónimo del actor en la auditoría |
  | Recomendación | `recommendation.facts` (misma cola que los hechos) | Perfil (también la marca de desactivada), feedback, sugerencias, búsquedas, control de entrada y eventos en la outbox; deja su marca de cuenta eliminada |
  | Analítica | `analytics.facts` | Los hechos del período cuya clave sigue vigente (calcula el código del usuario con esa clave). Conserva el control de recepción (identificadores de eventos, sin datos del usuario) y deja su marca, para que un hecho reentregado no se vuelva a insertar ([analytics-processing.md](../../specs/analytics-processing.md)) |

* **Lo que se borra por vencimiento, no por el evento:**

  | Dónde | Qué puede quedar | Plazo |
  |---|---|---|
  | Logs y trazas (ADR-0067) | Identificadores en los logs estructurados, incluido el `actorUserId` de un rechazo cuya auditoría falló | Retención de logs de 30 días (suposición) |
  | Backups y réplicas con recuperación a un punto en el tiempo | Copias de las bases anteriores al borrado | Retención de backups de 35 días (suposición). Si se restaura un backup, se vuelven a aplicar los `account.deleted.v1` de ese período antes de abrir el servicio |
  | Errores apartados (`travel.errors`) | Referencia al caso con el usuario | Se revisan en 24 h (`ingestion-operations.md`); los de una cuenta eliminada se cierran sin reprocesar |

* **Lo que no se puede ubicar:**
  * Los hechos analíticos de períodos cuya clave ya se destruyó (ADR-0064) quedan seudonimizados, sin forma de
    asociarlos al usuario. Siguen sujetos al riesgo de reidentificación por combinación de campos que esa ADR deja
    abierto.
  * La outbox enviada guarda el contenido 24 h (`ingestion-operations.md`), así que `account.deleted.v1` desaparece
    de la outbox del núcleo a las 24 h.
* **Auditoría:** el registro de cada región solo agrega. La única modificación permitida es reemplazar el
  identificador del actor eliminado por un seudónimo estable (`eliminada:<HMAC>`): el equipo de seguridad conserva
  la evidencia y puede seguir agrupando los intentos de ese actor. El HMAC usa una **clave propia de la auditoría**,
  que custodia el equipo de seguridad (no es la clave del HMAC del email) y se rota cada año, como en ADR-0064
  (suposición). El seudónimo sigue siendo un dato personal seudonimizado: quien tenga la clave y el `userId` puede
  asociarlo. Se retiene con el registro, 1 año.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Publish-Subscribe* (ADR-0002) | Un evento y una cola por consumidor; el núcleo no conoce a los consumidores | QA-14 |
| Patrón *Transactional Outbox* (ADR-0027) | El borrado del núcleo y el evento se confirman juntos | QA-14 |
| Patrón *Idempotent Receiver* | Cada consumidor borra sin fallar si ya no hay nada; el evento reentregado no cambia el resultado | QA-14 |
| Táctica *autenticar actores* (seguridad) | Eliminar la cuenta exige un inicio de sesión de hace 5 minutos o menos (`auth_time`) | QA-7 |
| Táctica *revocar el acceso* (seguridad) | Marca de cuenta eliminada: los tokens vigentes reciben `401` | QA-7 |
| Táctica *limitar la exposición* (seguridad) | Se borra todo lo que se puede asociar al usuario y la auditoría queda con un seudónimo | CON-3 |
| Táctica *auditar* (seguridad) | El registro de auditoría se conserva como evidencia, con el actor seudonimizado | QA-7 |
| Tácticas *reintentar* y *manejo de excepciones* (disponibilidad) | Los pasos del núcleo fuera de la partición se reintentan por reentrega; el barrido periódico corrige lo que dejó un hecho procesado en paralelo | QA-14 |

### Consequences

* Good, because agregar un proceso que guarde datos del usuario solo exige suscribirlo al evento.
* Good, because el núcleo responde enseguida y no depende de que los demás procesos estén disponibles.
* Good, because los tokens vigentes y los mensajes atrasados no recrean datos del usuario.
* Bad, because no hay vuelta atrás: un borrado por error no se puede deshacer.
* Bad, because nadie confirma que todos los procesos terminaron: se verifica con métricas por consumidor y con la
  antigüedad de su cola (ADR-0067).
* Bad, because los permisos y los registros de auditoría que el usuario dejó en **otras regiones** no se tocan. Un
  permiso queda inerte (está atado a una región y un `userId` que no se vuelven a emitir) hasta que el dueño lo
  quite, y esos registros conservan el identificador hasta su retención. Propagarlo necesitaría una operación
  nueva por el canal entre regiones (ADR-0062).
* Bad, because los hechos analíticos de años anteriores no se pueden borrar (los códigos ya no se pueden calcular).
* Bad, because la marca de cuenta eliminada conserva el identificador 30 días.
* Bad, because los logs y los backups conservan datos del usuario hasta su vencimiento, y restaurar un backup exige
  volver a aplicar las bajas.

### Confirmation

Pruebas del prototipo (`test_iteracion5_cuenta.py`):

* después del borrado, el identificador del usuario no aparece en ninguna tabla de ninguna base de la región, salvo
  en la marca;
* el login falla y el directorio ya no tiene la entrada;
* el dueño de un viaje compartido ya no ve al usuario entre sus invitados y la auditoría queda con el seudónimo;
* sin inicio de sesión reciente, el pedido da `401`;
* las novedades y los hechos atrasados se descartan, y el evento reentregado no falla;
* la marca vence a los 30 días, y el barrido quita lo que un hecho procesado en paralelo haya dejado;
* un token vigente no vuelve a crear el perfil de recomendación;
* la conexión SSE se cierra.

## Pros and Cons of the Options

### A1. Evento `account.deleted.v1`

* Good, because cada proceso borra lo suyo sin que otro lea su base (ADR-0001).
* Bad, because el borrado es eventualmente completo, no atómico entre procesos.

### A2. Orquestación desde el núcleo

* Good, because el núcleo sabe cuándo terminó todo.
* Bad, because acopla el núcleo a todos los procesos y el pedido depende de que todos respondan.

### A3. Conciliación diaria

* Good, because es simple y no necesita un evento nuevo.
* Bad, because tarda hasta un día y obliga a cada proceso a leer una lista central de cuentas eliminadas.

### B1. En el momento

* Good, because es simple y cumple el plazo de 24 h.
* Bad, because no protege de un borrado por error.

### B2. Gracia de 30 días

* Good, because el viajero puede arrepentirse.
* Bad, because los datos duran 30 días más y suma un estado de cuenta desactivada en todos los procesos.

### C1. Conservar hasta la retención

* Good, because no toca la auditoría ni la analítica.
* Bad, because retiene datos que todavía se pueden asociar al usuario.

### C2. Borrar lo que se pueda

* Good, because solo queda lo que ya no se puede asociar al usuario y la evidencia de seguridad seudonimizada.
* Bad, because exige una excepción a la regla de solo agregar de la auditoría.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 5, [iteration-5-recommendation](../01-add/iteration-5-recommendation.md) |
| Drivers | QA-14, QA-7, CON-3; pendiente de ADR-0081 y ADR-0064 |
| Contratos | [account-deleted.v1.yaml](../../specs/asyncapi/account-deleted.v1.yaml), [OpenAPI](../../specs/openapi/itinerary-api.v1.yaml), [access-audit.md](../../specs/access-audit.md) |
| Vistas afectadas | [Módulos](../02-views/module-view.md), [C&C](../02-views/cc-view.md), [secuencias](../02-views/sequence-views.md) |
| Código del prototipo | `prototype/nucleo/usuarios/eliminacion.py`, `prototype/ingesta/cuentas/`, `prototype/identidad/`, `prototype/notificador/`, `prototype/recomendacion/` |
