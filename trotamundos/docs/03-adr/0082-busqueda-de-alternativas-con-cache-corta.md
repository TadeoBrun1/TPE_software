---
status: "accepted"
date: 2026-11-22
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Búsqueda de alternativas en las APIs de los proveedores, con caché corta y búsquedas agrupadas

## Context and Problem Statement

Para sugerir una alternativa a una reserva cancelada hace falta saber qué ofertas existen: hoteles con
disponibilidad en la ciudad y las fechas, o vuelos y trenes entre los mismos lugares. El sistema hasta ahora solo
leía reservas ya hechas. En una disrupción (QA-12) miles de viajeros pierden el mismo vuelo a la vez, y los
proveedores limitan cuántas consultas aceptan (CON-2). ¿De dónde salen las ofertas y cómo se consultan sin
saturar a los proveedores ni atrasar las sugerencias?

## Decision Drivers

* QA-11: sugerencias avisadas en 2 minutos.
* QA-12: 15.000 afectados en 10 minutos respetando el 100 % de los límites de consulta de cada proveedor.
* QA-17: si un proveedor no responde, la búsqueda queda pendiente y se reintenta.
* CON-1 (APIs estándar) y CON-2 (sistemas externos que no podemos modificar).
* ADR-0023: puertos comunes y adaptadores por proveedor.

## Considered Options

* A. Consultar las APIs de búsqueda de los proveedores al momento de cada cancelación
* B. Mantener un catálogo propio copiado periódicamente
* C. Consultar las APIs de búsqueda con una caché corta y agrupando búsquedas equivalentes

## Decision Outcome

Chosen option: "C. Búsqueda con caché corta y búsquedas agrupadas", because en una disrupción las búsquedas de los
afectados son casi todas la misma (misma ruta y fecha, o misma ciudad y noches), así que una sola consulta al
proveedor sirve a todos, respeta sus límites (QA-12) y mantiene precios y disponibilidad razonablemente frescos,
cosa que un catálogo copiado no garantiza.

Reglas:

* **Puerto de búsqueda y adaptadores por proveedor** (*Ports and Adapters*, como ADR-0023), dentro del proceso de
  recomendación. El puerto recibe una consulta normalizada y devuelve ofertas normalizadas según
  [offer-search.md](../../specs/offer-search.md): tipo, proveedor, precio y moneda (ISO 4217), horarios con zona
  IANA, origen y destino o ciudad, escalas, cadena o aerolínea, enlace a la oferta y vencimiento. La ingesta no
  cambia: sus adaptadores siguen leyendo reservas.
* **Clave de búsqueda:** tipo, origen, destino o ciudad, fecha (y noches para alojamiento). No lleva datos del
  viajero: la consulta al proveedor no dice para quién es (táctica *limitar la exposición*).
* **Búsquedas agrupadas:** si una búsqueda con la misma clave está en curso, las demás esperan su resultado en vez
  de consultar otra vez (*request collapsing*).
* **Caché corta:** el resultado de una clave se reutiliza durante 5 minutos (suposición, por analogía con la
  vigencia habitual de una tarifa consultada en un buscador de viajes), o menos si la oferta trae un vencimiento
  menor. Se descarta antes si el proveedor responde que
  una oferta ya no está disponible.
* **Límite por proveedor:** cada adaptador respeta el límite de consultas publicado por el proveedor con una cubeta
  de fichas por región, con capacidad de la mitad del límite por minuto y recarga de la otra mitad por minuto, así
  ninguna ventana de un minuto lo supera. Si no quedan fichas, la búsqueda queda pendiente y se reintenta, en vez de
  exceder el límite.
* **Estado compartido de la región:** la caché, las búsquedas en curso (para agruparlas) y las cubetas de fichas
  viven en una **caché compartida en memoria por región** (tipo Redis, con réplica en otra zona; suposición), no en
  cada instancia. Así hay una sola caché, una sola consulta por clave y un solo límite por proveedor aunque haya *n*
  instancias. La búsqueda en curso es una entrada con vencimiento por clave; las fichas se descuentan con una
  operación atómica. Si la caché compartida no responde, no se consulta a ningún proveedor: las búsquedas quedan
  pendientes y se reintentan (preferimos atrasar sugerencias antes que exceder un límite).
* **Fallas:** se clasifican como en ADR-0023 (temporal, cuota, autorización, datos). Una falla temporal o de cuota
  deja la búsqueda pendiente con reintento y espera creciente; tras 3 fallas seguidas de un proveedor, se deja de
  consultarlo durante 1 minuto (*Circuit Breaker*; valores supuestos). La cancelación ya está en el panel: solo se
  atrasan las sugerencias (QA-17).
* **Varios proveedores:** se consulta a todos los adaptadores del tipo de reserva; si uno falla (o no tiene fichas) y
  otro responde, se sugieren las ofertas disponibles y se anota que la búsqueda fue parcial. Un resultado parcial
  no se guarda en la caché. La búsqueda sigue pendiente y se reintenta hasta completarse o hasta que el viajero
  acepte una alternativa. Se conservan IDs y feedback de las ofertas existentes; se agregan las nuevas y se reordena.
  Solo se avisa nuevamente si cambia la lista visible o se completa la búsqueda, con la misma clave de colapso.

Patrones y tácticas que aplica:

| Patrón o táctica | Cómo se aplica | Driver |
|---|---|---|
| Patrón *Ports and Adapters* | Un puerto de búsqueda y un adaptador por proveedor | CON-1, CON-2 |
| Táctica *mantener varias copias de los datos* (performance) | Caché de 5 minutos por clave de búsqueda, compartida por las instancias de la región | QA-11, QA-12 |
| Táctica *reducir la sobrecarga de cómputo* (performance), patrón *request collapsing* | Una consulta al proveedor por clave aunque haya miles de afectados | QA-12 |
| Táctica *administrar las solicitudes de trabajo* (performance) | Cubeta de fichas por proveedor y región | QA-12, CON-2 |
| Tácticas *reintentar* y *manejo de excepciones* (disponibilidad), patrón *Circuit Breaker* | Búsquedas pendientes con reintento; se deja de consultar a un proveedor que falla | QA-17 |
| Tácticas *adaptar la interfaz* y *adherir a estándares* (integrabilidad) | Contrato de oferta normalizado con ISO 4217 y zonas IANA | CON-1, QA-10 |
| Táctica *validar la entrada* (seguridad) | El adaptador descarta una oferta cuyo `offerUrl` no es https o no es de un dominio permitido del proveedor | QA-7 |

### Consequences

* Good, because en una disrupción el número de consultas crece con las rutas afectadas, no con los viajeros.
* Good, because un proveedor nuevo es un adaptador más del puerto.
* Bad, because una oferta mostrada puede haberse agotado en esos 5 minutos: el enlace lleva al proveedor, que es
  quien confirma disponibilidad y precio.
* Bad, because cada proveedor necesita un adaptador de búsqueda además del de reservas, y no todos ofrecen una API de
  búsqueda estándar (CON-1): los que no la tengan no aportan alternativas.

### Confirmation

Pruebas del prototipo: muchas cancelaciones del mismo vuelo generan una sola consulta al proveedor; un proveedor
caído deja la búsqueda pendiente y al volver se completan las sugerencias; el límite de consultas no se excede.

## Pros and Cons of the Options

### A. Consultar en cada cancelación

* Good, because los precios y la disponibilidad están al día.
* Bad, because en una disrupción multiplica las consultas por cada viajero y supera los límites de los proveedores.

### B. Catálogo propio copiado

* Good, because la respuesta no depende de que el proveedor esté disponible en ese momento.
* Bad, because precios y disponibilidad quedan viejos justo en una disrupción, cuando más cambian.
* Bad, because copiar el catálogo completo de cada proveedor es mucho más tráfico y almacenamiento que lo que se
  sugiere.

### C. Búsqueda con caché corta y búsquedas agrupadas

* Good, because combina frescura con un número de consultas acotado.
* Bad, because suma una caché y su vencimiento que hay que observar (aciertos, vencimientos, búsquedas pendientes).

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 5, [iteration-5-recommendation](../01-add/iteration-5-recommendation.md) |
| Drivers | QA-11, QA-12, QA-17, CON-1, CON-2 |
| Contratos | [offer-search.md](../../specs/offer-search.md) |
| Vistas afectadas | [C&C](../02-views/cc-view.md), [contexto](../00-requirements/context-diagram.md) |
| Código del prototipo | `prototype/recomendacion/busqueda/` |
