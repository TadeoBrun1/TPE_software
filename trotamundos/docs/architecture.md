# Arquitectura de Trotamundos — documento central

**Mantienen:** Tadeo Brun y Tomas Lateana.

**Estado:** primera iteración en revisión; segunda iteración documentada como propuesta y pendiente de alinear con las últimas correcciones de la primera. No hay evidencia de implementación o cumplimiento de atributos de calidad registrada en este documento.

Este documento resume la arquitectura y enlaza al detalle de requisitos, iteraciones, decisiones, vistas y contratos.

## 1. Introducción

Trotamundos es un panel de gestión de viajes para web y dispositivos móviles. Reúne las reservas de un viajero y las organiza por viaje, evitando que deba consultar múltiples aplicaciones y correos.

Las reservas pueden incorporarse desde correos autorizados, integraciones con proveedores externos y carga manual.

El diseño contempla 15 millones de cuentas, 2 millones de usuarios activos semanales y picos de tráfico. Estas cifras son objetivos del sistema; no representan capacidad demostrada por el prototipo.

| Iteración | Estado | Aporte |
|---|---|---|
| [1 — Estructura general](01-add/iteration-1-structure.md) | En revisión; ADRs propuestas | Arquitectura de referencia, núcleo modular, ingesta separada, mensajería y despliegue regional. |
| [2 — Ingesta](01-add/iteration-2-ingestion.md) | Pasos 2 a 6 propuestos; alineación y evaluación pendientes | Obtención autorizada de novedades, adaptadores, procesamiento, publicación durable y contrato propuesto. |
| [3 — Consulta y escala](01-add/iteration-3-query-scale.md) | Pendiente | Consulta, gestión, rendimiento, disponibilidad y escalabilidad. |
| [4 — Seguridad y evolución](01-add/iteration-4-security-evolvability.md) | Pendiente | Compartición, autenticación, internacionalización, analítica y evolución. |

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
| Analítica | Ejecutar procesamiento analítico separado de las operaciones habituales. Su almacenamiento se decide en la iteración 4. |

El núcleo es inicialmente un único desplegable con módulos internos.

La posible separación entre lectura y escritura del núcleo se analiza en la iteración 3; no se considera una decisión ya tomada.

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
| Base operativa | Conservar los datos oficiales de los usuarios de la región. |
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
- El comportamiento para usuarios que viajan se refina en las iteraciones 3 y 4.
- La compartición entre regiones se diseña en la iteración 4.
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
vinculaciones, asistencia de agencia y publicación confirmada. Ver ADR-0020 a 0027 y contratos de ingesta.
Son decisiones propuestas; la selección del broker, parámetros operativos y evaluación del paso 7 siguen pendientes.


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
| [0001](03-adr/0001-nucleo-modular-con-procesos-separados.md) | Núcleo modular con ingesta y analítica separadas. | proposed |
| [0002](03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) | Comunicación asincrónica con publicación y suscripción. | proposed |
| [0003](03-adr/0003-despliegue-por-regiones-con-region-de-origen.md) | Despliegue regional con región de origen por usuario. | proposed |
| [0004](03-adr/0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) | Clientes ricos y puerta de entrada única por región. | proposed |

### Segunda iteración

| ADR | Decisión propuesta | Estado |
|---|---|---|
| [0020](03-adr/0020-obtener-novedades.md) | Sondeo configurable y avisos donde estén disponibles. | proposed |
| [0021](03-adr/0021-autorizacion-correo.md) | Autorización delegada del correo y mínimo privilegio. | proposed |
| [0022](03-adr/0022-tuberia-ingesta.md) | Procesamiento mediante etapas internas. | proposed |
| [0023](03-adr/0023-adaptadores-proveedores.md) | Adaptadores para contratos y formatos externos. | proposed |
| [0024](03-adr/0024-avance-y-publicacion-durable.md) | Avance de sincronización y publicación durable coordinados. | proposed |

Las decisiones de la segunda iteración deben actualizarse donde corresponda para reflejar los ajustes indicados. No se registra aceptación conjunta por el solo hecho de integrar documentación.

## 11. Trazabilidad inicial

| Driver | Iteraciones | Decisiones relacionadas | Validación pendiente |
|---|---|---|---|
| QA-1 | 1 y 2, coordinadas con 3 | 0001, 0002, 0020, 0024 | Tiempo completo desde generación externa hasta visualización. |
| QA-2 y QA-3 | 3 | Base estructural 0001 y 0004 | Consulta web y primer contenido móvil bajo condiciones definidas. |
| QA-4 | 1 y 3 | 0001, 0002, 0003, 0004 | Recuperación ante fallos y presupuesto mensual. |
| QA-5 | 1 y 3 | 0001, 0003, 0004 | Capacidad y respuesta ante carga y picos acordados. |
| QA-6 | 2 y 3 | 0022, 0023, 0024 | Normalización, duplicaciones, desorden y conciliación. |
| QA-8 | 2 | 0021 | Autorización, renovación, revocación y datos conservados. |
| QA-9 | 1, 2 y 4 | 0001, 0002, 0023 | Incorporar una integración y evaluar impacto. |
| QA-7 y QA-10 | 3 y 4, sobre la base de 1 | 0003 y 0004 como base | Compartición, idiomas, formatos y atención regional. |
| RF-06 | 2 | Decisión de integración pendiente | Solicitud de asistencia a la agencia preferida. |
| RF-07 | 4 | Proceso separado por 0001 | Almacenamiento, transferencia y análisis sin degradar operaciones. |

Esta tabla expresa relaciones de diseño, no resultados de pruebas.

## 12. Riesgos y deuda arquitectónica

| Riesgo | Tratamiento pendiente | Responsable |
|---|---|---|
| Sondear muchos buzones puede exceder el presupuesto de frescura o las cuotas externas. | Planificación, consultas incrementales, avisos cuando existan y medición. | Iteración 2 |
| Un correo puede no incluir versión o referencia suficiente. | Separar incorporación automática segura de conciliación o resolución pendiente. | Iteraciones 2 y 3 |
| Novedades duplicadas o desordenadas pueden alterar incorrectamente una reserva. | Idempotencia y reglas de aplicación, sin depender únicamente del orden del intermediario. | Iteraciones 2 y 3 |
| Una notificación externa puede no indicar usuario ni región. | Resolver y verificar su vinculación antes del enrutamiento. | Iteración 2 |
| La caída de una zona puede consumir el presupuesto mensual. | Detección, conmutación y pruebas con tiempos definidos. | Iteración 3 |
| La caída de una región completa no tiene recuperación diseñada. | Precisar alcance y necesidad de recuperación regional. | Iteración 3 |
| Región de origen y región más cercana pueden diferir. | Evaluar atención de viajeros y acceso compartido entre regiones. | Iteraciones 3 y 4 |
| Un cambio confirmado puede no publicarse si el proceso falla. | Persistencia y publicación recuperable coordinadas. | Iteraciones 2 y 3 |
| Dos componentes pueden mantener estados contradictorios de una autorización. | Definir fuente autoritativa y coordinación de revocación. | Iteraciones 2 y 3 |
| Los análisis pueden competir por recursos con las operaciones. | Definir almacenamiento, transferencia y aislamiento analíticos. | Iteración 4 |
| CON-3 carece de un criterio concreto validado. | Precisar la política regional de datos y sus consecuencias. | Ambos integrantes |

## 13. Prototipo y evidencia

Ver [prototype/README.md](../prototype/README.md).

El prototipo debe demostrar recorridos acotados y trazables a contratos y decisiones. Los objetivos incluyen:

- Incorporar una novedad externa y consultar su resultado.
- Tolerar reentregas sin duplicar efectos.
- Recuperar publicación pendiente tras una caída.
- Verificar autorización y revocación del correo.
- Mantener consultas mientras la ingesta está detenida.

Son objetivos de validación, no pruebas ejecutadas.

Una ejecución local no demuestra capacidad para millones de usuarios, independencia real entre zonas ni disponibilidad global mensual.

El plazo del trabajo práctico y los recursos del grupo acotan el prototipo; no se utilizan como justificación de las decisiones de la arquitectura objetivo.

## 14. Coordinación y revisión

Los impactos se registran en [impact-log.md](01-add/impact-log.md).

Antes de cerrar la segunda iteración deben revisarse conjuntamente:

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
Agencia, enrutamiento y outbox del núcleo tienen contratos semánticos propuestos. La tecnología de mensajería,
pruebas de carga/seguridad y el paso 7 siguen pendientes; no se afirma implementación ni cumplimiento de QAs.
