# Registro de impactos entre iteraciones

Este documento registra las decisiones que afectan elementos compartidos entre iteraciones y los acuerdos pendientes entre sus responsables.

## Impactos registrados por la iteración 1

| Fecha | Origen | Cambio o decisión | Afecta | Resolución | ADR |
|---|---|---|---|---|---|
| 2026-10-27 | 1 | La idempotencia, su clave y el tratamiento de mensajes desordenados quedan por diseñar. Los correos pueden no incluir una versión externa. | 2 | Resolver mediante decisiones del rango 0020–0039. | ADR-0002 |
| 2026-10-27 | 1 | La publicación confiable de cambios confirmados del núcleo, la cola de errores, los datos personales en mensajes y la tecnología del broker quedan pendientes. | 2 | Definir contratos y mecanismos, coordinando con el responsable del núcleo. | ADR-0002 |
| 2026-10-27 | 1 | La separación entre lectura y escritura dentro del núcleo no está decidida. | 3 | Evaluar su necesidad al diseñar para QA-2. | ADR-0001 |
| 2026-10-27 | 1 | La analítica queda separada como proceso, pero su almacenamiento todavía no está decidido. | 4 | Elegir almacenamiento y transferencia mediante una ADR del rango 0060–0079. Resuelto: ADR-0064. | ADR-0001 |
| 2026-10-27 | 1 | La puerta de entrada valida la identidad, pero el mecanismo concreto de autenticación sigue pendiente. | 4 | Diseñar el mecanismo con QA-7. El acceso delegado al correo se trata por separado en la iteración 2. Resuelto: ADR-0060. | ADR-0004 |
| 2026-10-27 | 1 | Las notificaciones externas pasan por la entrada global y la puerta de entrada regional antes de llegar a la ingesta. Puede desconocerse la región de la reserva notificada. | 2 | Definir cómo identificar la región de origen sin confiar en datos de enrutamiento no verificados. | ADR-0003 y ADR-0004 |
| 2026-10-27 | 1 | El almacenamiento propio de ingesta no está definido. | 2 | Definir persistencia de cursores, resultados, autorizaciones y publicaciones pendientes, aclarando la propiedad de cada dato. | ADR-0001 |
| 2026-10-27 | 1 | RF-06, integración con la agencia de viajes preferida, se asigna a la iteración 2. | 2 | Incorporar su diseño como integración externa y acordar su relación con el núcleo. | Plan de iteraciones |

## Elementos compartidos conocidos

| Elemento | Definido inicialmente en | Regla de cambio |
|---|---|---|
| Modelo de datos de reservas | Iteración 1 | Cambios con revisión de los responsables de las iteraciones afectadas. |
| Modelo canónico de reserva | Iteración 1; refinamiento en 2 y 3 | Acordar campos, identidad y tratamiento de datos incompletos. |
| Broker y temas de mensajes | Iteración 1 | La iteración 2 define detalles sin alterar silenciosamente productores y consumidores. |
| Contratos de `specs/` | Iteración que los crea | Revisar cambios con productores y consumidores antes de implementar. |
| Clave de partición por usuario y región de origen | Iteración 1 | Cambios con revisión cruzada, especialmente de las iteraciones 2, 3 y 4. |
| Módulos del núcleo | Iteración 1 | Cambios con aviso y revisión de sus consumidores. |
| Puerta de entrada y entrada global | Iteración 1 | Coordinar cambios entre las iteraciones 2, 3 y 4. |

## Refinamiento de iteración 2 — estado al 2026-10-28

Los impactos de origen conservan su fecha y contexto. La siguiente tabla expresa el estado documental actual;
"Propuesto para revisión" significa que existe decisión concreta, sin atribuir aceptación conjunta.

| Tema | Resolución documental actual | Estado |
|---|---|---|
| Numeración | Despliegue ADR-0003 y puerta de entrada ADR-0004; referencias corregidas | Actualizado |
| Entrada de avisos | Entrada global, Gateway y receptor interno; ADR-0025 | Propuesto para revisión |
| Identificación de región | Directorio mínimo de suscripción y vigencia; ADR-0025 y contrato regional | Propuesto para revisión |
| Correo sin versión | Versión externa opcional; datos insuficientes van a resolución | Propuesto para revisión |
| Identidad | eventId, identidad de reserva y versión de esquema separados en contrato | Propuesto para revisión |
| Desorden | Núcleo compara versión si existe y conserva conflictos o cancelaciones pendientes | Propuesto para revisión con 3 |
| Vinculaciones | Núcleo es autoridad; ingesta conserva cursor, suscripción y estado técnico | Propuesto para revisión con 3 |
| Agencia | Módulo de asistencia saliente del núcleo con trabajador acotado; ADR-0026 | Propuesto para revisión con 3 |
| Eventos confirmados | Outbox transaccional del núcleo y contrato; ADR-0027 | Propuesto para revisión con 3 |
| Analítica | Flujo de cambios confirmados disponible; almacenamiento sigue en iteración 4 | Delimitado; diseño de almacén fuera de 2 |
| Broker | RabbitMQ, topología y políticas; ADR-0028 | Propuesto para revisión |

## Impactos que requieren coordinación

| Origen | Cambio | Afecta | Tratamiento | Estado |
|---|---|---|---|---|
| 2, ADR-0028 | Tres miembros del broker en tres zonas por región | 1 y 3 | Refina el mínimo general de al menos dos zonas de ADR-0003; no lo contradice. No modifica despliegue de otros elementos ni agrega recuperación regional | Aceptado por 3 (2026-10-28, merge del PR #4) |
| 2, ADR-0026 | Asistencia pertenece al núcleo; ingesta conserva función entrante | 1 y 3 | Módulo con trabajador acotado y contrato separado; medir competencia por recursos. Ante sobrecarga, la asistencia es prioridad baja (ADR-0047) | Aceptado por 3 (2026-10-28, merge del PR #4) |
| 2, ADR-0020 | Avisos de correo principales y reconciliación por cuotas | 1, 3 y QA-1/5 | Modelo de consultas y renovaciones documentado. Perfil lento incumple cinco minutos al perder avisos | Viabilidad universal de QA-1 abierta |
| 2, ADR-0024/0027 | Outboxes distintas, control de entrada y resultado atómicos | 3 y 4 | Implementar contratos sin compartir tablas | Propuesto para revisión |
| 2, ADR-0021 | Autoridad y barrera de revocación | 3 y 4 | Aplicar protocolo de autorización y probar carreras | Propuesto para revisión |
| 2, ADR-0028 | Consumo por usuario y presupuesto de aplicación y cliente | 3 | La iteración 3 mantiene 8 shards con un consumidor activo cada uno (no escala con el núcleo, ADR-0043); cada novedad se aplica en una transacción de la partición del usuario, así que shards y particiones no necesitan alinearse (ADR-0042); acepta 40 s de espera, 30 s de aplicación y 30 s de cliente | Coordinado (2026-10-28) |
| 2, ADR-0023 | QA-9 se evalúa incorporando trenes | 3 y 4 | Registrar esfuerzo ≤10 días-persona y verificar medios existentes sin cambios. La iteración 4 usa un medio que no existe (ferry), porque `train` ya está en el vocabulario, y agrega esquemas de detalles por tipo (ADR-0066) | Validación pendiente |

## Impactos de la iteración 3

| Fecha | Origen | Cambio o decisión | Afecta | Tratamiento | Estado |
|---|---|---|---|---|---|
| 2026-10-28 | 3 | QA-1 a escala con avisos perdidos (conflicto abierto de la iteración 2) se registra como riesgo aceptado | 2 | Mitigación posible: detectar buzones sin avisos y adelantar su reconciliación; iteración 5 si hay tiempo | Riesgo aceptado por ambos (2026-10-28) |
| 2026-10-28 | 3, ADR-0044 y 0048 | El núcleo consume `booking.change.detected.v1` sin cambios al contrato, con dueño por campo, marca de borrado y asignación a viajes por fechas; sin fechas, la reserva queda `pendiente` de asignación | 1 y 2 | Usa los campos ya definidos (`tripId`, fechas y versión de la fuente opcionales). Coincide con la regla de la iteración 1 de dejar pendiente lo que no se puede asociar | Compatible |
| 2026-10-28 | 3, ADR-0046 | El núcleo publica `panel.changed.v1` en `travel.domain`; el notificador lo consume con una cola exclusiva por instancia y una cola compartida `notifier.push`. No cambia `booking.changed.v1` | 2 | Nuevas colas en la topología de ADR-0028 | Aceptado por ambos (2026-10-28) |
| 2026-10-28 | 3, ADR-0045 y 0048 | Nuevo evento `trip.changed.v1` en el exchange `travel.domain` | 2 y 4 | Publicado desde la outbox del núcleo (ADR-0027); la analítica lo consume en la iteración 4 | Aceptado por ambos (2026-10-28) |
| 2026-10-28 | 3, ADR-0042 | La zona C del broker también aloja una instancia del monitor de base y las réplicas de la base que se reconstruyen si cae una zona | 2 | Comparten zona, no recursos | Aceptado por ambos (2026-10-28) |
| 2026-10-28 | 3, ADR-0043 | Se agrega CON-5 (startup con recursos limitados) a las restricciones | 1, 2 y 4 | Restricción de negocio, en estado de suposición | Aceptado por ambos (2026-10-28) |
| 2026-10-28 | 3, ADR-0040 | La transacción del núcleo incluye además el documento del panel | 2 | No cambia el contrato; la etapa "aplicación" (30 s) incluye actualizar el panel | Compatible |
| 2026-10-28 | 3, ADR-0042 | Todo lo de un usuario vive en su partición; ninguna transacción cruza particiones | 4 | La lectura de un itinerario compartido se hace en la partición del dueño del viaje | Resuelto en la iteración 4 (ADR-0061, ADR-0062) |
| 2026-10-28 | 3, ADR-0045 | Los viajes archivados se eliminan al año | 4 | La analítica decide cómo anonimizar los eventos que ya recibió | Resuelto en la iteración 4: anonimización al entrar con clave anual (ADR-0064) |
| 2026-10-28 | 3 | `bearerAuth` y la autenticación de la conexión SSE quedan genéricas en la API | 4 | Se definen con QA-7 | Resuelto en la iteración 4: token de 15 min y ticket SSE (ADR-0060) |
| 2026-10-28 | 3, ADR-0046 | Colas del notificador: las de avisos por instancia son *classic*, exclusivas y temporales (única excepción a las colas quorum); `notifier.push` es quorum y durable | 2 | Agregado a `specs/ingestion-operations.md` a pedido de Tomas Lateana (revisión cruzada) | Aceptado por ambos (2026-10-28) |

## Impactos de la iteración 4

| Fecha | Origen | Cambio o decisión | Afecta | Tratamiento | Estado |
|---|---|---|---|---|---|
| 2026-10-28 | 4, ADR-0060 | La entrada global usa `homeRegion` del token para enrutar y un directorio global `hash(email) → región` para el login | 1 | Refina ADR-0003 y ADR-0004 sin cambiarlas; el directorio sigue el criterio del de suscripciones (ADR-0025) | Propuesto para revisión |
| 2026-10-28 | 4, ADR-0062 | La puerta de entrada reenvía por mTLS a otra región los recursos con su prefijo; los identificadores de viajes e invitaciones llevan la región del dueño | 1 y 3 | Nuevo conector entre regiones; no se copian datos | Propuesto para revisión |
| 2026-10-28 | 4, ADR-0066 | `booking.change.detected.v1` pasa a 0.2.0: tipo abierto, `arrivalLocation` y `details` según `specs/schemas/` | 2 | Contrato de diseño 0.x sin consumidores en producción; los adaptadores producen `details` y el núcleo lo valida | Propuesto para revisión con 2 |
| 2026-10-28 | 4, ADR-0064 | El núcleo publica `booking.facts.v1` desde su outbox; la analítica consume además `trip.changed.v1`. `booking.changed.v1` queda sin consumidores en la primera entrega | 2 y 3 | Nueva cola quorum de la analítica en `travel.domain` (ADR-0028) | Propuesto para revisión |
| 2026-10-28 | 4, ADR-0067 | Además del `correlationId`, los mensajes llevan el contexto de traza (`traceparent`) en sus encabezados | 2 y 3 | Todos los productores y consumidores propagan el contexto con la biblioteca `observabilidad` | Propuesto para revisión con 2 |
| 2026-10-28 | 4, ADR-0045 | ADR-0045 remitía a la iteración 4 la anonimización de los eventos de viajes eliminados | 3 | Nota agregada en ADR-0045 que remite a ADR-0064 | Compatible |
| 2026-10-28 | 4, ADR-0064 | **Segunda entrega (opción A, recomendación):** el almacén analítico no tiene datos por usuario | 2da entrega | Un sistema de recomendación tendrá que guardar su propio perfil resumido por usuario (métricas comprimidas), calculado desde los datos operativos, en la región del usuario y eliminado junto con su cuenta | Para la segunda entrega |

## Criterio para resolver un impacto

1. Identificar documentos, contratos y responsables afectados.
2. Registrar la propuesta y su justificación.
3. Revisar con el otro integrante mediante el PR antes del merge.
4. Actualizar vistas, contratos y ADR afectados.
5. Registrar aceptación real y evidencia de las pruebas cuando existan.

El paso 7 contiene análisis de escenarios. La implementación y el cumplimiento medido quedan diferenciados del
estado documental. QA-1 a escala permanece abierto hasta resolver la recuperación dentro del presupuesto a escala.
