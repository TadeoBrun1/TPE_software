---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (revisión cruzada pendiente en el PR de la iteración 4)"
informed: ""
---

# Lectura remota de viajes compartidos en la región del dueño

## Context and Problem Statement

Los datos de un usuario viven solo en su región de origen (ADR-0003) y en su partición (ADR-0042). Si Juan (región
Sudamérica) comparte un viaje con Ana (región Europa), la solicitud de Ana llega a la región de Europa, pero los
datos están en Sudamérica. Hay que decidir cómo se leen.

## Decision Drivers

* CON-3 (suposición): los datos personales de Juan no deben copiarse a otra jurisdicción.
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
  puerta de entrada de la región de Ana ve que el recurso es de otra región y reenvía la solicitud a la puerta de
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

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Gateway Routing* | La puerta de entrada enruta según el prefijo de región del recurso, sin lógica de dominio | CON-3 |
| Táctica *limitar la exposición* (seguridad) | Los datos no se copian fuera de su región | CON-3, QA-7 |
| Táctica *autenticar actores* (seguridad) | Canal entre regiones con mTLS; la región del dueño valida el token del lector | QA-7 |

### Consequences

* Good, because los datos personales del dueño no salen de su región.
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
| Código del prototipo | `prototype/` |
