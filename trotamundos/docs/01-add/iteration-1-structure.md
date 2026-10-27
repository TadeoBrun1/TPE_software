# Iteración 1 — Estructura general del sistema

**Responsable:** Ambos
**Fecha:** 2026-10-27
**Estado:** En revisión. Las ADRs 0001, 0002, 0004 y 0005 están en `proposed` hasta que ambos las confirmen; al
confirmarlas pasan a `accepted` y la iteración se da por cerrada.
**Rango de ADRs:** 0001 a 0019 (ver [CONTRIBUTING](../../CONTRIBUTING.md))

---

## Paso 2 — Objetivo de la iteración

Establecer la estructura inicial del sistema: arquitectura de referencia, división en elementos de alto nivel,
comunicación entre ellos y estrategia general de despliegue, de modo que las iteraciones 2 y 3 puedan refinar cada
parte por separado.

Los atributos de calidad se atacan **a nivel de estructura**: acá se eligen los patrones que los hacen posibles y el
detalle de cada uno queda en la iteración indicada.

### Drivers seleccionados

| ID | Descripción | Prioridad | Qué se resuelve en esta iteración | Detalle en |
|---|---|---|---|---|
| CRN-1 | Estructura inicial del sistema | — | Arquitectura de referencia y elementos de alto nivel | — |
| RF-01 | Procesamiento de correo | Alta (primaria) | Existe un proceso de ingesta separado del núcleo | It. 2 |
| RF-03 | Integración con terceros por APIs estándar | Alta (primaria) | La ingesta tiene un adaptador por proveedor y un modelo canónico | It. 2 |
| RF-05 | Ciclo de vida del viaje | Alta (primaria) | El núcleo es dueño de viajes y reservas, y tiene una tarea programada de archivado | It. 3 |
| QA-1 | Frescura de actualizaciones (5 min) | H, H | La ingesta escala por separado y se comunica de forma asincrónica | It. 2 |
| QA-4 | Disponibilidad (5 min/mes) | H, H | Redundancia en varias zonas; la consulta sigue aunque la ingesta falle | It. 3 |
| QA-5 | Escalabilidad y picos | H, H | Núcleo sin estado y escalado independiente de cada carga | It. 3 |
| QA-9 | Evolucionabilidad | M, M | Adaptador por proveedor, modelo canónico y mensajes versionados | It. 2 y 4 |
| QA-10 (parte multirregión) | Operar en el mercado internacional | M, H | Despliegue por regiones con región de origen | It. 4 (idiomas y formatos) |

**Por qué QA-9 y la parte multirregión de QA-10 entran acá, aunque no son (H, H):** ambos dependen de decisiones de
estructura que después son muy caras de cambiar (cómo se separan las integraciones y si el sistema se despliega en
una o en varias regiones). Si se postergan, las iteraciones 2 y 3 diseñarían sobre una estructura que después habría
que rehacer.

**Por qué QA-2 (H, M) queda para la iteración 3:** sus tácticas (caché, separar lectura y escritura, modelos de
lectura) refinan el núcleo que se define acá, pero no cambian la estructura general.

### Restricciones que aplican

No se tratan como drivers a resolver: limitan las decisiones de todas las iteraciones.

| ID | Restricción | Efecto en esta iteración |
|---|---|---|
| CON-1 | Integración con terceros solo por APIs estándar | Obliga a un adaptador por proveedor |
| CON-2 | Sistemas externos que no se pueden modificar | La ingesta absorbe sus fallas y ráfagas; el núcleo no los llama directamente |
| CON-3 (suposición) | Datos personales según la normativa de cada región | Los datos de un usuario quedan en su región de origen (ADR-0004) |

### Drivers que no se seleccionan acá

| Driver | Iteración |
|---|---|
| QA-2 Latencia web, QA-3 Primer despliegue móvil | 3 |
| QA-6 Interoperabilidad, QA-8 Seguridad de correos, RF-02 Filtros y whitelists | 2 |
| QA-7 Seguridad de compartición, QA-10 (idiomas y formatos), RF-07 Analítica, RF-08 Compartición | 4 |

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
| Sistema Trotamundos (completo) | En la primera iteración el sistema entero es el único elemento |

## Paso 4 — Conceptos de diseño elegidos

En esta iteración se eligen conceptos de diseño (arquitectura de referencia, patrones y tácticas), no componentes
concretos ni tecnologías. Las alternativas descartadas y su análisis están en cada ADR.

### 4.1 Arquitectura de referencia

| Arquitectura de referencia | Dónde se usa | Drivers | ADR |
|---|---|---|---|
| Aplicación de cliente rico y aplicación móvil (guía de Microsoft, usada por Cervantes y Kazman) | Aplicación web de una sola página y app móvil nativa con caché local | CRN-1, QA-10, QA-3 | [0005](../03-adr/0005-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) |
| Aplicación de servicios | Backend que expone una API y no genera pantallas | CRN-1 | [0005](../03-adr/0005-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) |

### 4.2 Patrones

| Patrón | Tipo | Cómo se aplica | Drivers | ADR |
|---|---|---|---|---|
| *API Gateway* | Arquitectónico | Único punto de entrada; enruta por región de origen y reparte carga | QA-4, QA-5, QA-10 | [0005](../03-adr/0005-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) |
| Monolito modular | Arquitectónico | El núcleo es un único desplegable con módulos de responsabilidad clara | RF-05, QA-9 | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| *Publish-Subscribe* con intermediario de mensajes | Arquitectónico | Dos temas: novedades de reservas (ingesta → núcleo) y eventos de dominio (núcleo → consumidores) | QA-1, QA-4, QA-9 | [0002](../03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) |
| *Adapter* + *Canonical Data Model* | De diseño / integración | Un adaptador por proveedor traduce su API al modelo canónico de reserva | QA-9, CON-1 | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| Despliegue por celdas (*Deployment Stamps*) | De despliegue | Cada región es una copia completa del sistema que atiende a sus usuarios | QA-10, QA-4 | [0004](../03-adr/0004-despliegue-por-regiones-con-region-de-origen.md) |

### 4.3 Tácticas

Nombres según Bass, Clements y Kazman (4ta edición).

| Atributo | Táctica | Cómo se aplica | Drivers | ADR |
|---|---|---|---|---|
| Disponibilidad | Redundancia activa | Todas las instancias en al menos dos zonas por región, atendiendo tráfico a la vez | QA-4 | [0004](../03-adr/0004-despliegue-por-regiones-con-region-de-origen.md) |
| Disponibilidad | Monitoreo / heartbeat | El balanceador detecta instancias o zonas que no responden y deja de enviarles tráfico | QA-4 | [0004](../03-adr/0004-despliegue-por-regiones-con-region-de-origen.md) |
| Disponibilidad | Degradación elegante | Si la ingesta cae, la consulta sigue respondiendo con los últimos datos | QA-4 | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| Disponibilidad | Redundancia pasiva | Respaldo de cada región en otra región de la misma jurisdicción | QA-4, CON-3 | [0004](../03-adr/0004-despliegue-por-regiones-con-region-de-origen.md) |
| Performance / escalabilidad | Mantener múltiples copias del cómputo e introducir concurrencia | Núcleo sin estado con varias instancias detrás del balanceador | QA-5 | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| Performance / escalabilidad | Mantener múltiples copias de los datos | Réplica de la base en otra zona; caché del itinerario en la app móvil | QA-4, QA-3 | [0004](../03-adr/0004-despliegue-por-regiones-con-region-de-origen.md), [0005](../03-adr/0005-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) |
| Performance / escalabilidad | Limitar el tamaño de las colas / amortiguar la demanda | Las ráfagas de los proveedores esperan en el broker | QA-1, CON-2 | [0002](../03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) |
| Performance / escalabilidad | Administrar las solicitudes de trabajo | Límite de tráfico por cliente en la puerta de entrada | QA-5 | [0005](../03-adr/0005-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) |
| Modificabilidad | Dividir módulo / aumentar cohesión | Ingesta y analítica salen del núcleo | QA-5, QA-9 | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| Modificabilidad | Usar un intermediario | El broker separa productores y consumidores | QA-9 | [0002](../03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) |
| Modificabilidad | Restringir dependencias | La ingesta no conoce la base del núcleo; los adaptadores no dependen entre sí | QA-9 | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| Integrabilidad | Encapsular y adaptar la interfaz | Cada adaptador oculta la API estándar de su proveedor | QA-9, CON-1 | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |

## Paso 5 — Instanciación

### Elementos y responsabilidades

| Elemento | Tipo | Responsabilidades | Se refina en |
|---|---|---|---|
| Aplicación web | Cliente rico (aplicación de una sola página) | Mostrar el panel de viajes; carga manual de reservas (RF-04) | It. 3 |
| App móvil | Cliente nativo | Panel de viajes; GPS; caché local del último itinerario | It. 3 |
| Puerta de entrada | *API Gateway* | Único punto de entrada; valida la identidad; enruta a la región de origen; balancea; limita el tráfico | It. 3 y 4 |
| Núcleo | Monolito modular sin estado | Único dueño del estado de viajes y reservas; aplica las novedades de la ingesta; publica eventos de dominio | It. 3 |
| Módulo Viajes y ciclo de vida | Módulo del núcleo | Agrupar reservas por viaje; tarea programada que archiva los viajes completados (RF-05) | It. 3 |
| Módulo Reservas | Módulo del núcleo | Alta, cambio y baja de reservas (manual o por novedades); reservas pendientes de resolución | It. 2 y 3 |
| Módulo Usuarios y preferencias | Módulo del núcleo | Región de origen, idioma, cuentas de correo vinculadas, remitentes permitidos (RF-02) | It. 2 y 4 |
| Módulo Compartición | Módulo del núcleo | Personas designadas por viaje (RF-08) | It. 4 |
| Ingesta | Proceso separado | Sondeo de correos (RF-01); un adaptador por proveedor (RF-03); traducción al modelo canónico; publicación de novedades | It. 2 |
| Intermediario de mensajes | Broker persistente | Temas "novedades de reservas" y "eventos de dominio" | It. 2 |
| Base operativa | Almacenamiento por región | Datos del núcleo, particionados por usuario; réplica en otra zona | It. 3 |
| Analítica | Proceso separado | Consume los eventos de dominio; no comparte recursos con la consulta | It. 4 ([ADR-0060](../03-adr/0060-almacen-analitico-separado.md)) |

### Reglas de interacción

| Regla | Justificación |
|---|---|
| Solo el núcleo modifica el estado oficial de viajes y reservas; la ingesta no escribe en su base | Las reglas de negocio están en un solo lugar (QA-9) |
| Si a una novedad le faltan datos para asociarla a un viaje, la reserva queda pendiente de resolución | La ingesta no se bloquea por datos incompletos (QA-1) |
| Ningún proceso interno queda expuesto a Internet: todo entra por la puerta de entrada | Un único lugar para enrutar, autenticar y limitar (QA-4, QA-5) |
| El núcleo no guarda estado de sesión en memoria | Se pueden agregar instancias sin coordinación (QA-5) |
| La región de origen es parte de la clave de partición de los datos | Base de la operación multirregión (QA-10, CON-3) |
| Los mensajes llevan versión de esquema | Se puede evolucionar el formato sin romper consumidores (QA-9) |

### Contratos nuevos o modificados

| Contrato | Archivo en `specs/` | Cambio |
|---|---|---|
| Novedades de reservas (ingesta → núcleo) | `specs/asyncapi/` (a crear a partir de `booking-events.example.yaml`) | Nuevo: modelo canónico de reserva con versión de esquema. La clave de idempotencia se agrega en la iteración 2 |
| Eventos de dominio (núcleo → consumidores) | `specs/asyncapi/` (a crear) | Nuevo |
| API de itinerarios (clientes → puerta de entrada → núcleo) | `specs/openapi/itinerary-api.example.yaml` | Sin cambios; se refina en la iteración 3 |

## Paso 6 — Vistas actualizadas y ADRs creadas

| Vista | Qué cambió |
|---|---|
| [Modelo de dominio](../02-views/domain-model.md) | Región de origen del usuario, estados de viaje y reserva, origen de la reserva |
| [Vista de módulos](../02-views/module-view.md) | Módulos del núcleo y de la ingesta, con reglas de dependencia |
| [Vista C&C](../02-views/cc-view.md) | Clientes, puerta de entrada, núcleo, ingesta, broker, base y analítica, con los dos flujos de mensajes |
| [Vista de despliegue](../02-views/deployment-view.md) | Entrada global, regiones como celdas, zonas de falla y respaldo en la misma jurisdicción |

| ADR | Título | Estado |
|---|---|---|
| [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) | Núcleo como monolito modular, con ingesta y analítica como procesos separados | Propuesta |
| [0002](../03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) | Comunicación asincrónica con intermediario de publicación y suscripción | Propuesta |
| [0003](../03-adr/0003-almacen-analitico-separado.md) | Almacén analítico separado | Reemplazada por 0060 (trasladada a la iteración 4) |
| [0004](../03-adr/0004-despliegue-por-regiones-con-region-de-origen.md) | Despliegue multirregión con región de origen por usuario | Propuesta |
| [0005](../03-adr/0005-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) | Arquitectura de referencia: clientes ricos y puerta de entrada única | Propuesta |

## Paso 7 — Análisis

### Estado de los drivers

| Driver | Estado | Qué falta |
|---|---|---|
| CRN-1 | Cumplido | Confirmar las ADRs entre ambos |
| RF-01, RF-03 | Parcial | Sondeo de correos, adaptadores concretos y manejo de errores (iteración 2) |
| RF-05 | Parcial | Criterio de cuándo un viaje está completo y frecuencia del archivado |
| QA-1 | Parcial | Repartir los 5 minutos entre sondeo, broker y aplicación en el núcleo (iteración 2) |
| QA-4 | Parcial | Tiempos de detección y conmutación dentro de una región (iteración 3) |
| QA-5 | Parcial | Partición física de la base y política de escalado automático (iteración 3) |
| QA-9 | Parcial | Validarlo con un caso concreto: agregar trenes (iteración 2) |
| QA-10 (multirregión) | Parcial | Usuarios que viajan e itinerarios compartidos entre regiones (iteraciones 3 y 4) |
| CON-1, CON-2, CON-3 | Respetadas | CON-3 es una suposición: validar qué normativa se toma como criterio |

### Riesgos

| Riesgo | Driver | Cómo se mitiga | Iteración |
|---|---|---|---|
| Sondear millones de buzones puede no entrar en los 5 minutos | QA-1 | Notificaciones del proveedor de correo cuando existan, sondeo como respaldo | 2 |
| La conmutación ante una falla de zona consume el presupuesto de 5 min/mes | QA-4 | Detección por heartbeat y conmutación automática con tiempos medibles | 3 |
| Una persona de otra región no puede ver un itinerario compartido sin copiar datos | QA-7, CON-3 | Leer desde la región de origen del dueño del viaje | 4 |
| CON-3 no está validada con una normativa concreta | CON-3 | Validarla antes de cerrar la primera entrega | — |

### Lo que se deja para otras iteraciones

Quedan anotados en el [registro de impactos](impact-log.md):

* **Iteración 2:** idempotencia y su clave (los correos no traen versión), mensajes que llegan desordenados desde la
  fuente, publicación garantizada de los eventos del núcleo (*outbox*), cola de errores, qué datos personales pueden
  viajar en los mensajes y tecnología del broker.
* **Iteración 3:** separación entre lectura y escritura en el núcleo y caché para QA-2; *Backend for Frontend* solo
  si el análisis lo justifica.
* **Iteración 4:** almacén analítico ([ADR-0060](../03-adr/0060-almacen-analitico-separado.md)), mecanismo de
  autenticación y compartición entre regiones.

### Elementos compartidos con otras iteraciones

| Elemento compartido | Usado por iteración |
|---|---|
| Modelo canónico de reserva | 2, 3, 4 |
| Broker y esquema de mensajes (novedades y eventos de dominio) | 2, 3, 4 |
| Clave de partición por usuario y región de origen | 3, 4 |
| Módulos del núcleo | 2, 3, 4 |
| Puerta de entrada | 3, 4 |

### ¿Se sigue iterando?

Sí: iteraciones 2 y 3 en paralelo sobre esta estructura.

### Prototipo

Alcance acotado: demuestra la estructura, no la operación global.

| Qué demuestra | Cómo | Spec | ADRs |
|---|---|---|---|
| Procesos separados que se comunican por el broker | `docker compose` con núcleo, ingesta y broker | `specs/asyncapi/` | 0001, 0002 |
| Degradación elegante: con la ingesta detenida, la consulta responde | Prueba con la ingesta apagada | `specs/openapi/` | 0001 |
| Mensajes que esperan en el broker mientras el núcleo está caído | Prueba con el núcleo apagado | `specs/asyncapi/` | 0002 |

La multirregión y la puerta de entrada se documentan en las vistas, pero no se simulan en el prototipo.
