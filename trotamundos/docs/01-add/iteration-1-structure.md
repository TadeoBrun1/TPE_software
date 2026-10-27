# Iteración 1 — Estructura general del sistema

**Responsable:** Ambos
**Fecha:** 2026-10-27 a `<fin>`
**Estado:** En curso (decisiones propuestas, pendientes de confirmar por ambos)
**Rango de ADRs:** 0001 a 0019 (ver [CONTRIBUTING](../../CONTRIBUTING.md))

> Las decisiones de esta iteración son críticas y las toman las dos personas juntas. Las ADRs 0001 a 0004 están en
> estado `proposed` hasta que ambos las confirmen.

---

## Paso 2 — Objetivo de la iteración

Establecer la estructura inicial del sistema: estilo arquitectónico, división en elementos de alto nivel, comunicación
entre ellos y estrategia general de despliegue, de modo que las iteraciones 2 y 3 puedan refinar cada parte por
separado. Los QA se atacan **a nivel de estructura**: el detalle de cada uno queda en la iteración que se indica.

### Drivers seleccionados

| ID | Descripción | Prioridad | Qué se resuelve acá | Detalle en |
|---|---|---|---|---|
| RF-01 | Procesamiento de correo | Alta (primaria) | Existe un elemento de ingesta separado | It. 2 |
| RF-03 | Integración con terceros por APIs estándar | Alta (primaria) | La ingesta incluye un adaptador por proveedor | It. 2 |
| RF-05 | Ciclo de vida del viaje | Alta (primaria) | El núcleo es dueño del estado de viajes y reservas | It. 3 |
| RF-07 | Analítica de datos | Media | Límite entre el almacenamiento operativo y el analítico | It. 4 |
| QA-1 | Frescura de actualizaciones (5 min) | H, H | Camino ingesta → núcleo desacoplado y escalable por separado | It. 2 |
| QA-4 | Disponibilidad (5 min/mes) | H, H | Redundancia por zonas y regiones; la lectura sigue aunque la ingesta falle | It. 3 |
| QA-5 | Escalabilidad y picos | H, H | Núcleo sin estado, partición de datos, escala por separado de cada carga | It. 3 |
| QA-2 | Latencia web (800 ms) | H, M | Perfil de consulta separado de las escrituras; datos cerca del usuario | It. 3 |
| QA-9 | Evolucionabilidad | M, M | Adaptador por proveedor, modelo canónico y mensajes versionados | It. 2 y 4 |
| QA-10 | Usabilidad e i18n (multirregión) | M, H | Solo el principio de región de origen; la atención regional completa queda para después | It. 4 |
| CRN-1 | Estructura inicial del sistema | — | Todo este documento | — |
| CON-1 | Integración con terceros solo por APIs estándar | Restricción | Obliga a adaptadores por proveedor | — |
| CON-2 | Sistemas externos que no se pueden modificar | Restricción | La ingesta tolera sus fallas y límites | — |
| CON-3 | Datos personales según la normativa de cada región | Restricción | Condiciona dónde se almacenan los datos (ADR-0004) | — |

No se seleccionan acá QA-3, QA-6, QA-7 y QA-8: su dueño es otra iteración (ver [plan](iteration-plan.md)). Las
reglas de esta iteración que los protegen están en el Paso 5.

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
| Sistema Trotamundos (completo) | En la 1ra iteración el sistema entero es el único elemento |

## Paso 4 — Conceptos de diseño elegidos

> Elegidos de forma provisoria (ADR en estado `proposed`). Se confirman a mano entre ambos.

| Concepto elegido | Justificación | Alternativas descartadas | ADR |
|---|---|---|---|
| Núcleo modular, con ingesta y analítica como procesos separados. El núcleo tiene un perfil de consulta y otro de gestión, desplegables por separado desde el mismo código | Cargas muy distintas (consultas, importación, análisis) que deben escalar y fallar por separado (QA-5, QA-4, QA-1). Un equipo de 2 puede operar un núcleo modular, no una docena de servicios | Monolito modular en un único despliegue; microservicios por capacidad; funciones por evento (serverless) | [ADR-0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| Mensajería persistente con publicación y suscripción, con dos flujos: novedades de ingesta → núcleo, y eventos de dominio del núcleo → consumidores. Entrega al menos una vez, consumidores idempotentes y patrón *outbox* | Desacopla ritmos y fallas (QA-1, QA-4). Garantiza no perder mensajes (QA-6) y permite alimentar la analítica con todos los cambios, también los manuales | Llamada síncrona a una API del núcleo; cola punto a punto solo para ingesta; escritura directa de la ingesta en la base del núcleo | [ADR-0002](../03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) |
| Almacenamiento y procesamiento analíticos separados, alimentados con los eventos de dominio | Las consultas pesadas no deben degradar la base que atiende a los viajeros (QA-2, QA-4, RF-07) | Réplica de lectura de la misma base; captura de cambios (CDC) sobre la base del núcleo; carga por lotes | [ADR-0003](../03-adr/0003-almacen-analitico-separado.md) |
| Despliegue por regiones: cada usuario tiene una región de origen que atiende su tráfico y guarda sus datos, con varias zonas de fallo por región y recuperación en otra región | Cumple CON-3 y es la única opción que lleva QA-2, QA-3, QA-4 y QA-10 a escala global sin conflictos de escritura | Una sola región; región primaria con otra pasiva; región primaria con réplicas de lectura en todas las regiones | [ADR-0004](../03-adr/0004-despliegue-por-regiones-con-region-de-origen.md) |

### Matriz de decisión: estilo (ADR-0001)

Escala: ++ Promueve fuerte · + Promueve · 0 Neutral · − Inhibe · −− Inhibe fuerte.

| Opción | QA-5 | QA-4 | QA-1 | QA-9 | Viabilidad (2 personas, 10 días, prototipo local) |
|---|---|---|---|---|---|
| A. Monolito modular único | − | − | 0 | + | ++ |
| **B. Núcleo modular + procesos separados** | + | + | + | + | + |
| C. Microservicios por capacidad | ++ | + | + | + | − |
| D. Funciones por evento | ++ | + | + | 0 | −− |

### Matriz de decisión: despliegue (ADR-0004)

| Opción | QA-4 | QA-2 y QA-3 (latencia global) | QA-10 | CON-3 | Viabilidad |
|---|---|---|---|---|---|
| A. Una región con varias zonas | − | −− | −− | − | ++ |
| B. Varias zonas + región pasiva de recuperación | + | − | − | 0 | + |
| C. Región primaria + réplicas de lectura en todas las regiones | + | + | 0 | − | 0 |
| **D. Región de origen por usuario** | ++ | ++ | ++ | ++ | − |

D es la opción más cara: hay que resolver usuarios que viajan e itinerarios compartidos con personas de otra región.
Por eso el prototipo solo demuestra la partición, no la disponibilidad global (ver Paso 7).

## Paso 5 — Instanciación

| Decisión de instanciación | Justificación |
|---|---|
| El núcleo es el único que modifica el estado oficial de viajes y reservas. La ingesta no escribe en las tablas del núcleo | Evita duplicar reglas de negocio y protege la consistencia (QA-6) |
| La ingesta normaliza los datos externos a un modelo canónico de reserva; el núcleo valida, decide a qué viaje pertenece y aplica el cambio | Un adaptador por proveedor y un único modelo interno permiten agregar un medio de transporte sin tocar lo existente (QA-9, CON-1) |
| Si faltan datos para identificar o asociar una reserva, queda en estado pendiente de resolución | La ingesta no puede bloquearse por datos incompletos |
| Los mensajes no llevan contraseñas, tokens ni cuerpos completos de correo | Reduce la superficie de ataque (QA-8) |
| Clave de idempotencia de cada mensaje: proveedor + código de reserva + versión. Los mensajes de una misma reserva se procesan en orden | Repetir un mensaje no crea dos reservas; una cancelación que llega antes que la alta no se pierde (QA-6) |
| El núcleo guarda el cambio y el evento de dominio en la misma transacción (*outbox*) y un proceso aparte lo publica | Evita que un cambio confirmado no llegue a la analítica |
| Los mensajes llevan versión de esquema | Permite evolucionar el formato sin romper consumidores (QA-9) |
| El núcleo no guarda estado de sesión en memoria | Permite agregar instancias automáticamente (QA-5) |
| Los datos se particionan por usuario; la región de origen es parte de la clave de partición | Base de ADR-0004 y de la escala (QA-5, CON-3) |
| La entrada de tráfico es redundante y enruta por región de origen | Un balanceador único sería un punto único de falla (QA-4) |
| Antes de implementar, ambos acuerdan el formato de los mensajes | Es el contrato entre las iteraciones 2 y 3 |

### Contratos nuevos o modificados

| Contrato | Archivo en `specs/` | Cambio |
|---|---|---|
| Novedades de ingesta (ingesta → núcleo) | `specs/asyncapi/` (por crear a partir de `booking-events.example.yaml`) | Nuevo: modelo canónico de reserva, clave de idempotencia, versión de esquema |
| Eventos de dominio (núcleo → consumidores) | `specs/asyncapi/` (por crear) | Nuevo |
| API de itinerarios | `specs/openapi/itinerary-api.example.yaml` | Sin cambios en esta iteración |

## Paso 6 — Vistas actualizadas y ADRs creadas

| Vista | Qué cambió |
|---|---|
| [Modelo de dominio](../02-views/domain-model.md) | Pendiente: versión inicial (viaje, reserva canónica, usuario y región de origen) |
| [Vista de módulos](../02-views/module-view.md) | Pendiente: módulos del núcleo y adaptadores de ingesta |
| [Vista C&C](../02-views/cc-view.md) | Pendiente: núcleo (consulta y gestión), ingesta, analítica y broker, con los dos flujos |
| [Vista de despliegue](../02-views/deployment-view.md) | Pendiente: regiones, zonas y entrada de tráfico |

| ADR | Título | Estado |
|---|---|---|
| [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) | Núcleo modular con procesos separados | Propuesta |
| [0002](../03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) | Mensajería persistente con publicación y suscripción | Propuesta |
| [0003](../03-adr/0003-almacen-analitico-separado.md) | Almacén analítico separado | Propuesta |
| [0004](../03-adr/0004-despliegue-por-regiones-con-region-de-origen.md) | Despliegue por regiones con región de origen | Propuesta |

## Paso 7 — Análisis

El estado refleja lo que se espera de las decisiones propuestas. Se revisa cuando ambos las confirmen.

| Driver | Estado (cumplido, parcial, no cumplido) | Riesgos o pendientes |
|---|---|---|
| CRN-1 | Cumplido | Falta actualizar las vistas |
| RF-01, RF-03 | Parcial | El detalle de sondeo y adaptadores es de la iteración 2 |
| RF-05 | Parcial | La estructura de consulta y gestión es de la iteración 3 |
| RF-07 | Parcial | Falta fijar el retraso aceptable de la analítica; permisos y conservación son de la iteración 4 |
| QA-1 | Parcial | El sondeo de correos a esta escala es el mayor riesgo; falta repartir los 5 minutos entre sondeo, cola y aplicación |
| QA-4 | Parcial | 5 min/mes exige conmutación automática en bastante menos de 5 minutos; la entrada de tráfico debe ser redundante |
| QA-5 | Parcial | Falta definir la partición física de la base y el uso de caché para el panel |
| QA-2 | Parcial | Se valida en la iteración 3 |
| QA-9 | Parcial | Se valida en la iteración 2 con un caso real (agregar trenes) |
| QA-10 | Parcial | Solo el principio de región de origen; idiomas y formatos quedan para la iteración 4 |
| CON-1, CON-2, CON-3 | Cumplido | CON-3 depende de qué regiones se elijan; hay que validar la normativa con un criterio concreto |

### Impacto en otras iteraciones

Esta iteración define los **elementos compartidos** que las siguientes no deben romper en silencio. Quedan listados en
[impact-log.md](impact-log.md).

| Elemento compartido | Usado por iteración |
|---|---|
| Modelo canónico de reserva | 2, 3, 4 |
| Broker y esquema de mensajes (novedades y eventos de dominio) | 2, 3, 4 |
| Clave de partición por usuario y región de origen | 3, 4 |
| Perfil de consulta y perfil de gestión del núcleo | 3 |

### ¿Se sigue iterando?

Sí: iteraciones 2 y 3 en paralelo. Queda para la 4 la atención regional completa (QA-10), el retraso aceptable de la
analítica y los permisos de los datos analíticos.

### Prototipo

| Qué parte del prototipo implementa esta iteración | Spec | ADRs |
|---|---|---|
| Esqueleto de procesos: núcleo (consulta y gestión), ingesta y broker local | `specs/asyncapi/` | 0001, 0002 |
| Idempotencia y orden por reserva; la consulta sigue funcionando con la ingesta detenida | `specs/asyncapi/` | 0002 |
| Enrutamiento por región de origen simulando dos regiones locales | `specs/openapi/` | 0004 |

El prototipo local demuestra fallas de procesos y la partición por región, pero no demuestra disponibilidad global.
