# Recomendación de alternativas

**Estado:** propuesta de la iteración 5 (opción A). **ADRs:** 0081, 0083 y 0084. Proceso `recomendacion` de cada región.

Reglas del proceso de recomendación: qué lo dispara, qué guarda, cómo ordena y cómo aprende. Las rutas HTTP están
en la [OpenAPI](openapi/itinerary-api.v1.yaml) (0.4.0) y los mensajes en
[suggestions-available.v1.yaml](asyncapi/suggestions-available.v1.yaml) y
[suggestion-accepted.v1.yaml](asyncapi/suggestion-accepted.v1.yaml).

## 1. Entrada y disparador

* Cola quorum `recommendation.facts`, enlazada a `booking.facts.v1` ([AsyncAPI](asyncapi/booking-facts.v1.yaml)).
* Recepción idempotente: se deduplica por `eventId`; hecho recibido, actualización del perfil y búsqueda pendiente
  se guardan en una transacción antes del ACK.
* Dispara una búsqueda un hecho con `changeType` `cancelled`, `type` de alojamiento (`hotel`) o transporte
  (`flight`, `train`, `bus`, `car`) y `source` `provider` o `email`, de un viajero con la recomendación activada.
  Un hecho `manual` (el viajero canceló o borró) solo actualiza el perfil.
* Una reserva propuesta no genera hechos (ADR-0084), así que no puede disparar ni sesgar el perfil.

## 2. Perfil resumido (por viajero, en su región)

| Dato | Para qué | Se calcula con |
|---|---|---|
| Activación (`enabled`, por defecto `true`) | Opt-out (RF-09.4, QA-14) | Preferencias del viajero |
| Preferencias explícitas (precio máximo, escalas, franja horaria, proveedores preferidos y excluidos) | Filtro antes de ordenar (QA-13) | Preferencias y ajustes del feedback |
| Afinidad por proveedor y por tipo | Característica del ranking | Contadores de `booking.facts.v1` y aceptaciones |
| Banda de precios | Precio relativo | Precios de las últimas 20 ofertas aceptadas (suposición) |
| Duración típica de estadías y anticipación típica | Características | Fechas de `booking.facts.v1` |
| Ajuste de pesos por viajero | Personalización (ADR-0083) | Feedback |

No guarda códigos de reserva, nombres, notas ni textos. Sobrevive al borrado de viajes; se borra a pedido
(`DELETE /recommendations/profile`) o con la cuenta, junto con el feedback y las sugerencias. Con la recomendación
desactivada, los hechos nuevos solo se descartan: no actualizan el perfil. Leer las preferencias o las sugerencias
no crea un perfil.

## 3. Ranking

1. **Candidatos:** ofertas de la búsqueda ([offer-search.md](offer-search.md)) que no violan ningún límite explícito.
2. **Características** de cada oferta para ese viajero: precio relativo a su banda, duración, escalas, diferencia de
   horario con la reserva cancelada, demora de llegada, mismo proveedor, afinidad con el proveedor, coincidencia de
   noches.
3. **Puntaje:** probabilidad de aceptación de un modelo logístico, `σ(w_región · x + u_viajero · x)`.
4. **Se muestran 3** (suposición). Con probabilidad 0,1, una de las tres sale de fuera de las mejores (exploración).
   Cada sugerencia guarda su posición, la versión del modelo y sus características, para entrenar.
5. `reasonCodes` explica la sugerencia con códigos (ADR-0065); la app arma el texto.

## 4. Feedback (human-in-the-loop)

| Acción | Efecto inmediato | Señal para entrenar |
|---|---|---|
| `accept` | Sugerencia aceptada; `suggestion.accepted.v1`; el resto del grupo queda descartado | Positiva |
| `reject` (con motivo opcional) | Se ajusta `u_viajero` con un paso de gradiente y se reordena lo pendiente | Negativa |
| `adjust` (preferencias) | Cambia el filtro; cada sugerencia mostrada que el ajuste excluye mueve `u_viajero` con medio paso; se reordena lo pendiente | Rechazo débil: negativa con la mitad del peso (suposición) por cada sugerencia mostrada excluida |

La respuesta de `reject` y `adjust` trae las sugerencias reordenadas (QA-13, 2 s).

## 5. Entrenamiento y versiones

* Trabajo diario por región con el feedback de la región; los datos no salen de la región (CON-3).
* Ejemplos: características de cada sugerencia mostrada; etiqueta 1 si se aceptó, 0 si se rechazó o si un ajuste la
  excluyó (este último con la mitad del peso); peso por posición para corregir el sesgo de lo que se mostraba arriba.
  Con menos de 30 ejemplos (suposición) no se entrena. Uno de cada cinco ejemplos, elegido por hash de su
  identificador (suposición), queda reservado para evaluar.
* Cada versión guarda pesos, fecha, cantidad de ejemplos y su evaluación con el feedback reservado para prueba.
* Activación: una versión que no empeora la evaluación pasa a **canario** para el 5 % de los viajeros (hash estable
  del `userId`). Con una muestra mínima de 200 sugerencias mostradas (suposición), si su tasa de aceptación es más de
  un 10 % relativo menor que la de la activa, se retira; si no, pasa a activa. Volver atrás es cambiar la versión
  activa en el registro (QA-15).
* El canario se evalúa cada 5 minutos (suposición), no solo en el trabajo diario: la medida de QA-15 (vuelta atrás en
  5 minutos) se cuenta desde que junta la muestra mínima.
* A lo sumo un canario a la vez. Si el canario no juntó la muestra cuando corre el entrenamiento, la versión nueva
  lo reemplaza: el feedback del día entra en una versión del modelo en 24 h, y llega a toda la región cuando un
  canario junta la muestra (trade-off entre QA-13 y QA-15, más lento en regiones con poco tráfico).
* Sugerencias vencidas o nunca mostradas se borran a los 30 días (suposición, ADR-0081); el feedback conserva su copia
  de las características.

## 6. Observabilidad (ADR-0067)

Métricas por región. **QA-11** se mide de punta a punta, desde `committedAt` del hecho de la cancelación (cuando
quedó aplicada en el panel) hasta que el notificador envía el push: `suggestions.available.v1` lleva
`cancellationCommittedAt` y el notificador registra `qa11_cancelacion_a_aviso_s`; la recomendación registra además el
tramo hasta las sugerencias generadas (`qa11_cancelacion_a_sugerencias_s`). Además: aciertos de la
caché y consultas por proveedor (QA-12), búsquedas pendientes y su antigüedad (QA-17), tasa de aceptación por
versión del modelo (QA-15), tiempo de respuesta del feedback (QA-13). Los logs no llevan datos personales; el
`correlationId` del hecho viaja en `suggestions.available.v1`.

## 7. Validación en el prototipo

Datos sintéticos: viajeros con preferencias ocultas, cancelaciones y feedback simulado según esas preferencias. El
modelo entrenado debe superar al orden fijo por precio en tasa de aceptación; ninguna sugerencia viola un límite
explícito; un canario que empeora se retira solo.
