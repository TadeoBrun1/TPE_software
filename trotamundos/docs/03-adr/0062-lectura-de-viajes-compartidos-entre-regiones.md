---
status: "proposed"
date: 2026-10-28
decision-makers: "Tadeo Brun"
consulted: "Tomas Lateana (revisión cruzada en el PR de la iteración 4)"
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
  Ana. La región de Juan valida ese token con las claves públicas del proveedor de identidad de la región de Ana
  (cada puerta de entrada conoce las claves públicas de todas las regiones).
* El núcleo de la región de Juan verifica el permiso, registra el acceso (ADR-0061) y responde. La respuesta no se
  guarda en la región de Ana.
* **Lista de viajes compartidos conmigo:** cuando Ana acepta una invitación, su región guarda en la partición de Ana
  solo la referencia (identificador del viaje y fecha de aceptación), sin datos del itinerario. `GET /shared/trips`
  devuelve esas referencias, y cada viaje se lee de forma remota al abrirlo. Si una referencia apunta a un permiso
  revocado, la lectura devuelve `404` y la app la quita de la lista.
* Un identificador con una región que no existe se rechaza en la puerta de entrada de Ana y se registra en el
  registro de auditoría de esa región.
* Si la región de Juan no responde, Ana recibe `503`: no hay copia de respaldo (consecuencia de no copiar datos).
* El notificador de la región de Ana no recibe avisos de viajes de otra región: la app de Ana revalida el viaje
  compartido al abrirlo. Los avisos en vivo de viajes compartidos quedan fuera de alcance, también dentro de una
  misma región.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Gateway Routing* | La puerta de entrada enruta según la región del viaje | CON-3 |
| Táctica *limitar la exposición* (seguridad) | Los datos no se copian fuera de su región | CON-3, QA-7 |
| Táctica *autenticar actores* (seguridad) | Canal entre regiones con mTLS; la región del dueño valida el token del lector | QA-7 |

### Consequences

* Good, because los datos personales del dueño no salen de su región.
* Good, because revocar es inmediato: no hay copias que borrar.
* Bad, because la lectura suma la latencia de red entre regiones. Se supone de 100 a 250 ms; con un panel típico
  (ADR-0040) sigue dentro de 800 ms, pero los usuarios lejanos quedan más cerca del límite.
* Bad, because si la región del dueño cae, el viaje compartido no se puede ver.
* Bad, because los viajes compartidos entre regiones no tienen avisos en vivo.

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
