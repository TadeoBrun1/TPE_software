# Iteración 5 — Módulo avanzado: recomendación de alternativas con human-in-the-loop (opción A)

**Responsable:** Ambos (Tadeo Brun y Tomas Lateana). Las decisiones las tomaron los dos; Tomas revisa el PR.
**Fecha:** 2026-11-22
**Estado:** en revisión (PR de la rama `iteracion5`).
**Rango de ADRs:** 0080 a 0099 (ver [CONTRIBUTING](../../CONTRIBUTING.md))

> Segunda entrega. Las decisiones se tomaron eligiendo entre alternativas planteadas para cada punto; las descartadas
> y sus razones están en cada ADR. Lo que afecta a otras iteraciones está en el [registro de impactos](impact-log.md).

---

## Paso 2 — Objetivo de la iteración

Incorporar el módulo avanzado obligatorio de la segunda entrega: un sistema que, cuando una reserva del viajero se
cancela, le sugiera alternativas de alojamiento o transporte ordenadas según su historial y sus preferencias, y que
aprenda de lo que el viajero acepta, rechaza o ajusta, sin comprometer el panel ni los datos personales.

### Elección del módulo

El enunciado pide al menos uno de dos módulos. Se eligió la **opción A** (recomendación); la comparación completa,
con ventajas, desventajas y niveles de esfuerzo de las dos opciones, está en
[ADR-0080](../03-adr/0080-eleccion-del-modulo-avanzado.md). Resumen:

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. Recomendación** | Consumidor nuevo de eventos sin tocar el núcleo; no afecta QA-2; ya prevista en ADR-0064 | Almacén nuevo de perfiles; catálogo externo de ofertas; definir "aceptar" sin comprar; reglas nuevas de retención, push y entrenamiento |
| **B. Asistente virtual** | Reusa la derivación a la agencia (ADR-0026); reprogramaciones por el flujo de novedades; modelo local en la región | Texto generado en el backend (excepción a ADR-0004 y ADR-0065); prompt injection; conversaciones con datos personales; cómputo por región |

La A cuesta más al principio (diseño y prototipo) y después escala y opera barato; la B entraba más fácil pero
cuesta más mantenerla (pruebas no deterministas, escala en picos, seguridad y costo).

### Drivers seleccionados

| ID | Descripción | Prioridad | Qué se resuelve acá |
|---|---|---|---|
| RF-09 | Sugerir alternativas de alojamiento y transporte ante una cancelación y refinarlas con el feedback | Alta | Todo el módulo |
| QA-12 | 15.000 afectados en 10 minutos: QA-11 para el 95 % y el 100 % de los límites de los proveedores respetado | H, H | Búsqueda agrupada con caché y límite por proveedor |
| QA-11 | El 95 % de las sugerencias disponible y avisada en 2 minutos | H, M | Disparador por evento, búsqueda y aviso |
| QA-13 | Reordenar en 2 s respetando límites explícitos; feedback en el modelo en 24 h | H, M | Ranking aprendido, ajuste por viajero y entrenamiento diario |
| QA-14 | 0 sugerencias tras desactivar; perfil y feedback borrados en 24 h | H, M | Almacén propio, opt-out y borrado |
| QA-16 | Una falla de la recomendación no afecta QA-2 ni QA-4; pendientes en 10 minutos | H, M | Proceso aparte y búsquedas pendientes con reintento |
| QA-15 | Versión nueva del modelo para el 5 % y vuelta atrás en 5 minutos sin tocar otros procesos | M, M | Registro de versiones y canario |

Escenarios completos en [quality-attribute-scenarios.md](../00-requirements/quality-attribute-scenarios.md),
generados con `/generador-qas` y auditados con `/test-qas`. Se agregaron a los drivers por PR de ambos.

### Restricciones que aplican

| ID | Efecto en esta iteración |
|---|---|
| CON-1 | Las ofertas alternativas se obtienen por APIs estándar de búsqueda de los proveedores |
| CON-2 | Los proveedores limitan sus consultas y pueden fallar: la búsqueda se adapta a sus límites |
| CON-3 (suposición) | Perfiles, feedback y modelo quedan en la región de origen; no se combinan datos entre regiones |
| CON-5 (suposición) | El entrenamiento corre por lotes y el proceso escala de forma reactiva, sin capacidad reservada |

### Lo que no se trata acá

| Tema | Decisión |
|---|---|
| Rutas de varios tramos | Fuera del alcance acordado de RF-09: se sugieren alternativas del mismo tipo que la reserva cancelada |
| Sugerencias sin cancelación (huecos en el viaje, a pedido) | Fuera del alcance: el disparador es la cancelación o disrupción |
| Compra o emisión de reservas | Sigue fuera del sistema: aceptar deja una reserva propuesta y el enlace al proveedor |
| Asistente virtual (opción B) | No elegido (ADR-0080); RF-06 sigue diseñado (ADR-0026) sin cambios |
| Borrado de cuenta | No está diseñado en el sistema; cuando se diseñe debe borrar el perfil (registro de impactos) |

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
| Sistema por región (estructura de procesos) | Se agrega el proceso `recomendacion` con su base |
| Núcleo / `reservas` y `viajes` | Reserva propuesta, conciliación con la reserva real, vencimiento |
| Núcleo / `mensajeria` | Consumo de `suggestion.accepted.v1`; retiro de `booking.changed.v1`; clave de colapso en `panel.changed.v1` |
| Notificador | Push y SSE de `suggestions.available.v1` con la clave de colapso de la cancelación |
| Puerta de entrada | Rutas de sugerencias y preferencias hacia el proceso de recomendación, con prioridad baja |
| Broker (topología) | Colas `recommendation.facts` y `core.suggestions`; enlaces nuevos de `notifier.push` y de las colas de instancia |

## Paso 4 — Patrones y tácticas elegidos

### 4.0 Arquitectura de referencia

No cambia: clientes ricos y aplicación de servicios con puerta de entrada (ADR-0004), desplegada por celdas
regionales (ADR-0003). El módulo se suma como un proceso más de la celda, alimentado por eventos.

### 4.1 Patrones

| Patrón | Tipo | Cómo se aplica | Drivers | ADR |
|---|---|---|---|---|
| *Publish-Subscribe* y *Competing Consumers* | Arquitectónico / de integración | La recomendación consume `booking.facts.v1` con su cola; sus instancias compiten | QA-12, QA-16 | 0081 |
| *Idempotent Receiver* y *Transactional Outbox* | De integración | Hechos deduplicados; sugerencias y aceptaciones publicadas desde una outbox | QA-11, QA-6 | 0081, 0084 |
| *Ports and Adapters* | Arquitectónico | Puerto de búsqueda de ofertas con un adaptador por proveedor | CON-1, QA-15 | 0082 |
| *Cache-Aside* y *request collapsing* | De diseño | Una consulta por clave de búsqueda, reutilizada 5 minutos | QA-12 | 0082 |
| *Circuit Breaker* | De diseño | Se deja de consultar un proveedor que falla seguido | QA-16 | 0082 |
| Recomendación en dos etapas (candidatos y ranking) | De diseño (sistemas de recomendación) | Filtro por límites explícitos y orden por puntaje aprendido | QA-13 | 0083 |
| Exploración *epsilon-greedy* (bandit) | De diseño (sistemas de recomendación) | Una de cada diez listas incluye una oferta fuera de las mejores | RF-09.3 | 0083 |
| *Canary Release* | De despliegue | Versión nueva del modelo para el 5 % de los viajeros | QA-15 | 0083 |
| *API Gateway* | Arquitectónico | La puerta enruta las rutas de sugerencias al proceso nuevo | QA-7 | 0084 |

### 4.2 Tácticas

| Atributo | Táctica | Cómo se aplica | Drivers | ADR |
|---|---|---|---|---|
| Performance | Mantener varias copias de los datos | Caché de búsquedas de 5 minutos | QA-11, QA-12 | 0082 |
| Performance | Reducir la sobrecarga de cómputo | Búsquedas equivalentes agrupadas en una sola | QA-12 | 0082 |
| Performance | Administrar las solicitudes de trabajo | Cubeta de fichas por proveedor y región | QA-12 | 0082 |
| Performance | Priorizar eventos | Rutas de sugerencias con prioridad baja ante sobrecarga | QA-2 | 0084 |
| Performance | Programar recursos | Entrenamiento por lotes en un trabajo programado | CON-5 | 0083 |
| Disponibilidad | Degradación elegante | La cancelación se muestra sin sugerencias si el módulo o el proveedor fallan | QA-16 | 0081, 0082 |
| Disponibilidad | Reintentar y manejo de excepciones | Búsquedas pendientes con espera creciente | QA-16 | 0082 |
| Usabilidad | Mantener un modelo del usuario | Perfil con preferencias y ajuste de pesos por viajero | QA-13 | 0083 |
| Usabilidad | Apoyar la iniciativa del usuario | Ajustar parámetros reordena en el momento | QA-13 | 0083 |
| Seguridad | Separar entidades | Perfiles en un proceso y una base propios | QA-14 | 0081 |
| Seguridad | Limitar la exposición | Perfil resumido; la consulta al proveedor no identifica al viajero | QA-14 | 0081, 0082 |
| Seguridad | Autorizar actores | Sugerencias solo para el dueño del viaje | QA-7 | 0084 |
| Modificabilidad | Diferir el enlace | La versión activa del modelo se elige en tiempo de ejecución | QA-15 | 0083 |
| Desplegabilidad | Escalonar los despliegues y volver atrás | Canario al 5 % y vuelta atrás automática | QA-15 | 0083 |
| Integrabilidad | Adaptar la interfaz y adherir a estándares | Oferta normalizada con ISO 4217 y zonas IANA | CON-1 | 0082 |

## Paso 5 — Instanciación

### Elementos nuevos o refinados

| Elemento | Tipo | Responsabilidades | ADR |
|---|---|---|---|
| `recomendacion` (proceso por región) | Proceso nuevo | Consume hechos, mantiene perfiles, busca y ordena alternativas, sirve la API de sugerencias, entrena el modelo y publica sus eventos | 0081 |
| `recomendacion/hechos` | Módulo | Recepción idempotente de `booking.facts.v1`, actualización del perfil y disparo de búsquedas | 0081 |
| `recomendacion/perfiles` | Módulo | Perfil resumido, preferencias explícitas, activación y borrado | 0081 |
| `recomendacion/busqueda` | Módulo | Puerto y adaptadores de búsqueda, caché, agrupación, límite por proveedor y búsquedas pendientes | 0082 |
| `recomendacion/modelo` | Módulo | Características, puntaje, exploración, ajuste por viajero, entrenamiento y registro de versiones | 0083 |
| `recomendacion/sugerencias` | Módulo | Sugerencias por viaje, feedback, outbox de `suggestions.available.v1` y `suggestion.accepted.v1` | 0084 |
| `recomendacion/api` | Módulo | Rutas de sugerencias, feedback, preferencias y perfil | 0084 |
| Núcleo / `reservas` | Refinado | Reserva propuesta, conciliación con la reserva real, sin `booking.facts.v1` para propuestas | 0084 |
| Núcleo / `viajes` | Refinado | Las propuestas no mueven fechas ni archivado; la tarea diaria vence las propuestas | 0084 |
| Núcleo / `mensajeria` | Refinado | Consume `suggestion.accepted.v1`; deja de declarar `booking.changed.v1`; `collapseKey` en las cancelaciones | 0081, 0084 |
| Notificador | Refinado | Push y SSE de `suggestions.available.v1` | 0084 |
| Puerta de entrada | Refinada | Tabla de rutas con el destino `recomendacion` y prioridad baja | 0084 |

### Reglas de interacción

1. El núcleo aplica una cancelación (novedad de la ingesta) y publica, en la misma transacción, `panel.changed.v1`
   (con `collapseKey` de la reserva) y `booking.facts.v1` (ADR-0027, ADR-0064).
2. El notificador envía el push de la cancelación. La recomendación recibe el hecho por `recommendation.facts`: si
   el viajero tiene la recomendación activada y la reserva es de alojamiento o transporte, guarda una búsqueda
   pendiente en la misma transacción que el perfil y confirma el mensaje.
3. Un trabajador toma la búsqueda: usa la caché o se suma a una búsqueda en curso con la misma clave; si no, consulta
   a los proveedores respetando sus límites (ADR-0082).
4. Ordena las ofertas con la versión del modelo que le toca al viajero (activa o canario), guarda las 3 sugerencias y
   publica `suggestions.available.v1` desde su outbox (ADR-0083).
5. El notificador envía el push con la misma clave de colapso (reemplaza al de la cancelación) y el evento SSE.
6. La app pide `GET /trips/{tripId}/suggestions`. Si el viajero rechaza o ajusta, la respuesta trae las sugerencias
   reordenadas. Si acepta, recibe el enlace a la oferta y la recomendación publica `suggestion.accepted.v1`.
7. El núcleo crea la reserva propuesta en el viaje y el panel cambia. Si después llega la reserva real por la
   ingesta, la reemplaza.
8. Cada noche, el trabajo de entrenamiento de la región entrena una versión nueva con el feedback y, si pasa la
   evaluación, la activa como canario.

### Tiempos y valores de diseño

| Valor | Origen |
|---|---|
| 2 minutos desde la cancelación en el panel hasta el aviso | QA-11 (suposición) |
| Caché de búsquedas de 5 minutos | QA-12 (suposición) |
| 3 sugerencias, exploración 0,1 | ADR-0083 (suposición) |
| Circuit breaker: 3 fallas, 1 minuto | ADR-0082 (suposición) |
| Entrenamiento diario | QA-13 (suposición) |
| Canario 5 %, vuelta atrás si cae 10 % relativo | QA-15 (suposición) |
| Sugerencias vencidas borradas a los 30 días | ADR-0081 (suposición) |
| Tolerancia de un día para conciliar la propuesta | ADR-0084 (suposición) |

### Contratos nuevos o modificados

| Contrato | Archivo en `specs/` | Cambio |
|---|---|---|
| API de itinerarios | [openapi/itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) | 0.4.0: rutas de sugerencias, feedback, preferencias y perfil; estado `proposed`, origen `suggestion` y `offerUrl` en las reservas |
| Sugerencias disponibles | [asyncapi/suggestions-available.v1.yaml](../../specs/asyncapi/suggestions-available.v1.yaml) | Nuevo: recomendación → notificador |
| Sugerencia aceptada | [asyncapi/suggestion-accepted.v1.yaml](../../specs/asyncapi/suggestion-accepted.v1.yaml) | Nuevo: recomendación → núcleo |
| Avisos del panel | [asyncapi/panel-changed.v1.yaml](../../specs/asyncapi/panel-changed.v1.yaml) | 0.3.0: `collapseKey` opcional |
| Hechos de reservas | [asyncapi/booking-facts.v1.yaml](../../specs/asyncapi/booking-facts.v1.yaml) | 0.2.0: dos consumidores (analítica y recomendación); las propuestas no lo generan |
| Cambios confirmados | [asyncapi/booking-confirmed.v1.yaml](../../specs/asyncapi/booking-confirmed.v1.yaml) | Retirado: sin consumidor, su papel lo cubre `booking.facts.v1` |
| Búsqueda de ofertas | [offer-search.md](../../specs/offer-search.md) | Nuevo: consulta y oferta normalizadas, límites, caché y fallas |
| Recomendación | [recommendation.md](../../specs/recommendation.md) | Nuevo: disparador, perfil, características, feedback, entrenamiento y versiones |
| Topología del broker | [ingestion-operations.md](../../specs/ingestion-operations.md) | Colas y enlaces nuevos |

## Paso 6 — Vistas actualizadas y ADRs creadas

| Vista | Qué cambió |
|---|---|
| [Contexto](../00-requirements/context-diagram.md) | Búsqueda de ofertas en los sistemas de terceros y sugerencias al viajero |
| [Módulos](../02-views/module-view.md) | Proceso `recomendacion` y sus módulos; reglas de dependencia |
| [Componentes y conectores](../02-views/cc-view.md) | Proceso, colas y eventos nuevos; secuencia de cancelación a sugerencia y aceptación |
| [Despliegue](../02-views/deployment-view.md) | Proceso y base de recomendación por región; trabajo de entrenamiento |
| [Modelo de dominio](../02-views/domain-model.md) | Sugerencia, perfil de preferencias, feedback, versión del modelo y reserva propuesta |

| ADR | Título | Estado |
|---|---|---|
| [0080](../03-adr/0080-eleccion-del-modulo-avanzado.md) | Módulo avanzado de la segunda entrega: sistema de recomendación (opción A) | Aceptada |
| [0081](../03-adr/0081-proceso-de-recomendacion-con-perfiles-regionales.md) | Proceso de recomendación por región, alimentado por eventos y con su propio almacén de perfiles | Aceptada |
| [0082](../03-adr/0082-busqueda-de-alternativas-con-cache-corta.md) | Búsqueda de alternativas en las APIs de los proveedores, con caché corta y búsquedas agrupadas | Aceptada |
| [0083](../03-adr/0083-ranking-aprendido-del-feedback.md) | Ranking de ofertas por características, aprendido del feedback, con un modelo regional versionado | Aceptada |
| [0084](../03-adr/0084-entrega-y-aceptacion-de-sugerencias.md) | Sugerencias por una API propia con aviso del notificador, y aceptación como reserva propuesta | Aceptada |

## Paso 7 — Análisis

### Recorridos (Scenario Walkthrough)

**QA-11, cancelación normal.** Una aerolínea cancela un vuelo. El presupuesto de 2 minutos empieza cuando la
cancelación ya está en el panel: el hecho llega a la recomendación en segundos (misma outbox), la búsqueda usa la
caché o consulta al proveedor (el tiempo de respuesta del proveedor es lo que más pesa, fuera de nuestro control,
CON-2), el ranking de unas decenas de ofertas es de milisegundos, y el aviso sale por la outbox y el notificador.
El riesgo está en proveedores lentos: con un límite de 30 s por consulta (suposición) y un reintento, entra en 2
minutos.

**QA-12, disrupción.** 15.000 cancelaciones en 10 minutos son unas 25 por segundo, que las instancias de
recomendación consumen en paralelo. Si los 50 vuelos cancelados comparten 20 rutas y 2 fechas, hay unas 40 claves
de búsqueda de transporte y unas 20 de alojamiento: unas 60 consultas a los proveedores en 5 minutos en vez de
15.000. Si un proveedor limita más que eso, las búsquedas quedan pendientes y QA-11 se incumple para esa parte, lo
que se registra como riesgo. El panel no comparte procesos ni base con la recomendación: QA-2 no se afecta.

**QA-13, rechazo y ajuste.** El rechazo actualiza el ajuste del viajero y reordena las sugerencias pendientes del
viaje en la misma solicitud (sin consultar proveedores): entra holgado en 2 s. El ajuste de parámetros filtra antes
de ordenar, así que ninguna sugerencia mostrada viola un límite explícito.

**QA-14, desactivar y borrar.** Desactivar cambia una marca en el perfil que el disparador lee en la misma
transacción que el hecho: no se generan sugerencias nuevas. El borrado elimina perfil, preferencias, feedback y
sugerencias del viajero en su base regional; las réplicas siguen el mismo borrado.

**QA-15, modelo nuevo.** La versión entrenada queda en el registro; se activa como canario para el 5 % por hash del
`userId`. Si su tasa de aceptación cae más de un 10 % relativo, el registro vuelve a la anterior: es un cambio de
dato, sin desplegar código, y no toca el núcleo, la ingesta ni el notificador.

**QA-16, proveedor o módulo caído.** Con el proveedor caído, la búsqueda queda pendiente y el circuit breaker evita
insistir; con el proceso de recomendación caído, los hechos esperan en `recommendation.facts`. En los dos casos la
cancelación y su push ya salieron del núcleo y del notificador.

### Estado de los drivers

| Driver | Estado | Riesgos o pendientes |
|---|---|---|
| RF-09 | Cumplido por diseño | Conciliación por tipo, proveedor y fechas puede no reconocer una reserva real distinta de la oferta |
| QA-11 | Cumplido por diseño | Depende del tiempo de respuesta de los proveedores (CON-2); medir en el prototipo con proveedores simulados |
| QA-12 | Parcial | Si un proveedor limita por debajo de las claves de búsqueda de una disrupción, parte de los afectados recibe las sugerencias tarde |
| QA-13 | Cumplido por diseño | La calidad del orden depende del feedback acumulado; con pocos datos manda el modelo regional |
| QA-14 | Cumplido por diseño | Falta diseñar el borrado de cuenta del sistema; la normativa concreta (CON-3) sigue sin validar |
| QA-15 | Cumplido por diseño | El canario necesita una muestra mínima para decidir; en regiones chicas puede tardar |
| QA-16 | Cumplido por diseño | Ninguno nuevo |

### Riesgos

| Riesgo | Driver | Tratamiento |
|---|---|---|
| Un proveedor no tiene API de búsqueda estándar | CON-1, RF-09 | No aporta alternativas; se anota en el contrato de búsqueda |
| Ofertas agotadas en los 5 minutos de caché | RF-09.2 | El enlace lleva al proveedor, que confirma; el rechazo por oferta agotada se cuenta aparte |
| Sesgo de lo que ya se muestra (el modelo aprende solo de lo mostrado) | QA-13 | Exploración y corrección por posición (ADR-0083) |
| Doble uso de `booking.facts.v1` | ADR-0064, QA-14 | El contrato aclara que la seudonimización es del consumidor analítico |

### Supuestos de esta iteración

Los valores de la tabla "Tiempos y valores de diseño" son suposiciones (straw man) para discutir con los
stakeholders. El límite de 30 s por consulta a un proveedor del recorrido de QA-11 también es una suposición.

### Impacto en otras iteraciones

Registrado en el [registro de impactos](impact-log.md#iteración-5--2026-11-22): `booking.facts.v1` con dos
consumidores y retiro de `booking.changed.v1` (ADR-0027, ADR-0064, ADR-0067), clave de colapso y push de
sugerencias (ADR-0046), reserva propuesta y conciliación (ADR-0044, ADR-0045, ADR-0048), rutas nuevas con prioridad
baja (ADR-0004, ADR-0047), vista compartida sin propuestas (ADR-0061), topología del broker (ADR-0028) y borrado de
cuenta pendiente.

### ¿Se sigue iterando?

El módulo queda diseñado y el prototipo lo implementa. Queda como candidato para una iteración posterior: el borrado
de cuenta del sistema completo, la parte de QA-12 con proveedores de límites bajos y, si el feedback lo justifica,
sumar una señal colaborativa al ranking (opción C de ADR-0083).

### Prototipo

| Qué parte del prototipo implementa esta iteración | Spec | ADRs |
|---|---|---|
| Proceso `recomendacion/` con hechos, perfiles, búsqueda, modelo, sugerencias y API | `recommendation.md`, `offer-search.md`, OpenAPI 0.4.0 | 0081 a 0084 |
| Reserva propuesta, conciliación y vencimiento en el núcleo | OpenAPI 0.4.0, `suggestion-accepted.v1.yaml` | 0084 |
| Push y SSE de sugerencias con clave de colapso | `suggestions-available.v1.yaml`, `panel-changed.v1.yaml` 0.3.0 | 0084 |
| Generador de datos sintéticos y evaluación del modelo | `recommendation.md` | 0083 |
| Rutas de prioridad baja en la puerta y servicios nuevos en `docker-compose.yml` | OpenAPI 0.4.0 | 0047, 0084 |

Lo que comprueban las 18 pruebas de `tests/test_iteracion5_recomendacion.py`:

| Driver | Prueba | Resultado |
|---|---|---|
| RF-09, QA-11 | Cancelación del proveedor → 3 sugerencias con push y SSE; una cancelación manual no dispara nada | Cumple (reloj simulado) |
| RF-09.2 | Aceptar crea la reserva propuesta una sola vez, no mueve el viaje, la reserva real la concilia y vence si no llega | Cumple |
| QA-12 | 50 vuelos con 30 viajeros cada uno (escala 1/10): una consulta por clave y proveedor, 0 excesos de límite, p95 ≤ 2 min | Cumple a escala reducida |
| QA-13 | Rechazar y ajustar reordenan y ninguna sugerencia viola los límites explícitos | Cumple |
| QA-14 | Desactivada no genera sugerencias ni push; borrar el perfil elimina perfil, feedback, sugerencias y búsquedas | Cumple |
| QA-15 | Un canario con aceptación menor en más de un 10 % se retira solo; vuelta atrás manual | Cumple |
| QA-16 | Proveedores caídos → búsqueda pendiente que se completa al volver; resultado parcial; recomendación detenida sin afectar el panel | Cumple |
| ADR-0083 | Con 400 cancelaciones de viajeros sintéticos, la versión nueva baja la pérdida en datos reservados, se acerca a las preferencias ocultas y supera al orden por precio | Cumple con datos sintéticos |

Hallazgos del prototipo que ajustaron el diseño: `booking.facts.v1` suma `startsAt` y `endsAt` (0.2.0); borrar el
perfil conserva la marca de desactivada; un viaje ajeno responde como uno sin sugerencias; la cubeta de fichas usa
la mitad del límite como capacidad para no superarlo en ninguna ventana de un minuto. Estado y detalle en
[prototype/README.md](../../prototype/README.md).
