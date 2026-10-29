# Iteración 3 — Consulta, latencia, disponibilidad y escala

**Responsable:** Tadeo Brun (integrante B)
**Fecha:** 2026-10-28
**Estado:** diseño integrado en `main` mediante PR #6; ADRs aceptadas documentalmente.
Validación de implementación y riesgos pendientes según [cierre de primera entrega](../04-evaluation/first-delivery-review.md).
**Rango de ADRs:** 0040 a 0059 (ver [CONTRIBUTING](../../CONTRIBUTING.md))

> Las decisiones se tomaron eligiendo entre alternativas planteadas para cada punto; las descartadas y sus razones
> están en cada ADR. Lo que afecta a otras iteraciones está en el [registro de impactos](impact-log.md).

---

## Paso 2 — Objetivo de la iteración

Diseñar cómo el viajero consulta y gestiona sus viajes con la latencia exigida en web y móvil, cómo el sistema
sigue atendiendo ante fallas y picos de tráfico, y cómo el núcleo aplica las novedades que entrega la ingesta y
mantiene el ciclo de vida de los viajes.

### Drivers seleccionados

| ID | Descripción | Prioridad | Qué se resuelve acá |
|---|---|---|---|
| QA-2 | El 95 % de las solicitudes del panel en 800 ms o menos | H, M | Camino de lectura del panel |
| QA-3 | Primer contenido móvil en menos de 1,4 s (4G, sesión iniciada) | M, M | Comportamiento de la app al abrir |
| QA-4 | Detección en 30 s, redirección en 60 s, máximo 5 min/mes | H, H | Detección y conmutación del núcleo y de la base dentro de la región |
| QA-5 | 2 M usuarios activos, pico de 5 veces, cumpliendo QA-1 y QA-2 | H, H | Partición de la base, escalado y sobrecarga |
| RF-04 | Agregar, editar y eliminar reservas manualmente | Media | Conflictos entre cambios manuales y novedades |
| RF-05 | Agrupar por viaje y archivar al completarse | Alta | Asignación a viajes, criterio de completo, archivado y reactivación |
| QA-1 (etapas del núcleo y del cliente) | 100 s de los 300 s asignados por la iteración 2 | H, H | Aplicación de novedades y aviso al cliente |
| QA-6 (lado consumidor) | El 99,9 % de los mensajes válidos sin pérdida ni duplicación | H, M | Aplicación de novedades en el núcleo |

### Restricciones que aplican

| ID | Efecto en esta iteración |
|---|---|
| CON-3 (suposición) | Los datos no salen de la región de origen: la recuperación es dentro de la región |
| CON-4 | La app móvil nativa puede guardar el panel en el dispositivo |
| CON-5 (suposición, agregada en esta iteración) | Startup con recursos limitados: no se paga capacidad ociosa sin evidencia de uso |

### Lo que no se trata acá

| Tema | Decisión |
|---|---|
| QA-1 a escala con avisos perdidos (conflicto abierto de la iteración 2) | **Riesgo aceptado.** Se registra en el Paso 7; su mitigación queda para una iteración 5 si hay tiempo. Confirmado por ambos integrantes (2026-10-28) |
| Falla de una región completa | Sigue siendo un riesgo aceptado (ADR-0003); esta iteración no diseña recuperación entre regiones |
| Autenticación del viajero y compartición | Iteración 4 |

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
| Núcleo | Camino de lectura del panel, aplicación de novedades, gestión manual y ciclo de vida |
| Base operativa | Organización dentro de la región, detección de fallas y conmutación |
| Clientes web y móvil | Comportamiento al abrir y ante cambios |
| Puerta de entrada | Límites y prioridades ante sobrecarga |

## Paso 4 — Patrones y tácticas elegidos

### 4.1 Patrones

| Patrón | Cómo se aplica | Drivers | ADR |
|---|---|---|---|
| CQRS (un solo almacén) y *Materialized View* | Documento `panel_por_usuario`, actualizado en la misma transacción que el cambio | QA-2, QA-5, RF-04 | [0040](../03-adr/0040-modelo-de-lectura-del-panel.md) |
| Caché del cliente con validación condicional (HTTP `ETag`, *stale-while-revalidate*) | La app muestra el panel guardado y lo revalida con su versión | QA-3 | [0041](../03-adr/0041-cache-local-del-panel.md) |
| *Publish-Subscribe* (ADR-0002) y *Transactional Outbox* (ADR-0027) | El núcleo publica `panel.changed.v1`; el notificador se suscribe con una cola por instancia | QA-1, QA-5 | [0046](../03-adr/0046-notificador-de-cambios-del-panel.md) |
| *Competing Consumers* | Cola compartida para los push, para enviar cada uno una sola vez | QA-1 | [0046](../03-adr/0046-notificador-de-cambios-del-panel.md) |
| *Sharding* | Particiones lógicas por hash de usuario en varios nodos | QA-4, QA-5 | [0042](../03-adr/0042-particion-de-la-base-por-usuario.md) |
| *Active redundancy* (*hot spare*) | Réplica sincrónica de cada nodo de la base, en otra zona | QA-4 | [0042](../03-adr/0042-particion-de-la-base-por-usuario.md) |
| *Rate Limiting* y *Load Shedding* | Límite por cliente y rechazo de operaciones de menor prioridad | QA-2, QA-5 | [0047](../03-adr/0047-priorizacion-y-degradacion-ante-sobrecarga.md) |
| *Idempotent Receiver* (iteración 2) y marca de borrado (*tombstone*) | Aplicación de novedades sin duplicar ni recrear reservas borradas | QA-6, RF-04 | [0044](../03-adr/0044-novedades-y-cambios-manuales.md) |
| Tarea programada por lotes | Archivado diario por partición | RF-05 | [0045](../03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md) |

### 4.2 Tácticas

Nombres según Bass, Clements y Kazman (4ta edición).

| Atributo | Táctica | Cómo se aplica | Drivers | ADR |
|---|---|---|---|---|
| Performance | Mantener múltiples copias de los datos | Documento del panel en la base; panel guardado en la app | QA-2, QA-3 | [0040](../03-adr/0040-modelo-de-lectura-del-panel.md), [0041](../03-adr/0041-cache-local-del-panel.md) |
| Performance | Reducir la sobrecarga computacional | El panel no se arma en cada lectura, solo tiene viajes activos y responde `304` si no cambió | QA-2, QA-5 | [0040](../03-adr/0040-modelo-de-lectura-del-panel.md), [0041](../03-adr/0041-cache-local-del-panel.md), [0045](../03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md) |
| Performance | Mantener múltiples copias del cómputo | Instancias sin estado del núcleo y del notificador | QA-5, QA-2 | [0043](../03-adr/0043-escalado-solo-reactivo.md) |
| Performance | Aumentar recursos | Escalado automático por métrica de cada proceso; nodos nuevos para la base | QA-5 | [0043](../03-adr/0043-escalado-solo-reactivo.md), [0042](../03-adr/0042-particion-de-la-base-por-usuario.md), [0046](../03-adr/0046-notificador-de-cambios-del-panel.md) |
| Performance | Administrar las solicitudes de trabajo | Límite por cliente en la puerta de entrada (`429`) | QA-5 | [0047](../03-adr/0047-priorizacion-y-degradacion-ante-sobrecarga.md) |
| Performance | Priorizar eventos | El panel se atiende antes que las operaciones de prioridad media y baja | QA-2 | [0047](../03-adr/0047-priorizacion-y-degradacion-ante-sobrecarga.md) |
| Performance | Limitar la respuesta a eventos | Se baja o pausa el consumo de novedades en la sobrecarga | QA-5 | [0047](../03-adr/0047-priorizacion-y-degradacion-ante-sobrecarga.md) |
| Performance | Programar recursos | Archivado en el horario de menor carga | QA-5 | [0045](../03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md) |
| Disponibilidad | *Ping/echo* y *monitor* | La puerta de entrada consulta a las instancias del núcleo; el monitor de base consulta a cada primaria | QA-4 | [0042](../03-adr/0042-particion-de-la-base-por-usuario.md) |
| Disponibilidad | *Redundant spare* | Réplica sincrónica de cada nodo de la base; varias instancias del núcleo y del notificador en al menos dos zonas (iteración 1) | QA-4 | [0042](../03-adr/0042-particion-de-la-base-por-usuario.md), [0003](../03-adr/0003-despliegue-por-regiones-con-region-de-origen.md) |
| Disponibilidad | *Reconfiguration* | El ruteo de particiones se actualiza tras promover una réplica | QA-4 | [0042](../03-adr/0042-particion-de-la-base-por-usuario.md) |
| Disponibilidad | Degradación elegante | Sin notificador la app usa su caché; en la sobrecarga se rechaza lo secundario | QA-4 | [0046](../03-adr/0046-notificador-de-cambios-del-panel.md), [0047](../03-adr/0047-priorizacion-y-degradacion-ante-sobrecarga.md) |
| Seguridad | Limitar la exposición | Eliminación de viajes archivados al año; avisos sin datos de reservas | CON-3 | [0045](../03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md), [0046](../03-adr/0046-notificador-de-cambios-del-panel.md) |

## Paso 5 — Instanciación

### Elementos nuevos o refinados

| Elemento | Tipo | Responsabilidades |
|---|---|---|
| Núcleo / `panel` (proyector) | Módulo del núcleo | Único escritor de `panel_por_usuario`; regenera el panel desde las tablas; expone la versión |
| Núcleo / `reservas` | Módulo del núcleo (refinado) | Aplica novedades y cambios manuales con dueño por campo; marcas de borrado; avisos al usuario |
| Núcleo / `viajes` | Módulo del núcleo (refinado) | Asigna reservas a viajes por fechas; reservas sin fechas a "sin asignar"; tarea diaria de archivado y eliminación; reactivación |
| Núcleo / ruteo de particiones | Módulo del núcleo | Calcula la partición de cada usuario y conoce el nodo primario; lo usan la API, el consumidor de novedades y la tarea diaria |
| Notificador | Proceso nuevo, por región | Consume `panel.changed.v1` con una cola por instancia; mantiene conexiones SSE; envía push desde una cola compartida |
| Base operativa | Particiones lógicas en nodos con primaria y réplica sincrónica | Guarda todo lo de un usuario en su partición |
| Monitor de base | Componente de operación, tres instancias (zonas A, B y C) | *Ping/echo* a las primarias, promoción de réplicas por acuerdo de dos de tres |
| Puerta de entrada | Refinada | Límite por cliente y clasificación por prioridad; *ping/echo* a las instancias del núcleo; enruta `/panel/events` al notificador |
| App móvil y web | Refinadas | Caché local del panel con revalidación por versión; conexión SSE con la app abierta |

### Reglas de interacción

| Regla | Justificación |
|---|---|
| Toda escritura sobre viajes o reservas actualiza en la misma transacción las tablas, el panel y la outbox (`booking.changed.v1` o `trip.changed.v1`, y `panel.changed.v1`) | Coherencia del panel y publicación garantizada (ADR-0040, ADR-0027, ADR-0046) |
| Todo lo de un usuario vive en su partición; ninguna transacción cruza particiones | La transacción sigue siendo local (ADR-0042) |
| Los avisos al cliente llevan solo la versión del panel; los datos y los textos de aviso se piden por la API | No exponer datos de reservas fuera de la API autenticada (ADR-0046) |
| Una novedad cambia los campos del proveedor y nunca los del usuario; no recrea reservas borradas | Dueño por campo y marca de borrado (ADR-0044) |
| `429` cuando un cliente supera su límite; `503` con `Retry-After` cuando hay sobrecarga y la operación es de prioridad media o baja | Proteger el panel (ADR-0047) |
| El consumo de novedades no escala con las instancias del núcleo: 8 shards con un consumidor activo cada uno | Orden por usuario de la iteración 2 (ADR-0028) |

### Tiempos de detección

| Qué se vigila | Quién | Frecuencia | Falla declarada | Acción |
|---|---|---|---|---|
| Instancias del núcleo y del notificador | Puerta de entrada | Cada 5 s | 3 sin respuesta (15 s) | Deja de enviarles tráfico |
| Primarias de la base | Monitor de base | Cada 5 s | 6 sin respuesta (30 s) | Promueve la réplica en 30 s más (total 60 s) |

Son valores iniciales de diseño, ajustables con la operación, elegidos para cumplir los 30 s y 60 s de QA-4.

### Contratos nuevos o modificados

| Contrato | Archivo | Cambio |
|---|---|---|
| API de itinerarios | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) | Nuevo; reemplaza al ejemplo de formato. Panel con `ETag`, reservas sin asignar y avisos; SSE; viajes archivados, archivar y reactivar; gestión manual con `If-Match`; `429` y `503` |
| Avisos de cambio del panel | [panel-changed.v1.yaml](../../specs/asyncapi/panel-changed.v1.yaml) | Nuevo: versión del panel, motivo y relevancia; lo consume solo el notificador |
| Cambios confirmados de viajes | [trip-changed.v1.yaml](../../specs/asyncapi/trip-changed.v1.yaml) | Nuevo: creado, actualizado, archivado, reactivado, eliminado; lo consume la analítica (iteración 4) |
| Cambios confirmados de reservas | [booking-confirmed.v1.yaml](../../specs/asyncapi/booking-confirmed.v1.yaml) | Sin cambios |
| Novedades de reservas | [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml) | Sin cambios; el núcleo lo consume con las reglas de ADR-0044 y ADR-0048 |

## Paso 6 — Vistas actualizadas y ADRs creadas

| Vista | Qué cambió |
|---|---|
| [Vista C&C](../02-views/cc-view.md) | Notificador, monitor de base, conexión SSE, particiones, evento `panel.changed.v1` |
| [Vista de despliegue](../02-views/deployment-view.md) | Nodos de la base con primaria y réplica en zonas distintas; monitor en tres zonas; notificador; escalado |
| [Vista de módulos](../02-views/module-view.md) | Módulos `panel` y ruteo de particiones; módulos del notificador; regla de único escritor |
| [Vistas de secuencia](../02-views/sequence-views.md) | SEQ-3 (consulta del panel y aviso), SEQ-4 (falla de un nodo de la base), SEQ-6 (novedad que pisa una edición) |
| [Modelo de dominio](../02-views/domain-model.md) | Campos editados, marca de borrado, avisos, reservas sin asignar, reactivación |
| [Interfaces](../02-views/interfaces.md) | API de itinerarios v1, `panel.changed.v1`, `trip.changed.v1` |

| ADR | Título | Estado |
|---|---|---|
| [0040](../03-adr/0040-modelo-de-lectura-del-panel.md) | Modelo de lectura del panel por usuario, actualizado en la misma transacción | Aceptada documentalmente |
| [0041](../03-adr/0041-cache-local-del-panel.md) | Caché local del panel en la app, revalidada por versión | Aceptada documentalmente |
| [0042](../03-adr/0042-particion-de-la-base-por-usuario.md) | Partición de la base por usuario en varios nodos con réplica sincrónica | Aceptada documentalmente |
| [0043](../03-adr/0043-escalado-solo-reactivo.md) | Escalado automático solo reactivo, con capacidad mínima de disponibilidad | Aceptada documentalmente |
| [0044](../03-adr/0044-novedades-y-cambios-manuales.md) | Conflictos entre novedades y cambios manuales: dueño por campo y marca de borrado | Aceptada documentalmente |
| [0045](../03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md) | Archivado diario, reactivación y eliminación al año | Aceptada documentalmente |
| [0046](../03-adr/0046-notificador-de-cambios-del-panel.md) | Notificador separado con evento propio y cola por instancia | Aceptada documentalmente |
| [0047](../03-adr/0047-priorizacion-y-degradacion-ante-sobrecarga.md) | Priorización y degradación ante sobrecarga | Aceptada documentalmente |
| [0048](../03-adr/0048-asignacion-de-reservas-a-viajes.md) | Asignación automática de reservas a viajes por fechas | Aceptada documentalmente |

## Paso 7 — Análisis

Recorrido de escenarios sobre el diseño (*Scenario Walkthrough*). Son resultados esperados por diseño, no
mediciones: las cifras de carga son suposiciones que el prototipo y las pruebas de carga deben confirmar.

### Recorridos

| Escenario | Recorrido | Resultado esperado | Límite o riesgo |
|---|---|---|---|
| QA-2: el viajero abre el panel en la web | Entrada global → puerta de entrada → núcleo → lectura por clave en su partición → respuesta comprimida | Una lectura por clave, sin uniones; con un panel típico (hasta 20 KB) el tiempo queda dominado por la red | El costo crece con el tamaño del documento: se acota a 15 viajes completos (ADR-0040). Usuarios lejanos de su región suman latencia de red (QA-10) |
| QA-3: abre la app con sesión iniciada | Con caché: muestra el panel guardado y revalida en paralelo. Sin caché (instalación, dispositivo nuevo, caché borrada): espera `GET /panel` comprimido | Con caché, primer contenido sin esperar la red | Las aperturas sin caché cuentan dentro del 95 %; se supone que son menos del 5 % (cobertura pendiente) |
| QA-4: cae una instancia del núcleo | La puerta de entrada deja de enviarle tráfico tras 15 s sin respuesta | Solo se pierden las solicitudes en curso; los clientes reintentan | — |
| QA-4: cae la primaria de un nodo de la base | El monitor lo detecta en 30 s y, con acuerdo de dos de tres, promueve la réplica en 60 s | Los usuarios de **ese nodo** quedan sin lecturas ni escrituras durante la conmutación, sin pérdida de datos; los demás nodos no se afectan | Con pocos nodos al principio, cada nodo tiene una fracción grande de los usuarios |
| QA-4: cae una zona entera, o solo una réplica | Las réplicas de la otra zona se promueven (o la primaria sigue sola); se suspende la confirmación sincrónica y se reconstruye la réplica (en la zona C si cayó una zona) | Servicio restablecido en 60 s; se siguen aceptando escrituras | Durabilidad reducida hasta terminar la copia: una segunda falla en esa ventana pierde datos |
| QA-5: pico de 5 veces | El escalado arranca al 60 % de uso; mientras arrancan instancias se prioriza el panel y las novedades esperan en el broker | Un aumento de hasta 1,67 veces la carga del momento se absorbe sin perder QA-2 | Un escalón mayor puede **incumplir QA-2** hasta que llega la capacidad nueva, y atrasar QA-1 |
| QA-1: una novedad cambia un vuelo | Núcleo aplica (espera en cola ≤ 40 s + aplicación ≤ 30 s) → outbox → `panel.changed.v1` → notificador → SSE → `GET /panel` | Cambio visible dentro de los 100 s asignados al núcleo y al cliente | Medir la etapa del notificador |
| QA-1: la app se conecta o reconecta mientras ocurre un cambio | Abre SSE, recibe `ready` y recién entonces revalida; al reconectar revalida otra vez; con SSE caído revalida cada 60 s | Ningún cambio queda sin ver por una carrera entre la consulta y la suscripción ni por una desconexión | Con SSE caído, la etapa de cliente puede llegar a 60 s |
| RF-04: el hotel cambia una fecha que el usuario editó | Se aplica la fecha del proveedor, se conservan las notas, se agrega un aviso y se envía push | Panel fiel al proveedor, sin perder anotaciones | — |
| RF-04: el usuario borró una reserva y llega una novedad | La marca de borrado descarta la novedad | La reserva no reaparece | Si la borró por error, no ve cambios posteriores |
| RF-04: un cambio manual y una novedad del mismo usuario llegan a la vez | Cada transacción bloquea la fila del panel del usuario; la segunda espera a la primera | El panel termina con los dos cambios y la versión aumenta de a uno | Los cambios de un mismo usuario esperan en fila (son pocos por minuto) |
| RF-05: llega una reserva sin viaje | Con fechas: se asigna o se crea un viaje. Sin fechas: queda en "sin asignar" | El panel se arma solo cuando hay datos | Viajes cercanos en fechas pueden confundirse; el usuario corrige |
| RF-05: termina un viaje | La tarea diaria lo archiva a la fecha de fin + 2 días y lo elimina al año | Panel acotado; datos no acumulados | Hasta un día de demora para archivar |
| RF-05: el usuario queda varado después de la fecha de fin | Si el proveedor reprograma, el viaje sigue activo o se reactiva. Si nadie informa nada, se archiva y el usuario lo reactiva; no se vuelve a archivar por 7 días | El panel no depende de que el proveedor informe todo | La fecha de fin sale de los datos de las reservas: el sistema no infiere emergencias |

### Estado de los drivers

| Driver | Estado | Qué falta |
|---|---|---|
| QA-2 | Cumplido por diseño en carga normal | Puede incumplirse durante el arranque de instancias ante un escalón mayor a 1,67 veces (riesgo aceptado); prueba de carga con paneles típicos, grandes y en el límite |
| QA-3 | Parcial | Cumplido por diseño para aperturas con caché; las aperturas sin caché cuentan en el 95 % y su proporción y tiempo están pendientes de medir (cobertura pendiente) |
| QA-4 | Parcial | Cubierto para instancias, nodos y zonas; la falla de región sigue como riesgo aceptado; medir los tiempos |
| QA-5 | Parcial | Ajustar el umbral de escalado y validar las cifras de carga supuestas |
| RF-04 | Cumplido por diseño | — |
| RF-05 | Cumplido por diseño | Validar los márgenes de 2 y 7 días |
| QA-1 (etapas del núcleo y del cliente) | Cumplido por diseño en carga normal | Medir la etapa del notificador; con SSE caído la etapa de cliente puede llegar a 60 s; el conflicto a escala de la iteración 2 sigue abierto |
| QA-6 (lado consumidor) | Cumplido por diseño | Pruebas de reentrega, conflictos y marcas de borrado |

### Riesgos

| Riesgo | Driver | Tratamiento |
|---|---|---|
| QA-1 a escala: si se pierde un aviso del proveedor de correo, las cuentas con reconciliación de 15 min o 6 h superan los 5 minutos (de la iteración 2). No se estimó qué fracción de las actualizaciones afecta frente al 1 % que permite el percentil 99 | QA-1 | **Aceptado** por ambos integrantes (2026-10-28). Mitigación posible: detectar buzones que dejaron de recibir avisos y adelantar su reconciliación. Para una iteración 5 si hay tiempo |
| Un escalón de carga mayor a 1,67 veces durante el arranque de instancias | QA-2, QA-5 | Aceptado por CON-5: los días de pico del enunciado son una expectativa, no una garantía. Mitigado con priorización. Si en operación hay picos regulares, se agrega escalado programado con datos reales |
| Las cifras de carga son suposiciones | QA-5 | Validar con pruebas de carga del prototipo |
| Falla de una región completa | QA-4 | Aceptado desde la iteración 1 |
| Ventana con durabilidad reducida cuando un nodo de la base queda con una sola copia (cae la primaria, la réplica o una zona) | QA-4 | Aceptado: se priorizan las escrituras disponibles sobre bloquearlas; la réplica se reconstruye de inmediato y el tiempo en esa situación genera alerta |
| Desincronización entre tablas y panel por un error de programación | QA-2 | Único escritor, versión en el documento y reconstrucción |
| Push duplicado si el trabajador envía y cae antes de registrar el envío | QA-1 | Aceptado: la clave de colapso hace que el dispositivo muestre uno solo |
| Aperturas de la app sin caché | QA-3 | Cobertura pendiente: cuentan en el 95 %; se supone que son menos del 5 %; si no, se agrega la respuesta mínima |

### Supuestos de esta iteración

Son estimaciones para dimensionar y comparar opciones, no comportamientos garantizados: el uso real solo se conoce
con el sistema en operación. Cada una indica de qué dato del enunciado o de los QA parte.

| Supuesto | De dónde parte | Uso |
|---|---|---|
| Cada usuario activo carga el panel hasta 50 veces por semana (abrir la app o la web, recargar, volver a la pantalla) | 2 M de usuarios activos semanales (QA-5); el enunciado no da la frecuencia de uso | Estimar lecturas: ~165/s promedio y ~830/s con el pico de 5 veces, globales (ADR-0042) |
| Un panel típico tiene hasta 3 viajes activos y 20 reservas (hasta 20 KB); uno grande, hasta 15 viajes y 150 reservas (hasta 150 KB) | Ninguno del enunciado; uso esperado de un panel de viajes | Tamaño del documento y prueba de QA-2 (ADR-0040) |
| Las aperturas sin caché son menos del 5 % del total | La caché solo se pierde al instalar, cambiar de dispositivo o si el sistema la borra | Cobertura de QA-3 (ADR-0041) |
| Del 2 al 5 % de los usuarios activos tiene la app abierta al mismo tiempo | 2 M de usuarios activos semanales (QA-5) | Conexiones del notificador y de la puerta de entrada (ADR-0046) |
| La red 4G suma entre 600 y 1000 ms a una solicitud | Condición de red de QA-3; el enunciado no la cuantifica | Justificar la caché local (ADR-0041) |
| Una instancia tarda de 1 a 3 minutos en arrancar | Depende de la plataforma, que se elige al implementar | Umbral de escalado (ADR-0043) |
| El escalado arranca al 60 % de uso | Tiempo de arranque supuesto | Margen de 1,67 veces durante el arranque (ADR-0043) |
| Un viaje está completo 2 días después de su última reserva | RF-05 ("una vez que el viaje se completa"); el enunciado no define cuándo | Momento del archivado (ADR-0045) |
| Un viaje reactivado a mano no se archiva por 7 días | Caso del usuario varado sin reservas futuras | Reactivación (ADR-0045) |
| Los viajes archivados se eliminan al año | RF-05 ("archivarse o eliminarse") y CON-3 (suposición) | Retención (ADR-0045) |
| Los avisos al usuario duran 7 días en el panel | Ninguno; valor de producto | Lista `notices` (ADR-0044) |
| Pico de 5 veces el promedio | Suposición ya registrada en QA-5 | Todo el dimensionamiento |
| Startup con recursos limitados (CON-5) | El enunciado presenta a Trotamundos como "una nueva empresa emergente" | Escalado solo reactivo (ADR-0043) |

### Impacto en otras iteraciones

Registrado en el [registro de impactos](impact-log.md):

* **Iteración 2:** el núcleo consume `booking.change.detected.v1` sin cambios al contrato; el consumo sigue con 8
  shards y un consumidor activo cada uno; el núcleo publica dos eventos nuevos (`panel.changed.v1` y
  `trip.changed.v1`) en el exchange `travel.domain`; la zona C del broker también aloja el monitor de base y las
  réplicas que se reconstruyen. Se aceptan el módulo `asistencia` en el núcleo (ADR-0026) y el broker en tres zonas
  (ADR-0028).
* **Iteración 4:** la lectura de un itinerario compartido se hace en la partición del dueño; la autenticación de la
  API y de la conexión SSE se define ahí; la analítica recibe `trip.changed.v1`, incluidos archivados y eliminados,
  y debe decidir cómo anonimizar lo que ya recibió.

### ¿Se sigue iterando?

Sí: iteración 4 (seguridad de compartición, internacionalización, analítica y evolucionabilidad). El riesgo de QA-1
a escala queda para una iteración 5 si hay tiempo.

### Prototipo

| Qué demuestra | Cómo | Spec | ADRs |
|---|---|---|---|
| Panel por lectura por clave y coherencia en la misma transacción | `GET /panel`; un cambio manual y una novedad actualizan el documento | `itinerary-api.v1.yaml` | 0040, 0044 |
| Concurrencia por usuario | Un cambio manual y una novedad del mismo usuario al mismo tiempo: el panel tiene los dos y la versión sube en 2 | `itinerary-api.v1.yaml` | 0040 |
| Revalidación por versión | `GET /panel` con `If-None-Match` devuelve `304` | `itinerary-api.v1.yaml` | 0041 |
| Aviso de cambios | Un cliente SSE recibe la versión nueva tras un commit; con dos instancias del notificador, solo la que tiene la conexión la envía; un cambio entre la suscripción y la revalidación, o durante una desconexión, termina visible | `panel-changed.v1.yaml` | 0046 |
| Dueño por campo y marca de borrado | Pruebas sobre el módulo `reservas` | `booking-change-detected.v1.yaml` | 0044 |
| Asignación a viajes | Pruebas sobre el módulo `viajes`, con y sin fechas | `booking-change-detected.v1.yaml` | 0048 |
| Archivado y reactivación | Tarea con fecha simulada; `POST /trips/{tripId}/reactivate` | `trip-changed.v1.yaml` | 0045 |
| Priorización | Las operaciones de baja prioridad reciben `503` antes que el panel | `itinerary-api.v1.yaml` | 0047 |

Estado: implementado, con pruebas en `prototype/tests/test_iteracion3_panel.py`. La concurrencia se probó con dos
cambios manuales simultáneos y el aviso con dos instancias del notificador. La revalidación de la app después del
`ready` o de una desconexión no se prueba, porque el prototipo no tiene cliente. La partición usa 256 particiones
lógicas en dos bases del mismo motor; la conmutación entre zonas, el monitor y el escalado se documentan, pero no
se simulan. La multirregión sí se simula (dos regiones, iteración 4).

### Revisión de la iteración

La iteración se revisó con una auditoría independiente (un revisor sin el contexto de las decisiones). Las
correcciones aplicadas fueron:

* el evento propio para el notificador y la cola por instancia;
* la comparación de ADR-0042 contra la base real de ADR-0003, con el aislamiento por nodo;
* el monitor de base en tres zonas y la pérdida de una zona;
* CON-5 para el argumento de costo;
* el consumo de novedades fijo;
* las reglas para reservas sin fechas, reservas borradas y reactivación;
* la separación de las ADRs que tenían dos decisiones;
* los nombres de tácticas según Bass (4ta edición);
* los códigos `429` y `503`;
* la marca de suposición en las cifras, y documentos desactualizados.

Después, la revisión cruzada de Tomas Lateana agregó:

* el orden de conexión SSE antes de revalidar, la revalidación al reconectar y el respaldo con SSE caído (ADR-0046);
* la política de escrituras cuando un nodo de la base queda con una sola copia (ADR-0042);
* el bloqueo por usuario y la versión creciente del panel (ADR-0040);
* la deduplicación de los push y la configuración de las colas del notificador (ADR-0046, `ingestion-operations.md`);
* los tamaños de referencia del panel y la estrategia para paneles grandes (ADR-0040);
* las aperturas sin caché dentro del 95 % de QA-3 (ADR-0041).
