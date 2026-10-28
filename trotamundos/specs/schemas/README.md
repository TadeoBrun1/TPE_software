# Esquemas de detalles por tipo de reserva

Cada tipo de reserva tiene campos comunes (en la API y en los eventos) y un bloque `details` con su esquema propio
(ADR-0066). Este directorio tiene un archivo por esquema y versión: `details-<tipo>.v<n>.json` (JSON Schema
2020-12). El valor de `details.schema` es `<tipo>.v<n>`.

| Esquema | Archivo | Estado |
|---|---|---|
| `flight.v1` | [details-flight.v1.json](details-flight.v1.json) | Propuesto (iteración 4) |
| `train.v1` | [details-train.v1.json](details-train.v1.json) | Propuesto (iteración 4) |

Los esquemas de `hotel`, `car` y `bus` se agregan con el mismo formato al implementar sus adaptadores; hasta
entonces esas reservas solo tienen campos comunes.

## Reglas

* El núcleo valida `details` contra su esquema y lo guarda sin interpretarlo; un esquema que no conoce se rechaza.
* Todo cambio, incluso agregar un campo opcional, crea una versión nueva (`<tipo>.v2`), porque los esquemas tienen
  `additionalProperties: false`: un identificador designa siempre el mismo contenido. Las versiones conviven mientras
  haya reservas que las usen, y un adaptador manda la nueva recién cuando el núcleo la tiene registrada.
* El núcleo no compila los esquemas: los carga al arrancar desde los archivos registrados en su configuración.
* Un esquema no puede incluir códigos de reserva, números de billete, nombres de pasajeros ni otros datos personales:
  esos datos van en los campos comunes, que la vista compartida y la analítica filtran (ADR-0061, ADR-0064).
* No se repiten campos comunes (fechas, zonas horarias, lugares de salida y llegada).
* Agregar un medio de transporte nuevo (QA-9) empieza por su esquema acá; los pasos completos están en ADR-0066 y en
  el recorrido de QA-9 de la [iteración 4](../../docs/01-add/iteration-4-security-evolvability.md).
* Los detalles no van en `booking.facts.v1` (analítica) ni se traducen: el cliente los muestra con los textos de sus
  catálogos (ADR-0065).
