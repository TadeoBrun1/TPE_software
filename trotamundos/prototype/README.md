# Prototipo de Trotamundos

**Estado (2026-11-22):** la primera entrega se integró en `main` mediante PR #10 y #11. Cubre las iteraciones 2
(ingesta idempotente), 3 (panel, SSE y cambios), 4 (compartición, autenticación y auditoría) y, para la segunda
entrega, la 5 (recomendación de alternativas con human-in-the-loop, opción A). La analítica, la tarjeta para redes,
la asistencia de agencia y el medio nuevo (ferry) quedan fuera del alcance. La iteración 5 suma también la
eliminación de la cuenta (ADR-0085). Las 83 pruebas automáticas pasan en un solo proceso, con SQLite y un broker en
memoria. Los adaptadores de PostgreSQL y RabbitMQ y el `docker-compose.yml`
están escritos, pero no se ejecutaron en el entorno donde se armó el prototipo (no había Docker). Sí se probó a
mano una región con cada proceso por separado, comunicados por HTTP (con SQLite y un broker en memoria por proceso).

El código sigue la documentación: cada carpeta corresponde a un módulo de la [vista de módulos](../docs/02-views/module-view.md),
los mensajes y las respuestas se validan contra los archivos de [`specs/`](../specs/) (no se copian los esquemas),
y cada decisión implementada remite a su ADR. Una ejecución local no demuestra capacidad, disponibilidad entre
zonas ni el cumplimiento medido de los QA: las pruebas comprueban comportamiento y contratos.

## 1. Cómo ejecutarlo

Requisitos: Python 3.12 o superior (se probó con 3.13). Desde `trotamundos/prototype`:

```bash
pip install -r requirements.txt
python -m pytest -q          # 83 pruebas, unos 40 segundos
python demo.py               # recorrido por la API con dos regiones; --logs muestra los logs JSON
python sistema.py            # entrada global en http://localhost:8080, dos regiones en un proceso
```

`sistema.py` y `demo.py` arman las dos regiones (sa-east y eu-west) en el mismo proceso: cada una tiene su núcleo
con dos nodos de base, su registro de auditoría, su broker, su notificador, su ingesta, su proceso de recomendación
(con cuatro APIs de búsqueda sintéticas), su proveedor de identidad y su puerta de entrada. Las regiones solo se hablan por el canal entre puertas.

### Con Docker

```bash
docker compose up --build    # 17 contenedores: entrada global y, por región, PostgreSQL, RabbitMQ y 6 procesos
```

| Puerto | Qué es |
|---|---|
| `localhost:8080` | Entrada global (lo que usaría la app) |
| `localhost:8081` / `8082` | Puertas de entrada de sa-east y eu-west (avisos de proveedores) |
| `127.0.0.1:9001` / `9002` / `9003` | Núcleo, ingesta y recomendación de sa-east, solo para los endpoints de simulación |

Recorrido mínimo con `curl` (Juan vive en Argentina, así que su región es sa-east):

```bash
J='content-type: application/json'
curl -s localhost:8080/login/region -H "$J" -d '{"email":"juan@example.com","country":"AR"}'
curl -s localhost:8080/id/sa-east/accounts -H "$J" -d '{"email":"juan@example.com","password":"clave-segura","country":"AR"}'
curl -s localhost:8080/id/sa-east/token -H "$J" -d '{"email":"juan@example.com","password":"clave-segura"}'
TOKEN=...   # access_token de la respuesta anterior; userId también viene ahí
curl -s localhost:8080/bookings -H "$J" -H "Authorization: Bearer $TOKEN" -H 'Idempotency-Key: r1' \
     -d '{"type":"hotel","startsAt":"2026-12-10T15:00:00+01:00","endsAt":"2026-12-12T11:00:00+01:00","location":"Madrid"}'
curl -si localhost:8080/panel -H "Authorization: Bearer $TOKEN"                    # ETag "1"
curl -si localhost:8080/panel -H "Authorization: Bearer $TOKEN" -H 'If-None-Match: "1"'   # 304
curl -s -X POST localhost:8080/panel/events/ticket -H "Authorization: Bearer $TOKEN"     # ticket de 30 s
curl -N "localhost:8080/panel/events?ticket=<ticket>"                              # event: ready, panel-changed
```

Para que llegue una reserva de un proveedor simulado (la vinculación de cuentas, RF-02, no está en el alcance), se
usan los endpoints de simulación con la clave de administración de desarrollo. El orden importa: la ingesta
consulta en cuanto conoce la vinculación y después cada 15 minutos.

```bash
A='X-Admin-Key: solo-desarrollo-admin-no-usar-en-produccion'
curl -s 127.0.0.1:9001/simulacion/vinculaciones -H "$A" -H "$J" -d '{"connectionId":"c1","userId":"<userId>","providerId":"hotel-sol"}'
curl -s 127.0.0.1:9002/simulacion/hotel -H "$A" -H "$J" \
     -d '{"connectionId":"c1","reserva":{"reservationId":"H1","version":1,"status":"CONFIRMED","checkIn":"2026-12-11","checkOut":"2026-12-12","city":"Madrid","timeZone":"Europe/Madrid"}}'
curl -s 127.0.0.1:9002/simulacion/vinculaciones -H "$A" -H "$J" \
     -d '{"connectionId":"c1","userId":"<userId>","homeRegion":"sa-east","providerId":"hotel-sol","fuente":"provider"}'
```

Recomendación (iteración 5): si después el hotel cancela la reserva (`"version":2,"status":"CANCELLED"` por el
mismo endpoint de simulación), llegan las alternativas.

```bash
curl -s localhost:8080/trips/<tripId>/suggestions -H "Authorization: Bearer $TOKEN"
curl -s localhost:8080/suggestions/<id>/feedback -H "$J" -H "Authorization: Bearer $TOKEN" -d '{"action":"reject","reason":"too_expensive"}'
curl -s localhost:8080/suggestions/<id>/feedback -H "$J" -H "Authorization: Bearer $TOKEN" -d '{"action":"accept"}'
curl -s -X PUT localhost:8080/recommendations/preferences -H "$J" -H "Authorization: Bearer $TOKEN" -d '{"enabled":false}'
curl -s -X POST 127.0.0.1:9003/simulacion/busqueda/hotel-sol/falla -H "$A" -H "$J" -d '{"veces":3}'
curl -s -X POST 127.0.0.1:9003/simulacion/entrenamiento -H "$A"     # entrenamiento diario a pedido
```

Los correos de invitación simulados quedan en `docker compose exec nucleo-sa-east cat /datos/buzon-sa-east.jsonl`.

## 2. Qué hay en cada carpeta

| Carpeta | Módulo (vista de módulos) | ADR | Contrato |
|---|---|---|---|
| `nucleo/api` | núcleo/api | 0040, 0041, 0047 | [OpenAPI](../specs/openapi/itinerary-api.v1.yaml) |
| `nucleo/panel` | núcleo/panel (único escritor de `panel_por_usuario`) | 0040, 0041 | `panel.changed.v1` |
| `nucleo/reservas` | núcleo/reservas (manuales, novedades, dueño por campo, marcas de borrado) | 0044, 0066 | [ingestion-contract.md](../specs/ingestion-contract.md) |
| `nucleo/viajes` | núcleo/viajes (asignación por fechas, archivado diario) | 0045, 0048 | `trip.changed.v1` |
| `nucleo/datos` | núcleo/ruteo-particiones (256 particiones en 2 nodos) | 0042 | — |
| `nucleo/comparticion`, `nucleo/auditoria` | núcleo/comparticion y núcleo/auditoria | 0061, 0062 | [access-audit.md](../specs/access-audit.md) |
| `nucleo/usuarios` | núcleo/usuarios (perfil y marcadores de viajes compartidos) | 0062 | — |
| `nucleo/esquemas` | núcleo/esquemas-detalles | 0066 | [schemas/](../specs/schemas/) |
| `nucleo/mensajeria` | suscriptor-novedades y publicador-eventos | 0027, 0043 | [AsyncAPI](../specs/asyncapi/), [core-publication.md](../specs/core-publication.md) |
| `ingesta/*` | planificador, coordinador, gestor-vinculaciones, adaptadores-acceso, receptor-avisos, procesador, registro-sincronizacion y publicador-novedades | 0020 a 0025, 0028 | [ingestion-operations.md](../specs/ingestion-operations.md) |
| `notificador/sse`, `avisos`, `push` | conexiones-sse, consumidor-avisos y envio-push | 0046 | `panel.changed.v1` |
| `entrada/` | entrada/resolucion-regional | 0003, 0060 | — |
| `contratos/` | contratos (validadores leídos de `specs/`, topología y regla de shards) | 0002, 0028 | todos |
| `comun/observabilidad.py` | observabilidad | 0067 | encabezados `traceparent` |
| `comun/infraestructura/` | biblioteca técnica común: puertos de base, broker, outbox, HTTP, reloj y límites | 0024, 0027, 0028 | — |
| `puerta/` | simulación de la puerta de entrada (producto en la arquitectura) | 0004, 0047, 0060, 0062 | — |
| `identidad/` | simulación del proveedor de identidad regional (producto OIDC) | 0060 | — |
| `nucleo/reservas/propuestas.py`, `nucleo/mensajeria/consumidor_sugerencias.py` | núcleo/reservas (reservas propuestas, conciliación y vencimiento) y suscriptor-sugerencias | 0084 | `suggestion.accepted.v1` |
| `recomendacion/hechos`, `perfiles` | recomendación/receptor-hechos y perfiles (opt-out y borrado) | 0081 | `booking.facts.v1`, [recommendation.md](../specs/recommendation.md) |
| `recomendacion/busqueda` | recomendación/busqueda-ofertas (puerto, adaptadores, caché, cubeta y corte por proveedor) | 0082 | [offer-search.md](../specs/offer-search.md) |
| `recomendacion/modelo` | recomendación/modelo (características, ranking, entrenamiento y registro de versiones) | 0083 | [recommendation.md](../specs/recommendation.md) |
| `recomendacion/sugerencias`, `api` | recomendación/sugerencias (generación, feedback y eventos) y su API | 0084 | `suggestions.available.v1`, `suggestion.accepted.v1`, [OpenAPI](../specs/openapi/itinerary-api.v1.yaml) |
| `nucleo/usuarios/eliminacion.py`, `ingesta/cuentas/`, `identidad/` | eliminación de la cuenta: borrado en el núcleo con marca de cuenta eliminada, bajas en la ingesta, la identidad y el directorio | 0085 | `account.deleted.v1`, `DELETE /account` |
| `simuladores/` | buzón, API de hotel y API de aerolínea sintéticas; APIs de búsqueda y viajeros sintéticos (iteración 5); endpoints de simulación | CON-1, CON-2 | — |
| `sistema.py`, `docker-compose.yml` | ensamble local y despliegue de dos regiones | 0003 | — |

Reglas de dependencia comprobables en el código: núcleo, ingesta, notificador y recomendación no se importan entre
sí; los cuatro usan `contratos`, `comun/observabilidad` y `comun/infraestructura`. La puerta escribe sus rechazos en el registro
de auditoría de su región con su propio código, según el formato de `access-audit.md`.

## 3. Qué demuestran las pruebas

| Archivo | Qué comprueba | Drivers y ADR |
|---|---|---|
| `test_iteracion2_ingesta.py` | Escenarios de [ingestion-validation.md](ingestion-validation.md) (tabla siguiente), avisos firmados por la puerta, reserva sin fechas que queda sin asignar, dueño por campo con aviso importante y push sin repetir, marca de borrado, consultas con la ingesta detenida y novedades que esperan con el núcleo detenido | QA-1, QA-4, QA-6, QA-8; 0001, 0002, 0020 a 0028, 0044 |
| `test_iteracion3_panel.py` | Panel versionado con ETag y `304`, igual al regenerado desde las tablas; Idempotency-Key; asignación por fechas; 15 viajes completos y el resto en resumen; dos cambios concurrentes del mismo usuario (versión + 2); `If-Match` 400/412; `details` validado; archivado diario, reactivación por 7 días y eliminación al año; prioridades ante sobrecarga; 429 auditado; SSE `ready` y `panel-changed` a través de la entrada global; dos instancias del notificador; ticket SSE vencido o usado como token; telemetría del panel mostrado deduplicada | QA-1, QA-2, QA-3, QA-4, QA-5, RF-04, RF-05; 0040 a 0048, 0066, 0067 |
| `test_iteracion4_comparticion.py` | Invitar, aceptar y leer entre regiones con `no-store` y sin campos privados; invitación idempotente; rechazos auditados (`email_mismatch`, `secret_mismatch`, `no_permission`, `owner_endpoint`, `unauthenticated`, `removed`, `owner_region_unavailable`, `bad_region`, `not_found`); sin auditoría no hay acceso (503); tokens con otra audiencia, tipo, emisor, firma, algoritmo o región, vencidos o fuera del canal; sin token ni prefijo, rechazo auditado en la región más cercana; el mismo `userId` en otra región no comparte permisos; un solo salto entre puertas | QA-7; 0060, 0061, 0062, 0067 |
| `test_iteracion5_recomendacion.py` | Cancelación del proveedor → 3 sugerencias, y una manual no; hecho reentregado sin duplicar; push de la cancelación reemplazado por el de las alternativas (misma `collapseKey`); SSE `suggestions-available`; aceptar crea la reserva propuesta (idempotente, sin mover el viaje) y la reserva real la concilia; la propuesta vence con la tarea diaria; rechazar y ajustar reordenan sin violar límites; opt-out y borrado del perfil; con la recomendación desactivada no se perfila y leer no crea el perfil; oferta vencida `409`; enlaces de ofertas validados; solo el dueño ve sus sugerencias; prioridad baja ante sobrecarga y recomendación detenida sin afectar el panel; disrupción masiva a escala 1/10 sin exceder límites de proveedores; proveedor caído (pendiente y completada) y resultado parcial; canario retirado y vuelta atrás; aprendizaje con viajeros sintéticos | QA-11 a QA-17, RF-09; 0081 a 0084 |
| `test_iteracion5_cuenta.py` | Después de `DELETE /account`, el identificador del usuario no aparece en ninguna tabla de ninguna base de la región (salvo la marca de cuenta eliminada); login y directorio borrados; el dueño de un viaje compartido ya no ve al usuario; auditoría con el actor seudonimizado; login reciente exigido (también con token renovado); novedades y hechos atrasados descartados y evento reentregado sin fallas; la marca vence a los 30 días; un token vigente no recrea el perfil de recomendación; el barrido quita lo que un hecho en paralelo dejó; la conexión SSE se cierra | QA-14, QA-7; 0085 |
| `test_contratos.py` | Todo lo publicado cumple su AsyncAPI y lleva `traceparent`; respuestas contra la OpenAPI; regla de shards; topología (colas quorum con un consumidor activo y la cola del notificador como única excepción); esquemas de `details` registrados | 0002, 0028, 0066, 0067 |

Cobertura de los escenarios de [ingestion-validation.md](ingestion-validation.md):

| ID | Estado | Prueba o motivo |
|---|---|---|
| V01 | Cubierto | `test_v01_correo_sin_version_crea_la_reserva` (también descarte por remitente y misma traza) |
| V02 | Cubierto | `test_v02_proveedores_con_formatos_distintos` |
| V03 | Cubierto | `test_v03_reentrega_y_reconsulta_sin_duplicar` |
| V04 | Cubierto | Dos pruebas: por correo (sin orden, queda para conciliar) y por API (versión vieja no reactiva) |
| V05 | Cubierto | `test_v05_caida_de_la_ingesta_antes_y_despues_de_confirmar` |
| V06 | Cubierto | `test_v06_corte_despues_de_la_confirmacion_del_broker` |
| V07 | Cubierto | `test_v07_sin_ruta_la_outbox_no_se_marca_enviada` |
| V08 | Cubierto | `test_v08_caida_del_nucleo_antes_y_despues_del_commit` |
| V09 | Parcial | Revocación durante la consulta; la renovación de suscripciones no está modelada |
| V10 | No cubierto | Asistencia de agencia fuera del alcance |
| V11 | Cubierto | `test_v11_clasificacion_de_errores` (temporal, cuota, autorización, dato inválido y falla de base) |
| V12 a V15 | No cubiertos | Necesitan la infraestructura real: reinicio con datos persistentes, quórum de 3 miembros, carga sostenida y presión de espacio |
| V16 | Parcial | Aviso perdido recuperado por la reconciliación de 15 minutos; vencimiento de suscripción y cursor inválido sin cubrir |
| V17 | No cubierto | Trenes contra el puerto de proveedores y medición del esfuerzo de QA-9 pendientes (sí se validan `details` de tren) |

## 4. Simplificaciones

Cada una es una suposición del prototipo, no una decisión de la arquitectura objetivo.

* Las pruebas usan SQLite y un broker en memoria con la misma semántica que se espera de RabbitMQ: `mandatory`,
  confirmación, ACK después de procesar y reentrega. En SQLite, `BEGIN IMMEDIATE` serializa las escrituras y
  cumple el papel del bloqueo por usuario (`FOR UPDATE` en PostgreSQL).
* Dos nodos por región son dos bases del mismo motor. No hay réplica sincrónica, monitor de base ni conmutación
  entre zonas (ADR-0042). Hay una instancia del núcleo por región: no se simula escalado (ADR-0043) ni la falla de una
  instancia.
* La puerta de entrada y el proveedor de identidad son implementaciones mínimas propias que reemplazan productos.
  El proveedor genera su clave RSA al arrancar: si se reinicia, hay que reiniciar las puertas para que carguen la
  nueva. El canal entre regiones se autentica con una clave compartida en lugar de mTLS.
* Los identificadores de viajes, reservas e invitaciones llevan la partición del dueño, y los de viajes e
  invitaciones también su región (`sa-east:017-…`). Así se lee por clave sin buscar en todos los nodos.
* La vinculación de cuentas (RF-02), el envío de correos de invitación y el push del sistema operativo están
  simulados. Los proveedores son sintéticos y permiten inyectar fallas.
* La sobrecarga se fuerza en las pruebas (`ControlSobrecarga.forzada`); el reloj es inyectable para el archivado,
  los vencimientos y las esperas.
* Eliminación de la cuenta (iteración 5): no hay analítica en el prototipo, así que el borrado de sus hechos
  (ADR-0085) no se prueba; el registro de dispositivos de push está simulado y la revocación de autorizaciones
  delegadas en el proveedor también.
* Estado compartido de la búsqueda: la caché, las búsquedas en curso y las cubetas de fichas viven en la memoria de
  cada instancia; en la arquitectura son una caché compartida por región (ADR-0082). Con una instancia por región,
  como en el prototipo, el comportamiento es el mismo.
* Entrenamiento: corre como hilo de la instancia de recomendación que tiene `ENTRENAR=1`; en la arquitectura es un
  único trabajo programado por región (ADR-0083). Con varias instancias, solo una debe tenerlo.
* Recomendación (iteración 5): las APIs de búsqueda y los viajeros son sintéticos (`simuladores/busqueda.py`,
  `simuladores/datos_sinteticos.py`). La caché, la cubeta de fichas y el corte por proveedor viven en la memoria de
  cada instancia; en la arquitectura objetivo la cubeta es compartida por región (ADR-0082). El entrenamiento usa
  numpy en el mismo proceso; el registro de versiones es una tabla de la base de la recomendación. La prueba de
  disrupción masiva corre a escala 1/10 (1.500 viajeros) con reloj simulado: no mide capacidad real.

## 5. Hallazgos para la documentación

Lo que apareció al implementar y la documentación no resolvía del todo:

1. **`booking.changed.v1` no se publica.** No tenía consumidor (`ingestion-operations.md`) y, con `mandatory`, un
   mensaje sin ruta deja la outbox trabada. Los cambios confirmados, incluidos los manuales, salen en
   `booking.facts.v1`. **Resuelto en la iteración 5:** el contrato se retira y la recomendación consume
   `booking.facts.v1` (ADR-0081).
2. **Biblioteca técnica común.** La vista de módulos decía que solo `contratos` y `observabilidad` son comunes. Los
   puertos de base, broker, outbox y HTTP se usan en los tres procesos; se agregó `comun/infraestructura` a la
   vista como biblioteca técnica sin lógica de dominio.
3. **Descartes por sobrecarga sin auditar.** Un `503` de ADR-0047 sobre una ruta de recurso es un rechazo previo
   al núcleo, pero `access-audit.md` no tiene motivo para él. El prototipo no lo audita (queda en métricas).
4. **Cancelación anterior al alta.** Al llegar el alta se busca la cancelación pendiente de la misma reserva: si
   ambas tienen versión y la del alta es menor, la reserva se crea cancelada y el caso se cierra; si es mayor, se
   crea confirmada; sin orden confiable, la confirmación también queda pendiente de conciliación.
5. **Invitación y auditoría en la misma transacción.** Si no se puede auditar, la invitación no se crea ni se
   envía el correo, y el cliente reintenta con la misma Idempotency-Key.
6. **Ingesta caída.** La puerta responde `503` con `Retry-After` a los avisos de proveedores; la reconciliación
   cubre los avisos que el proveedor no reintente.
7. **SSE a través de la entrada global.** La entrada global tiene que reenviar el flujo a medida que llega; si
   espera la respuesta completa, la conexión nunca devuelve el `ready`.
8. **Solicitud sin token ni prefijo de región.** ADR-0060 no dice adónde va, por ejemplo, un `DELETE /bookings/{id}`
   sin token (los identificadores de reservas no llevan región). El prototipo supone que la entrada global la manda
   a la región más cercana, cuya puerta rechaza con `401` y audita el rechazo.

Hallazgos de la iteración 5:

9. **`booking.facts.v1` sin horas.** La recomendación compara horarios con la reserva cancelada y el evento solo
   traía fechas. Se agregaron `startsAt` y `endsAt` opcionales (0.2.0); la analítica sigue guardando el día.
10. **Borrar el perfil no reactiva.** Si el viajero desactivó la recomendación y después borra el perfil, se
    conserva solo la marca de desactivada; si no, borrar volvería a activarla por el opt-out.
11. **Viaje ajeno.** El proceso de recomendación no sabe de quién es un viaje: para otro usuario de la región, la
    lista de sugerencias de un viaje ajeno responde como uno sin sugerencias (`searchStatus: none`), sin revelar si
    existe. Un viaje de otra región da `404` en la puerta.
12. **Cubeta de fichas y ventana del proveedor.** Una cubeta llena del tamaño del límite más su recarga permite el
    doble del límite en un minuto. La cubeta usa la mitad del límite como capacidad y la otra mitad como recarga
    por minuto.
13. **Reservas sin viaje.** Una cancelación de una reserva sin asignar no genera sugerencias: la propuesta necesita
    un viaje donde quedar.
14. **Outbox enviada.** `ingestion-operations.md` pide vaciar el contenido de la outbox enviada a las 24 h, y el
    prototipo no lo hacía. Ahora la tarea diaria del núcleo lo hace (`PublicadorOutbox.limpiar_enviados`); sin eso,
    los eventos ya publicados conservaban el identificador de una cuenta eliminada.
15. **Cuenta eliminada con token vigente.** El token de acceso dura 15 minutos y la puerta no consulta al proveedor
    de identidad: la marca de cuenta eliminada del núcleo es la que corta el acceso en el momento, y también evita
    que el primer pedido vuelva a crear el perfil del usuario.

Correcciones de la auditoría independiente de la iteración 5 (detalle en el documento de la iteración):

16. **Cuenta eliminada y recomendación.** La API de recomendación también rechaza los tokens vigentes de una cuenta
    eliminada, y leer preferencias o sugerencias ya no crea un perfil.
17. **Recomendación desactivada.** Un hecho nuevo solo se descarta: ya no actualiza las métricas del perfil.
18. **Ajustar también entrena.** Cada sugerencia mostrada que un ajuste excluye es un rechazo débil (la mitad del
    peso), en el modelo del viajero y en el entrenamiento.
19. **Pasos del núcleo después del borrado.** Quitar permisos y seudonimizar la auditoría se hacen al consumir el
    propio `account.deleted.v1` (cola `core.accounts`): si algo falla, se reentrega. El seudónimo usa una clave
    propia, no la del HMAC del email.
20. **Sin orden por usuario en `recommendation.facts`.** Cada escritura revisa la marca de cuenta eliminada y un
    barrido periódico quita lo que un hecho procesado en paralelo haya dejado.
21. **QA-11 de punta a punta.** `suggestions.available.v1` lleva `cancellationCommittedAt` y el notificador mide
    hasta el push (`qa11_cancelacion_a_aviso_s`).
22. **Canario y caché.** El canario se evalúa cada 5 minutos en el ciclo; un resultado parcial ya no se guarda en la
    caché; una oferta vencida responde `409`; los enlaces de las ofertas se validan (https y dominio del
    proveedor); las sugerencias vencidas se borran a los 30 días.

Los hallazgos 1 y 3 se resolvieron en la iteración 5 (el 3, con la excepción declarada en `access-audit.md`); el
resto está registrado en el
[registro de impactos](../docs/01-add/impact-log.md).

## Revisión del PR #12

Cinco regresiones en `tests/test_revision_iteracion5.py`: presupuesto en otra moneda, recuperación de búsqueda
parcial sin duplicar y conservando rechazos, aceptación que termina la búsqueda, rollback que omite canarios
descartados y entrenamiento diario que conserva un canario sin muestra.

El precio relativo usa la mediana de las ofertas. La banda histórica de precios, anticipación y estadía típica
no están implementadas como características. El prototipo consulta en EUR y excluye ofertas en otra moneda
que el presupuesto explícito. El feedback se guarda inmediatamente; la publicación regional no tiene un plazo
garantizado de 24 horas. Las promociones nuevas guardan su predecesora en `historial_modelos_activos`; versiones
antiguas sin historial no permiten deducir una vuelta atrás segura.
