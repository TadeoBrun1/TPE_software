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
* Un cambio compatible (un campo opcional nuevo) se hace en el mismo archivo. Un cambio incompatible crea una
  versión nueva (`<tipo>.v2`) que convive con la anterior mientras haya reservas que la usen.
* Agregar un medio de transporte nuevo (QA-9) empieza por su esquema acá; los pasos completos están en ADR-0066 y en
  el recorrido de QA-9 de la [iteración 4](../../docs/01-add/iteration-4-security-evolvability.md).
* Los detalles no van en `booking.facts.v1` (analítica) ni se traducen: el cliente los muestra con los textos de sus
  catálogos (ADR-0065).
