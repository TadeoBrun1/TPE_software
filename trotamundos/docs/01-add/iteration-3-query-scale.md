# Iteración 3 — Consulta, latencia, disponibilidad y escala

**Responsable:** Tadeo Brun (integrante B)
**Fecha:** 2026-10-28
**Estado:** En revisión. Las ADRs 0040 a 0045 están en `proposed` hasta la revisión cruzada.
**Rango de ADRs:** 0040 a 0059 (ver [CONTRIBUTING](../../CONTRIBUTING.md))

> Las decisiones se tomaron eligiendo entre alternativas planteadas para cada punto; las descartadas y sus razones
> están en cada ADR. Lo que afecta a la iteración 2 está en el [registro de impactos](impact-log.md).

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
| QA-4 | Detección en 30 s, redirección en 60 s, máximo 5 min/mes | H, H | Detección y conmutación de núcleo y base dentro de la región |
| QA-5 | 2 M usuarios activos, pico de 5 veces, cumpliendo QA-1 y QA-2 | H, H | Partición de la base, escalado y sobrecarga |
| RF-04 | Agregar, editar y eliminar reservas manualmente | Media | Conflicto entre cambios manuales y novedades |
| RF-05 | Agrupar por viaje y archivar al completarse | Alta | Asignación a viajes, criterio de completo, archivado |
| QA-1 (etapas del núcleo y del cliente) | 100 s de los 300 s asignados por la iteración 2 | H, H | Aplicación de novedades y aviso al cliente |
| QA-6 (lado consumidor) | El 99,9 % de los mensajes válidos sin pérdida ni duplicación | H, M | Aplicación de novedades en el núcleo |

### Restricciones que aplican

| ID | Efecto en esta iteración |
|---|---|
| CON-3 (suposición) | Los datos no salen de la región de origen: la recuperación es dentro de la región |
| CON-4 | La app móvil nativa puede guardar el panel en el dispositivo |

### Lo que no se trata acá

| Tema | Decisión |
|---|---|
| QA-1 a escala con avisos perdidos (conflicto abierto de la iteración 2) | **Riesgo aceptado.** Se registra en el Paso 7; su mitigación queda para una iteración 5 si hay tiempo |
| Falla de una región completa | Sigue siendo un riesgo aceptado (ADR-0003); esta iteración no diseña recuperación entre regiones |
| Autenticación del viajero y compartición | Iteración 4 |

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
| Núcleo | Camino de lectura del panel, aplicación de novedades, gestión manual y ciclo de vida |
| Base operativa | Organización dentro de la región y conmutación |
| Clientes web y móvil | Comportamiento al abrir y ante cambios |
| Puerta de entrada | Límites y prioridades ante sobrecarga |

## Paso 4 — Patrones y tácticas elegidos

### 4.1 Patrones

| Patrón | Cómo se aplica | Drivers | ADR |
|---|---|---|---|
| CQRS (un solo almacén) y *Materialized View* | Documento `panel_por_usuario`, actualizado en la misma transacción que el cambio | QA-2, QA-5 | [0040](../03-adr/0040-modelo-de-lectura-del-panel.md) |
| *Cache-Aside* en el cliente con revalidación (*stale-while-revalidate*) | La app muestra el panel guardado y revalida con la versión | QA-3 | [0041](../03-adr/0041-cache-local-y-notificador.md) |
| *Publish-Subscribe* (ADR-0002) | El notificador consume los eventos de dominio | QA-1, QA-9 | [0041](../03-adr/0041-cache-local-y-notificador.md) |
| *Sharding* | Particiones lógicas por hash de usuario, con réplica sincrónica por nodo | QA-5, QA-4 | [0042](../03-adr/0042-particion-de-la-base-por-usuario.md) |
| *Rate Limiting* y *Load Shedding* | Límite por cliente y rechazo de operaciones de baja prioridad | QA-5, QA-2 | [0043](../03-adr/0043-escalado-reactivo-y-degradacion.md) |
| *Idempotent Receiver* y *Transactional Outbox* (iteración 2) | Aplicación de novedades en una transacción local | QA-6 | [0044](../03-adr/0044-aplicacion-de-novedades-en-el-nucleo.md) |
| *Scheduler Agent* / tarea por lotes | Archivado diario por partición | RF-05 | [0045](../03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md) |

### 4.2 Tácticas

Nombres según Bass, Clements y Kazman (4ta edición).

| Atributo | Táctica | Cómo se aplica | Drivers | ADR |
|---|---|---|---|---|
| Performance | Mantener múltiples copias de los datos | Documento del panel en la base; panel guardado en la app | QA-2, QA-3 | [0040](../03-adr/0040-modelo-de-lectura-del-panel.md), [0041](../03-adr/0041-cache-local-y-notificador.md) |
| Performance | Reducir la sobrecarga computacional | El panel no se arma en cada lectura y solo contiene viajes activos | QA-2 | [0040](../03-adr/0040-modelo-de-lectura-del-panel.md), [0045](../03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md) |
| Performance | Aumentar recursos | Escalado automático de núcleo, notificador e ingesta; nodos nuevos para particiones | QA-5 | [0042](../03-adr/0042-particion-de-la-base-por-usuario.md), [0043](../03-adr/0043-escalado-reactivo-y-degradacion.md) |
| Performance | Administrar las solicitudes de trabajo | Límite por cliente en la puerta de entrada | QA-5 | [0043](../03-adr/0043-escalado-reactivo-y-degradacion.md) |
| Performance | Priorizar eventos | El panel se atiende antes que las operaciones secundarias | QA-2 | [0043](../03-adr/0043-escalado-reactivo-y-degradacion.md) |
| Performance | Limitar la respuesta a eventos | Las novedades esperan en el broker durante la sobrecarga | QA-5 | [0043](../03-adr/0043-escalado-reactivo-y-degradacion.md) |
| Performance | Programar recursos | Archivado en el horario de menor carga | QA-5 | [0045](../03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md) |
| Disponibilidad | Monitoreo / heartbeat | La puerta de entrada saca instancias del núcleo que no responden; el monitor de base detecta primarias caídas en 30 s | QA-4 | [0042](../03-adr/0042-particion-de-la-base-por-usuario.md) |
| Disponibilidad | Redundancia pasiva | Réplica sincrónica que se promueve a primaria | QA-4 | [0042](../03-adr/0042-particion-de-la-base-por-usuario.md) |
| Disponibilidad | Redundancia activa (iteración 1) | Varias instancias del núcleo y del notificador en al menos dos zonas | QA-4 | [0003](../03-adr/0003-despliegue-por-regiones-con-region-de-origen.md) |
| Disponibilidad | Degradación elegante | Sin notificador la app usa su caché; en sobrecarga se rechaza lo secundario | QA-4 | [0041](../03-adr/0041-cache-local-y-notificador.md), [0043](../03-adr/0043-escalado-reactivo-y-degradacion.md) |
| Modificabilidad | Dividir módulo | El notificador es un proceso aparte del núcleo | QA-5 | [0041](../03-adr/0041-cache-local-y-notificador.md) |
| Modificabilidad | Aumentar la cohesión | Las reglas de conciliación y asignación viven en un solo módulo cada una | RF-04, RF-05 | [0044](../03-adr/0044-aplicacion-de-novedades-en-el-nucleo.md) |
| Seguridad | Limitar la exposición | Eliminación de viajes archivados al año; avisos sin datos de reservas | CON-3 | [0041](../03-adr/0041-cache-local-y-notificador.md), [0045](../03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md) |

## Paso 5 — Instanciación

### Elementos nuevos o refinados

| Elemento | Tipo | Responsabilidades |
|---|---|---|
| Núcleo / `panel` (proyector) | Módulo del núcleo | Único escritor de `panel_por_usuario`; regenera el panel desde las tablas; expone la versión |
| Núcleo / `reservas` | Módulo del núcleo (refinado) | Aplica novedades y cambios manuales con dueño por campo; registra campos editados por el usuario |
| Núcleo / `viajes` | Módulo del núcleo (refinado) | Asigna reservas a viajes por fechas; tarea diaria de archivado y eliminación |
| Núcleo / ruteo de particiones | Módulo del núcleo | Calcula la partición de cada usuario y conoce qué nodo es primaria |
| Notificador | Proceso nuevo, por región | Consume `booking.changed.v1` y `trip.changed.v1`; mantiene conexiones SSE; envía push del sistema operativo |
| Base operativa | Particiones lógicas en nodos con primaria y réplica sincrónica | Guarda todo lo de un usuario en su partición |
| Monitor de base | Componente de operación | Heartbeat de primarias y promoción de réplicas |
| Puerta de entrada | Refinada | Límite por cliente y clasificación por prioridad; enruta `/panel/events` al notificador |
| App móvil y web | Refinadas | Caché local del panel con revalidación por versión; conexión SSE con la app abierta |

### Reglas de interacción

| Regla | Justificación |
|---|---|
| Toda escritura sobre viajes o reservas actualiza en la misma transacción las tablas, el panel y la outbox | Coherencia fuerte del panel y publicación garantizada (ADR-0040, ADR-0027) |
| Todo lo de un usuario vive en su partición; ninguna transacción cruza particiones | La transacción sigue siendo local (ADR-0042) |
| Los avisos del notificador llevan solo la versión del panel; los datos se piden por la API | No exponer datos de reservas fuera de la API autenticada |
| Una novedad cambia los campos del proveedor; nunca los del usuario | Dueño por campo (ADR-0044) |
| Las operaciones de baja prioridad pueden rechazarse con `429` o `503` y `Retry-After` | Proteger el panel en la sobrecarga (ADR-0043) |

### Contratos nuevos o modificados

| Contrato | Archivo | Cambio |
|---|---|---|
| API de itinerarios | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) | Nuevo; reemplaza al ejemplo de formato. Panel con `ETag`, avisos SSE, viajes archivados y gestión manual |
| Cambios confirmados de viajes | [trip-changed.v1.yaml](../../specs/asyncapi/trip-changed.v1.yaml) | Nuevo: creado, actualizado, archivado, eliminado, con la versión del panel |
| Cambios confirmados de reservas | [booking-confirmed.v1.yaml](../../specs/asyncapi/booking-confirmed.v1.yaml) | Sin cambios; el notificador es un consumidor nuevo |
| Novedades de reservas | [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml) | Sin cambios; el núcleo lo consume con las reglas de ADR-0044 |

## Paso 6 — Vistas actualizadas y ADRs creadas

| Vista | Qué cambió |
|---|---|
| [Vista C&C](../02-views/cc-view.md) | Notificador, monitor de base, conexión SSE y particiones |
| [Vista de despliegue](../02-views/deployment-view.md) | Particiones con primaria y réplica en zonas distintas; notificador en cada zona; escalado |
| [Vista de módulos](../02-views/module-view.md) | Módulos `panel` y ruteo de particiones; regla de único escritor |
| [Vistas de secuencia](../02-views/sequence-views.md) | SEQ-3 (consulta del panel), SEQ-4 (falla de una primaria), SEQ-6 (novedad que pisa una edición manual) |
| [Modelo de dominio](../02-views/domain-model.md) | Campos editados por el usuario, versión del panel, fecha de archivado |

| ADR | Título | Estado |
|---|---|---|
| [0040](../03-adr/0040-modelo-de-lectura-del-panel.md) | Modelo de lectura del panel por usuario, actualizado en la misma transacción | Propuesta |
| [0041](../03-adr/0041-cache-local-y-notificador.md) | Caché local en la app y notificador separado | Propuesta |
| [0042](../03-adr/0042-particion-de-la-base-por-usuario.md) | Partición de la base por usuario con réplica sincrónica | Propuesta |
| [0043](../03-adr/0043-escalado-reactivo-y-degradacion.md) | Escalado solo reactivo, priorización y degradación | Propuesta |
| [0044](../03-adr/0044-aplicacion-de-novedades-en-el-nucleo.md) | Aplicación de novedades: dueño por campo y asignación por fechas | Propuesta |
| [0045](../03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md) | Archivado diario por partición y eliminación al año | Propuesta |

## Paso 7 — Análisis

Recorrido de escenarios sobre el diseño (*Scenario Walkthrough*). Son resultados esperados por diseño, no
mediciones: las cifras de carga son suposiciones que el prototipo y las pruebas de carga deben confirmar.

### Recorridos

| Escenario | Recorrido | Resultado esperado | Límite o riesgo |
|---|---|---|---|
| QA-2: el viajero abre el panel en la web | Entrada global → puerta de entrada → núcleo → lectura por clave en su partición → respuesta | Una lectura por clave; el tiempo queda dominado por la red | Usuarios lejanos de su región suman latencia de red (QA-10) |
| QA-3: abre la app con sesión iniciada | Lee el panel guardado y lo muestra; en paralelo `GET /panel` con versión | Primer contenido sin esperar la red | Primera apertura sin caché depende de la red |
| QA-4: cae una instancia del núcleo | La puerta de entrada deja de enviarle tráfico al fallar el heartbeat | Solo se pierden las solicitudes en curso; los clientes reintentan | Tiempos de heartbeat a medir |
| QA-4: cae la primaria de una partición | El monitor lo detecta en 30 s y promueve la réplica en 60 s | Solo los usuarios de esa partición quedan sin escrituras durante la conmutación, sin pérdida de datos | Pérdida simultánea de las dos zonas: riesgo de región |
| QA-5: pico de 5 veces | El escalado arranca al 60 % de uso; mientras arrancan las instancias se prioriza el panel y las novedades esperan en el broker | El panel sigue respondiendo; QA-1 puede atrasarse | Picos predecibles dependen del margen mínimo |
| QA-1: una novedad cambia un vuelo | Núcleo aplica (≤ 70 s incluida la espera en cola) → outbox → notificador → SSE → `GET /panel` | Cambio visible dentro de los 100 s asignados al núcleo y al cliente | Medir la etapa del notificador |
| RF-04: el hotel cambia una fecha que el usuario editó | Se aplica la fecha del proveedor, se conservan las notas y se avisa | Panel fiel al proveedor, sin perder las anotaciones | Registrar campos editados |
| RF-05: llega una reserva sin viaje | Se asigna al viaje cuyas fechas la cubren o se crea uno nuevo | El panel se arma solo | Viajes cercanos en fechas pueden confundirse; el usuario corrige |
| RF-05: termina un viaje | La tarea diaria lo archiva a la fecha de fin + 2 días y lo elimina al año | Panel acotado; datos no acumulados | Hasta un día de demora para archivar |
| RF-05: el usuario queda varado después de la fecha de fin | Si el proveedor reprograma, la novedad cambia la fecha y el viaje sigue activo (o se reactiva). Si nadie informa nada, se archiva y el usuario lo reactiva a mano | El panel no depende de que el proveedor informe todo | La fecha de fin sale de los datos de las reservas: el sistema no infiere emergencias |

### Estado de los drivers

| Driver | Estado | Qué falta |
|---|---|---|
| QA-2 | Cumplido por diseño | Prueba de carga del panel en el pico |
| QA-3 | Cumplido por diseño para aperturas con caché | Primera apertura sin caché (riesgo menor) |
| QA-4 | Parcial | Cubierto para instancias, zonas y particiones; la falla de región sigue como riesgo aceptado |
| QA-5 | Parcial | Ajustar el umbral de escalado y validar las cifras de carga supuestas |
| RF-04 | Cumplido por diseño | — |
| RF-05 | Cumplido por diseño | Validar el margen de 2 días |
| QA-1 (etapas del núcleo y del cliente) | Cumplido por diseño | Medir la etapa del notificador; el conflicto a escala de la iteración 2 sigue abierto |
| QA-6 (lado consumidor) | Cumplido por diseño | Pruebas de reentrega y conflictos |

### Riesgos

| Riesgo | Driver | Tratamiento |
|---|---|---|
| QA-1 a escala: si se pierde un aviso del proveedor de correo, las cuentas con reconciliación de 15 min o 6 h superan los 5 minutos (de la iteración 2) | QA-1 | **Aceptado.** Mitigación posible: detectar buzones que dejaron de recibir avisos y adelantar su reconciliación. Para una iteración 5 si hay tiempo |
| Los picos predecibles pasan por los minutos de arranque del escalado reactivo | QA-5 | Aceptado: los días de pico del enunciado son una expectativa, no una garantía para todas las semanas y regiones, y pagar capacidad por las dudas no se justifica en una startup. Mitigado con escalado temprano (60 %) y priorización. Si en operación se ven picos regulares, se agrega escalado programado con datos reales |
| Las cifras de carga son suposiciones (aperturas por usuario, conexiones simultáneas) | QA-5 | Validar con pruebas de carga del prototipo |
| La falla de una región completa deja sin servicio a sus usuarios | QA-4 | Aceptado desde la iteración 1; las particiones lo acotan pero no lo resuelven |
| Desincronización entre tablas y panel por un error de programación | QA-2 | Único escritor, versión en el documento y reconstrucción |
| Primera apertura de la app sin caché | QA-3 | Aceptado; el escenario supone sesión iniciada |

### Supuestos de esta iteración

Son estimaciones para dimensionar y comparar opciones, no comportamientos garantizados: el uso real solo se conoce
con el sistema en operación. Cada una indica de qué dato del enunciado o de los QA parte.

| Supuesto | De dónde parte | Uso |
|---|---|---|
| Cada usuario activo carga el panel hasta 50 veces por semana (abrir la app o la web, recargar, volver a la pantalla) | 2 M de usuarios activos semanales (QA-5); el enunciado no da la frecuencia de uso | Estimar las lecturas por segundo: ~165/s promedio y ~830/s con el pico de 5 veces (ADR-0042) |
| Del 2 al 5 % de los usuarios activos tiene la app abierta al mismo tiempo | 2 M de usuarios activos semanales (QA-5) | Dimensionar las conexiones del notificador (ADR-0041) |
| Un viaje está completo 2 días después de su última reserva | RF-05 ("una vez que el viaje se completa"); el enunciado no define cuándo | Momento del archivado (ADR-0045) |
| Los viajes archivados se eliminan al año | RF-05 ("archivarse o eliminarse") y CON-3 (suposición) | Retención de datos (ADR-0045) |
| El escalado arranca al 60 % de uso | QA-5 (pico de 5 veces) y el tiempo de arranque de una instancia (1 a 3 minutos) | Umbral de escalado (ADR-0043) |
| Pico de 5 veces el promedio | Suposición ya registrada en QA-5 | Todo el dimensionamiento |

### Impacto en otras iteraciones

Registrado en el [registro de impactos](impact-log.md):

* **Iteración 2:** el núcleo consume `booking.change.detected.v1` sin cambios; el notificador es un consumidor nuevo
  de `booking.changed.v1`; se agrega el evento `trip.changed.v1` al exchange `travel.domain`. Se aceptan el módulo
  `asistencia` en el núcleo (ADR-0026) y el broker en tres zonas (ADR-0028).
* **Iteración 4:** la lectura de un itinerario compartido se hace en la partición del dueño; la autenticación de
  `bearerAuth` y de la conexión SSE se define ahí; la analítica recibe `trip.changed.v1`, incluidos los
  archivados y eliminados, y debe decidir cómo anonimizar lo que ya recibió.

### ¿Se sigue iterando?

Sí: iteración 4 (seguridad de compartición, internacionalización, analítica y evolucionabilidad). El riesgo de QA-1
a escala queda para una iteración 5 si hay tiempo.

### Prototipo

| Qué demuestra | Cómo | Spec | ADRs |
|---|---|---|---|
| Panel por lectura por clave y coherencia en la misma transacción | Endpoint `GET /panel`; un cambio manual y una novedad actualizan el documento | `itinerary-api.v1.yaml` | 0040, 0044 |
| Revalidación por versión | `GET /panel` con `If-None-Match` devuelve `304` | `itinerary-api.v1.yaml` | 0041 |
| Aviso de cambios | Un cliente SSE recibe la versión nueva tras un commit | `trip-changed.v1.yaml`, `booking-confirmed.v1.yaml` | 0041 |
| Dueño por campo y asignación a viajes | Pruebas sobre el módulo `reservas` | `booking-change-detected.v1.yaml` | 0044 |
| Archivado | Tarea con fecha simulada | `trip-changed.v1.yaml` | 0045 |

La partición se demuestra con dos particiones lógicas en un mismo motor; la conmutación entre zonas, el escalado y
la multirregión se documentan, pero no se simulan en el prototipo local.
