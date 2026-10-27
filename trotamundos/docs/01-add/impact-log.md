# Registro de impactos entre iteraciones

Este documento registra las decisiones que afectan elementos compartidos entre iteraciones y los acuerdos pendientes entre sus responsables.

## Impactos registrados por la iteración 1

| Fecha | Origen | Cambio o decisión | Afecta | Resolución | ADR |
|---|---|---|---|---|---|
| 2026-10-27 | 1 | La idempotencia, su clave y el tratamiento de mensajes desordenados quedan por diseñar. Los correos pueden no incluir una versión externa. | 2 | Resolver mediante decisiones del rango 0020–0039. | ADR-0002 |
| 2026-10-27 | 1 | La publicación confiable de cambios confirmados del núcleo, la cola de errores, los datos personales en mensajes y la tecnología del broker quedan pendientes. | 2 | Definir contratos y mecanismos, coordinando con el responsable del núcleo. | ADR-0002 |
| 2026-10-27 | 1 | La separación entre lectura y escritura dentro del núcleo no está decidida. | 3 | Evaluar su necesidad al diseñar para QA-2. | ADR-0001 |
| 2026-10-27 | 1 | La analítica queda separada como proceso, pero su almacenamiento todavía no está decidido. | 4 | Elegir almacenamiento y transferencia mediante una ADR del rango 0060–0079. | ADR-0001 |
| 2026-10-27 | 1 | La puerta de entrada valida la identidad, pero el mecanismo concreto de autenticación sigue pendiente. | 4 | Diseñar el mecanismo con QA-7. El acceso delegado al correo se trata por separado en la iteración 2. | ADR-0004 |
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

## Propuestas de la iteración 2

Estas propuestas están documentadas para revisión. No implican aprobación conjunta ni validación mediante un prototipo.

| Cambio propuesto | Afecta | Resolución o acuerdo pendiente | Estado |
|---|---|---|---|
| Evento `booking.change.detected.v1` como interfaz de ingesta | 1 y 3 | Revisar el contrato contra la estructura actual. Representa una novedad detectada, no un cambio confirmado. | Propuesto |
| El núcleo conserva la propiedad del estado oficial | 2 y 3 | Ingesta publica novedades; el núcleo valida, concilia, asocia a un viaje y aplica los cambios. | Compatible con la primera iteración |
| `tripId` no obligatorio en la novedad | 3 | El núcleo determina la asociación o conserva el caso pendiente de resolución. | Revisión pendiente |
| Outbox de ingesta coordinada con cursores y resultados | 3 y 4 | Revisar persistencia, confirmaciones y recuperación; distinguirla de la publicación de eventos del núcleo. | Propuesto |
| Presupuesto completo de cinco minutos | 2 y 3 | Distribuir detección, espera en mensajes, aplicación y visualización; conocer cuotas y carga. | Sin cifras acordadas |
| Revocación del acceso al correo | 3 y 4 | Coordinar nuevos accesos y publicaciones pendientes; definir mensajes en tránsito y conservación de reservas. | Revisión pendiente |

## Ajustes necesarios tras las correcciones de la iteración 1

La rama de ingesta se preparó originalmente sobre una versión anterior de la primera iteración. Sus documentos deben alinearse con la revisión incorporada a `main` en el commit `05a8fd737847cecc89722ccde9cd0824e5ffbd0f`.

| Tema | Ajuste necesario en la iteración 2 | Estado |
|---|---|---|
| Numeración de ADRs | ADR-0003 ahora corresponde al despliegue regional. ADR-0004 corresponde a clientes ricos y puerta de entrada. Corregir las referencias anteriores. | Pendiente |
| Entrada de notificaciones | Mostrar entrada global, puerta de entrada regional y receptor de ingesta. No exponer el receptor directamente a Internet. | Pendiente |
| Identificación de región | Definir cómo obtener la región antes de enrutar una notificación externa. Incluir `homeRegion` en el evento no resuelve por sí solo esa búsqueda. | Pendiente |
| Idempotencia sin versión externa | El contrato actual exige `sourceVersion` para procesamiento automático. Revisarlo para admitir correos con datos suficientes aunque no incluyan versión externa. | Pendiente |
| Identidad del mensaje y de la reserva | Distinguir `eventId`, referencia externa, clave de negocio y ámbito de usuario o vinculación. No confundir versión de esquema con versión externa. | Revisión pendiente |
| Mensajes desordenados | El orden del canal no corrige novedades que ya llegan desordenadas. Definir conciliación y tratamiento de cancelaciones anteriores al alta. | Revisión pendiente |
| Configuración de vinculaciones | Acordar qué datos administra el módulo de usuarios del núcleo y qué estado técnico conserva la ingesta. Evitar dos fuentes autoritativas contradictorias. | Pendiente |
| Agencia de viajes | Incorporar RF-06 al objetivo, drivers, componentes e interfaces de la iteración 2. | Pendiente |
| Eventos confirmados del núcleo | Completar el mecanismo de publicación confiable, coordinando con la iteración 3 y manteniendo al núcleo como dueño de sus transacciones. | Pendiente |
| Analítica | Conservar el flujo de cambios confirmados, pero dejar la decisión de almacenamiento para la iteración 4. | Pendiente |
| Tecnología del broker | Seleccionar y justificar la tecnología según durabilidad, consumo, recuperación y carga. | Pendiente |

## Criterio para resolver un impacto

1. Identificar los documentos, contratos y responsables afectados.
2. Proponer la modificación y registrar su justificación.
3. Revisarla con el otro integrante mediante el Pull Request.
4. Actualizar las vistas, contratos y ADR correspondientes.
5. Registrar la resolución real antes de cerrar la iteración.

La documentación de un impacto no equivale a una aprobación ni a una prueba ejecutada. Las decisiones y verificaciones pendientes deben permanecer identificadas como tales.

## Resolución documental de alineación de ingesta

Se proponen los ajustes antes identificados: avisos por Gateway, ADR-0003 para región y ADR-0004 para entrada,
correo sin versión externa obligatoria, autoridad de configuración en núcleo, RF-06 con adaptador de agencia y
outbox propia del núcleo. Ver ADR-0025 a 0027. La revisión cruzada queda pendiente; no se atribuye aprobación.
El broker, tiempos/cuotas/retención, migración o recuperación regional y la evaluación del paso 7 siguen abiertos.
