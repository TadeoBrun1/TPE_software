---
status: "accepted"
date: 2026-10-28
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Internacionalización: catálogos de textos remotos, datos neutros del backend y formato en el cliente

## Context and Problem Statement

QA-10 exige mostrar el 100 % de los textos y formatos de los idiomas soportados según la configuración del usuario,
manteniendo QA-2 y QA-3. La parte multirregión ya está resuelta (ADR-0003). Falta decidir dónde viven los textos de
la interfaz y cómo se formatean fechas, horas, zonas horarias y monedas.

## Decision Drivers

* QA-10: textos y formatos en el idioma del usuario.
* QA-2 y QA-3: el idioma no debe afectar la latencia ni la caché del panel (ADR-0040, ADR-0041).
* Modificabilidad: agregar un idioma no debería cambiar código (no es QA-9, que trata de medios de transporte).

## Considered Options

* A. Catálogos de textos remotos por idioma; el backend devuelve datos neutros y el cliente los formatea
* B. Textos ya traducidos y formateados por el servidor
* C. Textos empaquetados dentro de la app

## Decision Outcome

Chosen option: "A. Catálogos remotos y formato en el cliente", because agregar un idioma es agregar un catálogo, sin
cambiar el backend ni publicar la app, y el panel sigue siendo el mismo documento para cualquier idioma.

Reglas:

* **Textos:** cada cliente usa catálogos por idioma, versionados. La app trae los de su versión y descarga
  actualizaciones o idiomas nuevos sin publicar una versión nueva. Si falta una traducción, se muestra el idioma base.
* **Dónde se sirven:** los catálogos son archivos estáticos versionados (`/i18n/{idioma}.v{n}.json`), sin datos
  personales, publicados igual en todas las regiones y servidos por la puerta de entrada de cada región. El cliente
  los guarda con caché larga, porque una versión no cambia nunca. La app móvil abre con el catálogo que ya tiene y
  actualiza en segundo plano, así que el idioma no suma espera a QA-3; la web descarga el catálogo una vez y lo
  reutiliza.
* **Datos neutros del backend:** fechas y horas en ISO 8601 con el desfase horario del lugar de la reserva, más el
  nombre de la zona horaria IANA (`timeZone`, por ejemplo `Asia/Tokyo`), para que el cliente muestre la zona y
  resuelva bien los cambios de horario de verano; monedas con código ISO 4217 y montos numéricos; códigos en lugar de
  textos para estados y tipos. El backend no devuelve textos traducidos, salvo la tarjeta para redes (excepción de
  ADR-0063).
* **Formato en el cliente:** fechas, horas, números y monedas se formatean con las reglas estándar de cada idioma y
  país (Unicode CLDR, disponibles en las librerías estándar de web y móvil). Las horas de una reserva se muestran en
  la zona horaria del lugar, indicándola.
* **Textos que vienen de los proveedores** (nombres de hoteles, notas de una aerolínea) se muestran como llegaron; no
  se traducen.
* El idioma y el país del usuario se guardan en su perfil (`usuarios`) y la app los usa para elegir catálogo.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Táctica *diferir el enlace* (modificabilidad) | Los textos se eligen en tiempo de ejecución desde catálogos externos | QA-10 |
| Táctica *adherir a estándares* (integrabilidad) | ISO 8601, zonas IANA, ISO 4217 y Unicode CLDR | QA-10 |

### Consequences

* Good, because agregar un idioma no toca el backend ni exige publicar la app.
* Good, because el panel (ADR-0040) y su caché (ADR-0041) no dependen del idioma.
* Bad, because cada cliente (web y móvil) mantiene su formateo y sus catálogos.
* Bad, because los textos de los proveedores quedan en su idioma original.

### Confirmation

Prueba: el mismo panel se muestra en dos idiomas con fechas, horas y monedas correctas; un idioma nuevo se agrega
publicando solo su catálogo; una clave sin traducir muestra el idioma base.

## Pros and Cons of the Options

### A. Catálogos remotos y formato en el cliente

* Good, because separa el idioma del backend y de la publicación de la app.
* Bad, because duplica el formateo en los clientes.

### B. Textos armados en el servidor

* Good, because hay un solo lugar para traducir.
* Bad, because el panel y su caché pasarían a depender del idioma, y cada cambio de texto toca el núcleo.

### C. Textos dentro de la app

* Good, because es lo más simple.
* Bad, because agregar o corregir un idioma exige publicar una versión nueva de la app.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 4, [iteration-4-security-evolvability](../01-add/iteration-4-security-evolvability.md) |
| Drivers | QA-10, QA-2, QA-3 |
| Vistas afectadas | [module-view](../02-views/module-view.md) |
| Specs | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| ADRs relacionadas | [0003](0003-despliegue-por-regiones-con-region-de-origen.md), [0040](0040-modelo-de-lectura-del-panel.md), [0041](0041-cache-local-del-panel.md) |
| Código del prototipo | `prototype/nucleo/reservas/modelo.py` (datos neutros en la API); el cliente no está en el alcance |

## Estado de integración documental

Esta decisión forma parte del diseño integrado mediante [PR #7](https://github.com/TadeoBrun1/TPE_software/pull/7),
merge `00f21b9` del 2026-10-28. Los refinamientos posteriores incorporados en `main` también forman parte de
la base de cierre `00f21b9`. `accepted` registra adopción del diseño por integración, no ejecución del prototipo
ni cumplimiento medido de los QA. Las confirmaciones de implementación y los riesgos conservan su estado.
