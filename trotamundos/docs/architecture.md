# Arquitectura de Trotamundos — documento central

**Mantienen:** Tadeo Brun y Tomas Lateana.

**Estado:** iteraciones 1 a 4 integradas en main; decisiones adoptadas documentalmente. Cierre de primera entrega arquitectónica registrado; implementación, mediciones y riesgos abiertos detallados en docs/04-evaluation/first-delivery-review.md.

Este documento resume la arquitectura y enlaza al detalle de requisitos, iteraciones, decisiones, vistas y contratos.

## 1. Introducción

Trotamundos es un panel de gestión de viajes para web y dispositivos móviles. Reúne las reservas de un viajero y las organiza por viaje, evitando que deba consultar múltiples aplicaciones y correos.

Las reservas pueden incorporarse desde correos autorizados, integraciones con proveedores externos y carga manual.

El diseño contempla 15 millones de cuentas, 2 millones de usuarios activos semanales y picos de tráfico. Estas cifras son objetivos del sistema; no representan capacidad demostrada por el prototipo.

| Iteración | Estado | Aporte |
|---|---|---|
| [1 — Estructura general](01-add/iteration-1-structure.md) | Diseño integrado; ADRs aceptadas | Arquitectura de referencia, núcleo modular, ingesta separada, mensajería y despliegue regional. |
| [2 — Ingesta](01-add/iteration-2-ingestion.md) | Diseño integrado; QA-1 a escala y validación pendientes | Obtención autorizada de novedades, adaptadores, procesamiento, publicación durable y contrato propuesto. |
| [3 — Consulta y escala](01-add/iteration-3-query-scale.md) | Pasos 2–7 documentados; decisiones confirmadas por ambos | Modelo de lectura del panel, caché local y notificador, particiones por usuario, escalado y degradación, aplicación de novedades y archivado. |
| [4 — Seguridad y evolución](01-add/iteration-4-security-evolvability.md) | Pasos 2–7 documentados y auditados; decisiones de ambos integrantes | Identidad por región, compartición con cuenta y auditoría, lectura entre regiones, tarjeta para redes, analítica regional seudonimizada, internacionalización en el cliente, detalles por tipo de reserva y observabilidad. |

La incorporación de al menos un módulo avanzado —recomendaciones o chatbot— es obligatoria para la segunda entrega. Su elección continúa pendiente.

## 2. Contexto y alcance

Ver el [diagrama de contexto](00-requirements/context-diagram.md).

### Responsabilidades principales

- Consultar reservas organizadas por viaje desde web y móvil.
- Incorporar reservas desde correos autorizados.
- Aplicar filtros y listas de remitentes seguros.
- Obtener detalles, actualizaciones y cancelaciones desde proveedores.
- Permitir agregar, actualizar y eliminar reservas manualmente.
- Gestionar el ciclo de vida y archivado de viajes.
- Integrarse con la agencia preferida para facilitar asistencia.
- Compartir itinerarios con personas designadas.
- Proporcionar datos para análisis.

La compra, emisión y pago de reservas no se incluyen en el alcance inicial propuesto.

Obtener información sobre una cancelación no equivale a ejecutar una cancelación ante el proveedor.

## 3. Entradas del diseño

| Entrada | Documento |
|---|---|
| Requerimientos funcionales | [functional-rqmts.md](00-requirements/functional-rqmts.md) |
| Escenarios de calidad | [quality-attribute-scenarios.md](00-requirements/quality-attribute-scenarios.md) |
| Árbol de utilidad | [utility-tree.md](00-requirements/utility-tree.md) |
| Restricciones y concerns | [constraints-concerns.md](00-requirements/constraints-concerns.md) |
| Drivers arquitectónicos | [architectural-drivers.md](00-requirements/architectural-drivers.md) |

Los percentiles, el pico de tráfico 5× y otras medidas identificadas como supuestos deben validarse. No se presentan como valores textuales de la consigna.

CON-3, relacionada con políticas regionales de datos, continúa como suposición a validar.

Las modificaciones de entradas compartidas deben revisarse entre ambos integrantes y registrarse.

## 4. Modelo de dominio

Ver [domain-model.md](02-views/domain-model.md).

Los conceptos principales son usuario, viaje, reserva, cuenta vinculada, proveedor y compartición.

El núcleo administra el estado oficial de viajes y reservas. La ingesta interpreta información externa, pero no decide unilateralmente la asociación de una reserva con un viaje.

La identificación de reservas externas, su conciliación entre correo y API y el tratamiento de casos incompletos se refinan entre las iteraciones 2 y 3.

## 5. Organización general

La arquitectura separa tres clases de trabajo:

| Elemento | Responsabilidad |
|---|---|
| Núcleo modular | Consultar y gestionar viajes, reservas, usuarios y permisos. Es el único dueño del estado oficial. |
| Ingesta | Obtener información externa autorizada, normalizarla y publicar novedades. |
| Analítica | Ejecutar procesamiento analítico separado de las operaciones habituales, con un almacén por región y los datos seudonimizados al entrar ([ADR-0064](03-adr/0064-analitica-regional-seudonimizada.md)). |

El núcleo es inicialmente un único desplegable con módulos internos.

La iteración 3 separa la lectura del panel con un modelo de lectura por usuario dentro de la misma base, actualizado en la misma transacción que cada cambio ([ADR-0040](03-adr/0040-modelo-de-lectura-del-panel.md)).

Ver la [vista de módulos](02-views/module-view.md).

## 6. Elementos de ejecución y conectores

Ver la [vista de componentes y conectores](02-views/cc-view.md).

| Elemento | Responsabilidad |
|---|---|
| Aplicación web y app móvil | Presentar viajes y permitir las operaciones del usuario. |
| Entrada global | Enrutar hacia la región de origen correspondiente. |
| Puerta de entrada regional | Recibir tráfico externo, validar su origen o identidad según corresponda, limitar tráfico y dirigir solicitudes. |
| Núcleo | Aplicar reglas y permisos, consultar datos y confirmar modificaciones. |
| Ingesta | Sondear correos, consultar APIs y procesar notificaciones externas. |
| Intermediario persistente | Conservar y entregar mensajes entre productores y consumidores. |
| Base operativa | Conservar los datos oficiales de los usuarios de la región, en particiones por usuario con réplica sincrónica (ADR-0042). |
| Notificador | Avisar a las apps que su panel cambió, por SSE o push (ADR-0046). |
| Analítica | Consumir cambios confirmados para preparar análisis. |

### Dos flujos de mensajes

| Flujo | Productor | Consumidor | Significado |
|---|---|---|---|
| Novedad externa detectada | Ingesta | Núcleo | Información externa que debe validarse y evaluarse. |
| Cambio confirmado | Núcleo | Analítica y otros consumidores autorizados | Modificación ya confirmada sobre el estado oficial. |

El núcleo publica cambios confirmados provenientes tanto de la ingesta como de operaciones manuales.

La ingesta no escribe directamente en las tablas operativas del núcleo.

Una confirmación de recepción del intermediario no equivale a la aplicación de una reserva.

## 7. Despliegue regional

Ver la [vista de despliegue](02-views/deployment-view.md).

La propuesta de la primera iteración establece:

- Región de origen por usuario.
- Procesos y mensajería distribuidos entre varias zonas dentro de cada región.
- Base primaria y réplica sincrónica en otra zona.
- Entrada global y puertas de entrada regionales redundantes.
- Partición de los datos según usuario y región de origen.

La región de origen no se obtiene de la ubicación momentánea del viajero.

### Límites pendientes

- Atender desde la región de origen no garantiza atender desde la región físicamente más cercana.
- El comportamiento para usuarios que viajan se refina en las iteraciones 3 y 4: se los atiende desde su región de
  origen y la app formatea en su idioma y en la zona horaria de cada reserva (ADR-0065).
- La compartición entre regiones se lee de forma remota en la región del dueño, sin persistir una réplica en la puerta del lector; la respuesta sí transita entre regiones (ADR-0062).
- La identificación de la región correspondiente a una notificación externa se resuelve en la iteración 2.
- La recuperación ante caída de una región completa no está diseñada en esta base.
- No se afirma cumplimiento de políticas regionales de datos sin definir y validar sus criterios.

Los tiempos de detección y redirección agregados a QA-4 son supuestos de diseño a validar. No sustituyen el límite de cinco minutos mensuales de inactividad no planificada.

## 8. Refinamiento propuesto de ingesta

Ver [iteration-2-ingestion.md](01-add/iteration-2-ingestion.md).

### Componentes

- Planificador de sincronización.
- Coordinador de consultas.
- Gestor de vinculaciones.
- Adaptadores de acceso.
- Receptor de notificaciones.
- Procesador de selección, extracción, normalización y validación.
- Registro de sincronización.
- Publicador de novedades.

Son componentes lógicos de la ingesta, no microservicios obligatoriamente independientes.

| Artefacto | Documento |
|---|---|
| Componentes y conectores detallados | [ingestion-view.md](02-views/ingestion-view.md) |
| Secuencias de procesamiento y recuperación | [ingestion-sequences.md](02-views/ingestion-sequences.md) |
| Semántica del intercambio | [ingestion-contract.md](../specs/ingestion-contract.md) |
| AsyncAPI propuesto | [booking-change-detected.v1.yaml](../specs/asyncapi/booking-change-detected.v1.yaml) |

### Alineación documental de ingesta

Se actualizaron receptor por Gateway, referencias ADR-0003/0004, versión externa opcional, propiedad de
vinculaciones, asistencia de agencia y publicación confirmada. Ver ADR-0020 a 0028 y contratos de ingesta.
Son decisiones propuestas; broker y parámetros se definen en ADR-0028 y el paso 7 está analizado; ejecución del prototipo pendiente.


## 9. Interfaces y secuencias

Ver [interfaces.md](02-views/interfaces.md) y [specs/](../specs/).

Los contratos usados por ambas iteraciones deben revisarse entre productor y consumidor antes de implementar.

El contrato de novedades debe distinguir:

- Identificador del evento.
- Identidad de la reserva.
- Identidad del cambio.
- Versión del esquema.
- Versión externa, cuando exista.

No debe inventar referencias o versiones ausentes.

Ver también las [secuencias generales](02-views/sequence-views.md) y las [secuencias de ingesta](02-views/ingestion-sequences.md).

Los archivos `*.example.yaml` son ejemplos de formato y no demuestran que una interfaz esté implementada.

## 10. Decisiones arquitectónicas

Ver el [índice completo de ADRs](03-adr/README.md).

### Primera iteración

| ADR | Decisión | Estado |
|---|---|---|
| [0001](03-adr/0001-nucleo-modular-con-procesos-separados.md) | Núcleo modular con ingesta y analítica separadas. | accepted |
| [0002](03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) | Comunicación asincrónica con publicación y suscripción. | accepted |
| [0003](03-adr/0003-despliegue-por-regiones-con-region-de-origen.md) | Despliegue regional con región de origen por usuario. | accepted |
| [0004](03-adr/0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) | Clientes ricos y puerta de entrada única por región. | accepted |

### Segunda iteración

| ADR | Decisión adoptada | Estado |
|---|---|---|
| [0020](03-adr/0020-obtener-novedades.md) | Avisos principales y reconciliación adaptable de correo. | accepted |
| [0021](03-adr/0021-autorizacion-correo.md) | Autorización delegada del correo y mínimo privilegio. | accepted |
| [0022](03-adr/0022-tuberia-ingesta.md) | Procesamiento mediante etapas internas. | accepted |
| [0023](03-adr/0023-adaptadores-proveedores.md) | Adaptadores para contratos y formatos externos. | accepted |
| [0024](03-adr/0024-avance-y-publicacion-durable.md) | Avance de sincronización y publicación durable coordinados. | accepted |
| [0025](03-adr/0025-enrutamiento-de-avisos.md) | Directorio mínimo y enrutamiento regional. | accepted |
| [0026](03-adr/0026-integracion-agencia.md) | Asistencia saliente del núcleo. | accepted |
| [0027](03-adr/0027-publicacion-del-nucleo.md) | Outbox de cambios confirmados del núcleo. | accepted |
| [0028](03-adr/0028-rabbitmq-y-politicas.md) | RabbitMQ con colas quorum y políticas. | accepted |

### Tercera iteración

| ADR | Decisión adoptada | Estado |
|---|---|---|
| [0040](03-adr/0040-modelo-de-lectura-del-panel.md) | Modelo de lectura del panel por usuario, actualizado en la misma transacción. | accepted |
| [0041](03-adr/0041-cache-local-del-panel.md) | Caché local del panel en la app, revalidada por versión. | accepted |
| [0042](03-adr/0042-particion-de-la-base-por-usuario.md) | Partición de la base por usuario en varios nodos con réplica sincrónica. | accepted |
| [0043](03-adr/0043-escalado-solo-reactivo.md) | Escalado automático solo reactivo. | accepted |
| [0044](03-adr/0044-novedades-y-cambios-manuales.md) | Novedades y cambios manuales: dueño por campo y marca de borrado. | accepted |
| [0045](03-adr/0045-ciclo-de-vida-y-archivado-de-viajes.md) | Archivado diario, reactivación y eliminación al año. | accepted |
| [0046](03-adr/0046-notificador-de-cambios-del-panel.md) | Notificador separado con evento propio y cola por instancia. | accepted |
| [0047](03-adr/0047-priorizacion-y-degradacion-ante-sobrecarga.md) | Priorización y degradación ante sobrecarga. | accepted |
| [0048](03-adr/0048-asignacion-de-reservas-a-viajes.md) | Asignación automática de reservas a viajes por fechas. | accepted |

### Cuarta iteración

| ADR | Decisión adoptada | Estado |
|---|---|---|
| [0060](03-adr/0060-identidad-por-region-con-tokens.md) | Proveedor de identidad por región y tokens de vida corta; directorio global mínimo; ticket SSE. | accepted |
| [0061](03-adr/0061-comparticion-con-cuenta-y-auditoria.md) | Compartición con personas designadas con cuenta, control en el núcleo y auditoría. | accepted |
| [0062](03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md) | Lectura remota de viajes compartidos en la región del dueño. | accepted |
| [0063](03-adr/0063-tarjeta-de-resumen-para-redes-sociales.md) | Tarjeta de resumen pública para redes sociales. | accepted |
| [0064](03-adr/0064-analitica-regional-seudonimizada.md) | Almacenes analíticos regionales con seudonimización al entrar. | accepted |
| [0065](03-adr/0065-internacionalizacion-en-el-cliente.md) | Catálogos de textos remotos, datos neutros del backend y formato en el cliente. | accepted |
| [0066](03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) | Campos comunes y detalles con esquema propio por tipo de reserva. | accepted |
| [0067](03-adr/0067-observabilidad-con-trazas-y-metricas.md) | Trazas distribuidas, métricas por etapa y logs estructurados. | accepted |

Las decisiones de la segunda, la tercera y la cuarta iteración se revisan conjuntamente antes de aceptarse.

## 11. Trazabilidad inicial

| Driver | Iteraciones | Decisiones relacionadas | Validación pendiente |
|---|---|---|---|
| QA-1 | 1, 2, 3 y 4 | 0001, 0002, 0020, 0024, 0040, 0044, 0046, 0067 | Tiempo completo desde generación externa hasta visualización, medido por etapa con trazas. |
| QA-2 y QA-3 | 3 | 0040, 0041, 0043, 0047 | Prueba de carga del panel y primer contenido móvil con caché. |
| QA-4 | 1, 3 y 4 | 0001, 0002, 0003, 0004, 0042, 0047, 0067 | Conmutación de nodos e instancias; presupuesto mensual medido con métricas. |
| QA-5 | 1 y 3 | 0001, 0003, 0004, 0042, 0043 | Umbral de escalado reactivo y particiones ante picos. |
| QA-6 | 2 y 3 | 0022, 0023, 0024, 0044 | Normalización, duplicaciones, desorden, conciliación y marcas de borrado. |
| RF-04 y RF-05 | 3 | 0040, 0044, 0045, 0048 | Conflictos con cambios manuales, asignación a viajes, archivado y reactivación. |
| QA-8 | 2 | 0021 | Autorización, renovación, revocación y datos conservados. |
| QA-9 | 1, 2 y 4 | 0001, 0002, 0023, 0066 | Agregar un medio nuevo (ferry) al prototipo y registrar el esfuerzo. |
| QA-7 y RF-08 | 4, sobre la base de 1 | 0004, 0060, 0061, 0062, 0063 | Designado, no designado, revocado y enlace reenviado; auditoría de cada intento. |
| QA-10 | 1, 3 y 4 | 0003, 0040, 0065 | Dos idiomas y zonas horarias sobre el mismo panel; latencia de QA-2 desde lejos de la región (parcial). |
| CRN-2 | 4 | 0067 | Propagación del contexto a través del broker. |
| RF-06 | 2, implementación coordinada con 3 | 0026: asistencia saliente del núcleo | Solicitud de asistencia a la agencia preferida. |
| RF-07 | 1 y 4 | 0001, 0064 | Consultas del equipo de datos y seudonimización. |

Esta tabla expresa relaciones de diseño, no resultados de pruebas.

## 12. Riesgos y deuda arquitectónica

| Riesgo | Tratamiento pendiente | Responsable |
|---|---|---|
| Sondear muchos buzones puede exceder el presupuesto de frescura o las cuotas externas. | Planificación, consultas incrementales, avisos cuando existan y medición. | Iteración 2 |
| Un correo puede no incluir versión o referencia suficiente. | Separar incorporación automática segura de conciliación o resolución pendiente. | Iteraciones 2 y 3 |
| Novedades duplicadas o desordenadas pueden alterar incorrectamente una reserva. | Idempotencia y reglas de aplicación, sin depender únicamente del orden del intermediario. | Iteraciones 2 y 3 |
| Una notificación externa puede no indicar usuario ni región. | Resolver y verificar su vinculación antes del enrutamiento. | Iteración 2 |
| La caída de una zona puede consumir el presupuesto mensual. | *Ping/echo* y conmutación de nodos de la base en 30 s y 60 s (ADR-0042); falta medirlos. Ventana con una sola copia hasta reconstruir la réplica. | Iteración 3 (diseñado) |
| La caída de una región completa no tiene recuperación diseñada. | Riesgo aceptado: no está en el estímulo de QA-4; las particiones acotan a quiénes afecta. | Aceptado |
| QA-1 a escala: avisos perdidos con reconciliación lenta. | Riesgo aceptado en la iteración 3; mitigación candidata para la iteración 5. | Aceptado |
| Escalón de carga mayor a 1,67 veces durante el arranque de instancias. | Escalado temprano y priorización; QA-2 puede incumplirse en esos minutos; escalado programado solo si la operación muestra picos regulares (CON-5). | Iteración 3 (aceptado) |
| Región de origen y región más cercana pueden diferir. | Se atiende desde la región de origen (latencia aceptada en la iteración 3); la compartición entre regiones suma la red entre regiones (ADR-0062). | Iteraciones 3 y 4 (aceptado) |
| Un cambio confirmado puede no publicarse si el proceso falla. | Persistencia y publicación recuperable coordinadas. | Iteraciones 2 y 3 |
| Dos componentes pueden mantener estados contradictorios de una autorización. | Definir fuente autoritativa y coordinación de revocación. | Iteraciones 2 y 3 |
| Los análisis pueden competir por recursos con las operaciones. | Almacén analítico propio por región, alimentado por eventos (ADR-0064). | Iteración 4 (diseñado) |
| Un token de acceso robado sirve hasta 15 minutos. | Vida corta y revocación del token de renovación (ADR-0060). | Iteración 4 (aceptado) |
| Una primera solicitud desde muy lejos de la región de origen puede superar los 800 ms de QA-2. | Se cumple con la conexión abierta; mitigación candidata: TLS en la entrada global cerca del usuario. | Iteración 4 (aceptado), candidata para la 5 |
| Si falla la auditoría, se rechazan las lecturas de viajes compartidos. | QA-7 exige el 100 %; auditoría replicada en dos zonas (ADR-0061). | Iteración 4 (aceptado) |
| Retención de hechos seudonimizados tras eliminar una cuenta o viaje, y cobertura de hechos tardíos sin clave. | Validar retención y riesgo de reidentificación; aplicar protocolo idempotente y período de commit (ADR-0064). | Iteración 4 (validación pendiente) |
| CON-3 carece de un criterio concreto validado. | Precisar la política regional de datos y sus consecuencias. | Ambos integrantes |

## 13. Prototipo y evidencia

Ver [prototype/README.md](../prototype/README.md).

El prototipo debe demostrar recorridos acotados y trazables a contratos y decisiones. Los objetivos incluyen:

- Incorporar una novedad externa y consultar su resultado.
- Tolerar reentregas sin duplicar efectos.
- Recuperar publicación pendiente tras una caída.
- Verificar autorización y revocación del correo.
- Mantener consultas mientras la ingesta está detenida.
- Leer el panel por clave y revalidarlo por versión (`304`).
- Avisar un cambio por SSE desde la instancia del notificador que tiene la conexión.
- Aplicar dueño por campo, marca de borrado y asignación a viajes.
- Archivar y reactivar viajes con una fecha simulada.

Son objetivos de validación, no pruebas ejecutadas.

Una ejecución local no demuestra capacidad para millones de usuarios, independencia real entre zonas ni disponibilidad global mensual.

El plazo del trabajo práctico y los recursos del grupo acotan el prototipo; no se utilizan como justificación de las decisiones de la arquitectura objetivo.

## 14. Coordinación y revisión

Los impactos se registran en [impact-log.md](01-add/impact-log.md).

Como seguimiento de implementación y validación de la segunda iteración, deben verificarse:

- Su alineación con la primera iteración actualizada.
- El contrato ingesta-núcleo.
- La propiedad de datos y autorizaciones.
- La integración con la agencia.
- Las garantías y límites de publicación.
- Los riesgos y criterios de evaluación del paso 7.

Los aportes y revisiones reales se registran en [TEAM-LOG.md](../TEAM-LOG.md). La asistencia de IA se documenta en [ai/prompts.md](../ai/prompts.md).

## Actualización documental de alineación

La revisión incorpora los acuerdos de la primera iteración sin decidir perfiles de lectura/escritura, almacén
analítico ni recuperación regional. El contrato de correo ya no exige versión externa para toda incorporación.
Agencia, enrutamiento y outbox del núcleo tienen contratos semánticos propuestos. RabbitMQ y el paso 7 se completan en ADR-0028; pruebas de carga/seguridad siguen pendientes, sin afirmar implementación o cumplimiento de QAs.

## Cierre de diseño de la iteración 2

Pasos 2 a 7 documentados, con RabbitMQ, políticas operativas y recorrido analítico de escenarios. Ver
[ADR-0028](03-adr/0028-rabbitmq-y-politicas.md), [políticas](../specs/ingestion-operations.md),
[autorización](../specs/ingestion-authorization.md) y [validación futura](../prototype/ingestion-validation.md).
Las ADR reflejan adopción documental por integración en main; el prototipo no tiene resultados ejecutados.

## Refinamiento posterior a revisión de iteración 2

El correo usa avisos como vía principal y sondeo incremental para reconciliación. Las políticas calculan consultas
y renovaciones además de novedades: el perfil adaptable no garantiza QA-1 si se pierde un aviso en cuentas de baja
frecuencia. Asistencia es un módulo saliente del núcleo, fuera de ingesta. El broker objetivo usa tres miembros en
tres zonas; esto refina el mínimo general de ADR-0003. Ver el estado actual en [impactos](01-add/impact-log.md).

## Diseño de la iteración 3

El panel se lee por clave desde un documento por usuario que se actualiza en la misma transacción que cada cambio
(ADR-0040). La app muestra su copia local al abrir y la revalida con la versión (ADR-0041). Un notificador separado
consume el evento `panel.changed.v1`, con una cola por instancia, y avisa por SSE o push (ADR-0046). La base de cada
región se divide en particiones por usuario repartidas en nodos, cada uno con réplica sincrónica en otra zona y un
monitor en tres zonas (ADR-0042). El escalado es solo reactivo, sin capacidad reservada por calendario (ADR-0043, con
la restricción CON-5), y ante sobrecarga se prioriza el panel (ADR-0047). El núcleo resuelve los conflictos entre
novedades y cambios manuales con dueño por campo y marcas de borrado (ADR-0044) y asigna las reservas a viajes por
fechas (ADR-0048); una tarea diaria archiva los viajes completos, permite reactivarlos y elimina los archivados al
año (ADR-0045). Ver [iteración 3](01-add/iteration-3-query-scale.md).

## Diseño de la iteración 4

Cada región tiene su proveedor de identidad (OpenID Connect) y un directorio global mínimo traduce el HMAC del email,
calculado por la entrada global, a la región para el login; la puerta de entrada valida tokens de 15 minutos sin
consultar al proveedor y la conexión SSE se abre con un ticket firmado (ADR-0060). Un viaje se comparte con personas
que tienen cuenta: el dueño invita por email, solo una cuenta con ese email puede aceptar y el permiso queda atado a
ella; todo pedido sobre un viaje ajeno pasa por el módulo `comparticion`, y cada intento, permitido o rechazado, queda
registrado antes de responder, por el núcleo o por la puerta de entrada (ADR-0061). Si la persona es de otra región,
la puerta de entrada reenvía la solicitud a la región del dueño por un canal mTLS y la respuesta autorizada transita sin persistirse en las puertas (ADR-0062).
En redes sociales se publica una tarjeta de resumen que no da acceso al itinerario (ADR-0063). La analítica tiene un
almacén por región, alimentado por el evento `booking.facts.v1` y seudonimizado al entrar con una clave que se destruye
cada año (ADR-0064). El backend devuelve datos neutros y los clientes formatean con catálogos de textos remotos
(ADR-0065); QA-2 fuera de la región queda en riesgo para conexiones nuevas desde muy lejos. Las reservas tienen campos
comunes y un bloque de detalles con esquema propio por tipo, para agregar medios sin tocar el núcleo (ADR-0066). Todos
los procesos envían trazas, métricas y logs a un colector por región, con el `correlationId` de punta a punta hasta la
app (ADR-0067). Ver [iteración 4](01-add/iteration-4-security-evolvability.md).

## Correcciones integradas de revisión de iteración 4

El principal es regional y los tokens tienen validación completa de emisor, audiencia, tipo y vigencia (ADR-0060).
La vista compartida omite details; su respuesta transita a la región del lector sin persistencia en las puertas,
con Cache-Control no-store. Eliminar un marcador se ejecuta siempre en la región del lector (ADR-0062).
La analítica aplica recepción idempotente y códigos por período de committedAt; no se afirma anonimato por destruir
claves. Ver [procesamiento](../specs/analytics-processing.md). La auditoría cubre también rechazos sin token a rutas
del dueño; [medición de calidad](../specs/quality-measurement.md) separa tiempo de caída de tasa de éxito y declara
telemetría faltante. Las correcciones quedaron integradas mediante PR #7; no hay pruebas de prototipo ejecutadas.

## Cierre de primera entrega

Ver [revisión final y matriz de riesgos](04-evaluation/first-delivery-review.md). Es un cierre documental, con
pendientes identificados; no una certificación de rendimiento, seguridad o disponibilidad del sistema ejecutado.
