# Búsqueda de ofertas alternativas

**Estado:** propuesta de la iteración 5 (opción A). **ADR:** 0082. Lo usa solo el proceso de recomendación.

Contrato del puerto de búsqueda que el proceso de recomendación usa para encontrar alternativas a una reserva
cancelada. Cada proveedor tiene un adaptador que traduce su API estándar de búsqueda (CON-1) a este contrato. La
ingesta no cambia: sus adaptadores siguen leyendo reservas.

## Consulta normalizada

| Campo | Alojamiento | Transporte | Notas |
|---|---|---|---|
| `type` | `hotel` | `flight`, `train`, `bus`, `car` | Código abierto de tipo (ADR-0066); se busca el mismo tipo que la reserva cancelada |
| `location` | Ciudad | Origen (aeropuerto, estación o ciudad) | Nunca una dirección |
| `arrivalLocation` | — | Destino | |
| `date` | Fecha de entrada | Fecha de salida | Fecha local del lugar |
| `nights` | Noches de la reserva cancelada | — | |
| `currency` | Moneda preferida para precios | Ídem | ISO 4217 |

La **clave de búsqueda** es la concatenación de `type`, `location`, `arrivalLocation`, `date` y `nights`. La consulta
no lleva datos del viajero: el proveedor no sabe para quién es (táctica *limitar la exposición*).

## Oferta normalizada

| Campo | Obligatorio | Formato |
|---|---|---|
| `offerId` | Sí | Identificador del proveedor para la oferta |
| `type`, `provider` | Sí | Tipo de reserva y nombre del proveedor (aerolínea, cadena) |
| `startsAt`, `endsAt` | `startsAt` sí | ISO 8601 con el desfase del lugar, más `timeZone` y `arrivalTimeZone` IANA (ADR-0065) |
| `location`, `arrivalLocation` | `location` sí | Como en la consulta |
| `stops` | Transporte | Entero ≥ 0 |
| `price` | Sí | `amount` numérico y `currency` ISO 4217 |
| `offerUrl` | Sí | Enlace a la oferta en el proveedor; es lo que se muestra al aceptar |
| `expiresAt` | No | Hasta cuándo el proveedor garantiza la oferta; acota la caché |

Un adaptador no inventa datos que el proveedor no da (igual que ADR-0023): un campo ausente queda ausente.

`offerUrl` viene de un tercero y la app lo abre: el adaptador solo acepta `https` y un dominio de la lista permitida
de ese proveedor (configuración del adaptador). Una oferta con otro enlace se descarta como error de datos.

## Caché, agrupación y límites

* La caché, las búsquedas en curso y las cubetas de fichas están en una caché compartida en memoria por región
  (ADR-0082), no en cada instancia del proceso de recomendación. Si no responde, no se consulta: las búsquedas
  quedan pendientes.
* Una búsqueda en curso con la misma clave se comparte: las demás esperan su resultado (*request collapsing*).
* El resultado se reutiliza 5 minutos (suposición) o hasta el `expiresAt` más cercano, lo que pase primero.
* Cada adaptador tiene una cubeta de fichas por región dimensionada con el límite publicado por el proveedor:
  capacidad de la mitad del límite por minuto y recarga de la otra mitad por minuto, para que ninguna ventana de un
  minuto lo supere (una cubeta llena del tamaño del límite más su recarga permitiría casi el doble). Un proveedor sin
  fichas no se consulta: si otro proveedor del tipo respondió, el resultado es parcial; si ninguno, la búsqueda queda
  pendiente y se reintenta. Nunca se excede el límite (QA-12).
* Un resultado parcial no se guarda en la caché, para que la próxima búsqueda de esa clave consulte al que faltó.
* Tiempo máximo de una consulta: 30 s (suposición).

## Fallas

| Clase (ADR-0023) | Ejemplo | Tratamiento |
|---|---|---|
| Temporal | Error 5xx, tiempo agotado | Búsqueda pendiente; reintento con espera creciente |
| Cuota | 429 con `Retry-After` | Búsqueda pendiente hasta la hora indicada |
| Autorización | Credencial del adaptador rechazada | Alerta a operación; ese proveedor no aporta ofertas hasta corregirlo |
| Datos | Oferta sin precio o sin enlace | Se descarta esa oferta y se cuenta en métricas |

Tras 3 fallas temporales seguidas de un proveedor, no se lo consulta durante 1 minuto (*Circuit Breaker*,
suposición). Si un proveedor falla y otro responde, la búsqueda se completa como **parcial**.

## Validación en el prototipo

Muchas cancelaciones con la misma clave generan una sola consulta; un proveedor caído deja la búsqueda pendiente y al
volver se completa; la cubeta no se excede; un proveedor que falla y otro que responde dan una búsqueda parcial.
