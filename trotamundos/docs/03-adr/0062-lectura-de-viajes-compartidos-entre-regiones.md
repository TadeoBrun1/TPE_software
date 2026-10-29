---
status: "accepted"
date: 2026-10-28
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Lectura remota de viajes compartidos en la región del dueño

## Context and Problem Statement

Los datos de un usuario viven solo en su región de origen (ADR-0003) y en su partición (ADR-0042). Si Juan (región
Sudamérica) comparte un viaje con Ana (región Europa), la solicitud de Ana llega a la región de Europa, pero los
datos están en Sudamérica. Hay que decidir cómo se leen.

## Decision Drivers

* CON-3 (suposición): persistencia regional del estado autoritativo y tratamiento explícito del tránsito autorizado; falta validar el criterio normativo.
* QA-7: revocar el acceso debe tener efecto inmediato y cada acceso debe registrarse.
* QA-2: la lectura debe seguir dentro de 800 ms.

## Considered Options

* A. Lectura remota: la región de Ana reenvía la solicitud a la región de Juan
* B. Copiar el viaje compartido a la región de Ana
* C. Redirigir al cliente de Ana a la región de Juan, con un token válido solo para ese viaje

## Decision Outcome

Chosen option: "A. Lectura remota en la región del dueño", because hay una sola copia de los datos, en su región, y
la verificación del permiso y la auditoría (ADR-0061) ocurren siempre en el mismo lugar.

Reglas:

* Los identificadores de viajes e invitaciones incluyen la región del dueño (por ejemplo `sa-east:7f3c...`). La
  puerta de entrada de la región de Ana aplica primero la tabla por método y ruta que sigue. Solo las operaciones
  remotas se reenvían a la puerta de
  entrada de esa región por un canal interno entre regiones con autenticación mutua (mTLS), con el token original de
  Ana. La región de Juan acepta ese token solo porque llega por ese canal (excepción de ADR-0060) y valida su firma
  con las claves públicas del proveedor de identidad de la región de Ana (cada puerta de entrada conoce las claves
  públicas de todas las regiones). La puerta solo enruta: no conoce reglas de compartición.
* El núcleo de la región de Juan verifica el permiso, registra el acceso (ADR-0061) y responde. La respuesta no se
  guarda en la región de Ana.
* **Lista de viajes compartidos conmigo:** después de aceptar, la app de Ana llama a `POST /shared/trips` en su
  propia región, y el módulo `usuarios` del núcleo de Ana guarda en su partición solo la referencia (identificador
  del viaje y fecha de aceptación), sin datos del itinerario. La operación es idempotente: si falla, la app la
  reintenta, y como la aceptación también es idempotente, volver a aceptar y registrar deja todo igual. La
  referencia es solo un marcador: no da permiso, porque el permiso se verifica en la región de Juan al leer.
  `GET /shared/trips` devuelve las referencias y cada viaje se lee de forma remota al abrirlo. Si una lectura
  devuelve `404` (permiso quitado o viaje eliminado), la app borra la referencia con `DELETE /shared/trips/{tripId}`.
* Un identificador con una región que no existe, o una región del dueño que no responde, se rechazan en la puerta de
  entrada de Ana (`404` y `503`) y se registran en el registro de auditoría de la región de Ana (ADR-0061). No hay
  copia de respaldo del viaje (consecuencia de no copiar datos).
* El notificador de la región de Ana no recibe avisos de viajes de otra región: la app de Ana revalida el viaje
  compartido al abrirlo. Los avisos en vivo de viajes compartidos quedan fuera de alcance, también dentro de una
  misma región.

### Tabla de enrutamiento por método y ruta

La ruta completa y su método se evalúan antes de usar el prefijo. No se reenvía toda petición que contenga un tripId.

| Operación | Región que la ejecuta | Regla |
|---|---|---|
| `GET /shared/trips` | Región del lector autenticado | Lista de marcadores propios |
| `POST /shared/trips` | Región del lector autenticado | Registra un marcador propio; no concede permiso |
| `DELETE /shared/trips/{tripId}` | Región del lector autenticado | Borra su marcador aunque el tripId tenga prefijo ajeno, el viaje haya desaparecido o la región del dueño esté caída |
| `GET /shared/trips/{tripId}` | Región del dueño según prefijo | La puerta del lector reenvía por mTLS; el dueño valida principal, permiso y auditoría |
| `POST /shares/{shareId}/accept` | Región de la invitación según prefijo | Reenvío por mTLS con token original y validación completa de ADR-0060 |
| `/trips/{tripId}` y sus operaciones del dueño | Región del dueño | Un actor ajeno se rechaza y audita; mTLS no convierte al lector en dueño |
| `/panel`, `/bookings/...` y perfil | Región del usuario autenticado | No se enrutan usando tripId incluido en un cuerpo de petición |
| `GET /cards/{cardId}` sin token | Región de la tarjeta | Excepción pública de ADR-0063 |

Un prefijo desconocido en una lectura remota causa rechazo auditado. En cambio, eliminar un marcador local no
consulta ese destino: no se conserva una referencia obsoleta porque el dueño esté caído. Solo se permite un salto
entre puertas registradas; una solicitud ya reenviada con destino incorrecto se rechaza, sin bucle de reenvíos.

### Persistencia y tránsito frente a CON-3

La lectura remota devuelve datos por la puerta del lector y al dispositivo autorizado: los datos sí atraviesan
regiones. mTLS protege el canal, pero no elimina esa transferencia. Se mantiene una única copia autoritativa y no
se permite almacenamiento de la respuesta en logs, trazas o cachés de las puertas. La vista compartida responde
`Cache-Control: no-store`; la app no la persiste como caché local y la revalida al abrir. Revocar impide nuevas
lecturas, pero no puede retirar información ya vista o copiada por una persona.

CON-3 conserva su estado de suposición: esta es una propuesta de tratamiento del tránsito y de las excepciones
ya registradas, no una afirmación de cumplimiento de una normativa no seleccionada. El equipo debe revisar ese
criterio antes de aprobar. También deben considerarse el email de invitación en la región del dueño y los
seudónimos de los directorios; no se afirma que ningún dato personal sale de una región.

Pruebas: borrar en Europa un marcador de un viaje de Sudamérica sin contactar Sudamérica; repetir el borrado;
leer ese mismo viaje por mTLS; caída de Sudamérica; prefijo inválido; actor no autorizado; ningún contenido de la
respuesta en cachés ni logs.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Gateway Routing* | La puerta de entrada enruta según el prefijo de región del recurso, sin lógica de dominio | CON-3 |
| Táctica *limitar la exposición* (seguridad) | No se persiste una réplica remota; la respuesta autorizada sí transita entre regiones | CON-3, QA-7 |
| Táctica *autenticar actores* (seguridad) | Canal entre regiones con mTLS; la región del dueño valida el token del lector | QA-7 |

### Consequences

* Good, because el estado autoritativo queda en la región del dueño y no se persiste una réplica en la región del lector. La respuesta sí cruza regiones.
* Good, because quitar el permiso tiene efecto inmediato: no hay copias que borrar.
* Bad, because la lectura suma la latencia de red entre regiones. Se supone de 100 a 250 ms; con un panel típico
  (ADR-0040) sigue dentro de 800 ms, pero los usuarios lejanos quedan más cerca del límite.
* Bad, because si la región del dueño cae, el viaje compartido no se puede ver.
* Bad, because los viajes compartidos entre regiones no tienen avisos en vivo.
* Bad, because la referencia en la región del lector puede quedar desactualizada (permiso quitado) hasta que la app
  la borra; no expone datos, porque la lectura siempre se verifica en la región del dueño.

### Confirmation

Prototipo: con dos regiones simuladas como dos instancias locales, una lectura de un viaje de la otra región se
reenvía y responde, y la auditoría queda en la región del dueño. Medición de la latencia entre regiones en el
despliegue real.

## Pros and Cons of the Options

### A. Lectura remota

* Good, because no copia datos y centraliza permiso y auditoría.
* Bad, because suma latencia y depende de la disponibilidad de la otra región.

### B. Copia en la región del lector

* Good, because la lectura es local y rápida.
* Bad, because copia datos personales del dueño a otra jurisdicción (CON-3) y revocar exige borrar copias.

### C. Redirigir al cliente

* Good, because no pasa por la puerta de entrada de la región del lector.
* Bad, because el cliente tiene que conocer la dirección de otras regiones y manejar tokens por viaje.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 4, [iteration-4-security-evolvability](../01-add/iteration-4-security-evolvability.md) |
| Drivers | CON-3, QA-7, QA-2 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md), [deployment-view](../02-views/deployment-view.md), [sequence-views](../02-views/sequence-views.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0003](0003-despliegue-por-regiones-con-region-de-origen.md), [0042](0042-particion-de-la-base-por-usuario.md), [0060](0060-identidad-por-region-con-tokens.md), [0061](0061-comparticion-con-cuenta-y-auditoria.md) |
| Código del prototipo | `prototype/puerta/enrutamiento.py` y `prototype/puerta/app.py` |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #7](https://github.com/TadeoBrun1/TPE_software/pull/7),
merge `00f21b9` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
