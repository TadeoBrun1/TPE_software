# Iteración 4 — Seguridad, compartición, analítica, internacionalización y evolucionabilidad

**Responsable:** Ambos (decisiones tomadas por Tadeo Brun; revisión cruzada de Tomas Lateana en el PR)
**Fecha:** 2026-10-28
**Estado:** Decisiones tomadas (2026-10-28). Las ADRs 0060 a 0067 quedan en `proposed` hasta el merge a `main`.
Revisada con una auditoría independiente (ver el final del documento).
**Rango de ADRs:** 0060 a 0079 (ver [CONTRIBUTING](../../CONTRIBUTING.md))

> Las decisiones se tomaron eligiendo entre alternativas planteadas para cada punto; las descartadas y sus razones
> están en cada ADR. Lo que afecta a otras iteraciones está en el [registro de impactos](impact-log.md).

---

## Paso 2 — Objetivo de la iteración

Resolver lo que cruza todo el sistema: quién es cada usuario, cómo se comparte un itinerario sin que lo vea quien no
fue designado, cómo se recopilan datos analíticos sin exponer datos personales, cómo se muestra la aplicación en
varios idiomas y países, cómo se agrega un medio de transporte sin tocar lo existente, y cómo se observa el sistema
para poder medir los QA de las iteraciones anteriores.

### Drivers seleccionados

| ID | Descripción | Prioridad | Qué se resuelve acá |
|---|---|---|---|
| QA-7 | El 100 % de los accesos de personas no designadas se rechaza y queda registrado | M, M | Identidad, permiso por viaje y auditoría |
| RF-08 | Compartir un itinerario con personas designadas | Media | Invitación, aceptación, revocación y lectura entre regiones |
| Interoperabilidad con redes sociales | "Interoperar con redes sociales para compartir itinerarios" (enunciado, atributo Interoperabilidad) | — | Qué se publica sin romper QA-7 |
| RF-07 | Datos analíticos y consultas pesadas para el equipo de datos | Media | Fuente de datos, almacén y tratamiento de datos personales |
| QA-10 | Textos y formatos según la configuración del usuario, cumpliendo QA-2 y QA-3 | M, H | Catálogos de textos y formato de fechas, horas y monedas |
| QA-9 | Agregar un medio de transporte en 10 días-persona o menos, sin modificar el código existente | M, M | Modelo de reserva extensible por tipo |
| CRN-2 | Registro de eventos, monitoreo y trazas | — | Cómo se miden QA-1 y QA-4 |

### Restricciones que aplican

| ID | Efecto en esta iteración |
|---|---|
| CON-2 | Las redes sociales son externas: no se integra una API por red ni se guardan credenciales de redes |
| CON-3 (suposición, se mantiene) | Los datos personales no cruzan regiones: identidad por región, lectura remota de viajes compartidos, analítica solo regional, observabilidad por región |
| CON-4 | La app móvil nativa formatea con las librerías del sistema y guarda catálogos de textos |
| CON-5 (suposición) | Sin componentes globales con datos personales que haya que replicar y operar en todas las regiones |

### Lo que no se trata acá

| Tema | Decisión |
|---|---|
| Opción avanzada A o B (segunda entrega) | Fuera de alcance. Para la opción A (recomendación) se registra un impacto: ADR-0064 deja claro qué datos no puede usar |
| QA-1 a escala con avisos perdidos | Sigue como riesgo aceptado (iteración 3); iteración 5 si hay tiempo |
| Falla de una región completa | Riesgo aceptado desde la iteración 1 |
| Avisos en vivo de viajes compartidos | Fuera de alcance: quien recibe el viaje revalida al abrirlo (ADR-0062) |
| Autorización delegada al correo (QA-8) | Resuelta en la iteración 2 (ADR-0021); no cambia |

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
| Puerta de entrada y entrada global | Validación de tokens, enrutamiento por región en el login y reenvío entre regiones |
| Núcleo / `usuarios` y `comparticion` | Identidad del viajero, preferencias de idioma, invitaciones, permisos y auditoría |
| Núcleo / `reservas` | Campos comunes y detalles por tipo |
| Analítica | Fuente de datos, almacén y anonimización |
| Clientes web y móvil | Login, ticket SSE, catálogos de textos, formato, vista genérica de reservas |
| Todos los procesos | Trazas, métricas y logs |

## Paso 4 — Patrones y tácticas elegidos

### 4.1 Patrones

| Patrón | Cómo se aplica | Drivers | ADR |
|---|---|---|---|
| *Federated Identity* (OpenID Connect / OAuth 2.0) con token firmado | Un proveedor de identidad por región emite tokens de 15 min; la puerta de entrada los valida sin consultar | QA-7, QA-5 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md) |
| *Gateway Routing* | La entrada global enruta por región de origen; la puerta de entrada reenvía a la región del dueño de un viaje compartido | CON-3, RF-08 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md), [0062](../03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md) |
| *Publish-Subscribe* y *Transactional Outbox* (iteraciones 1 y 2) | El núcleo publica `booking.facts.v1` para la analítica en la misma transacción que el cambio | RF-07 | [0064](../03-adr/0064-analitica-regional-anonimizada.md) |
| Almacén analítico separado | Copia regional de los hechos, anonimizada, para consultas pesadas | RF-07, QA-5 | [0064](../03-adr/0064-analitica-regional-anonimizada.md) |
| Modelo con campos comunes y extensión por tipo (esquema por tipo) | Bloque `details` validado contra `specs/schemas/` | QA-9 | [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) |
| Catálogos de recursos externos (*externalized strings*) | Textos de la interfaz fuera del código, por idioma | QA-10 | [0065](../03-adr/0065-internacionalizacion-en-el-cliente.md) |
| *Distributed Tracing* con identificador de correlación | `correlationId` y `traceparent` desde la ingesta hasta el cliente | CRN-2, QA-1 | [0067](../03-adr/0067-observabilidad-con-trazas-y-metricas.md) |

### 4.2 Tácticas

Nombres según Bass, Clements y Kazman (4ta edición).

| Atributo | Táctica | Cómo se aplica | Drivers | ADR |
|---|---|---|---|---|
| Seguridad | Autenticar actores | Token firmado en cada solicitud; mTLS y validación del token entre regiones | QA-7 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md), [0062](../03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md) |
| Seguridad | Autorizar actores | Permiso por viaje y persona, verificado en cada lectura en el módulo `comparticion` | QA-7 | [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md) |
| Seguridad | Limitar el acceso | Solo la puerta de entrada recibe solicitudes externas; el ticket SSE solo abre una conexión | QA-7 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md) |
| Seguridad | Limitar la exposición | Vista compartida sin notas ni códigos; `404` en lugar de `403`; tarjeta pública sin reservas; datos sin copiar entre regiones; analítica anonimizada; logs sin datos personales | QA-7, CON-3 | [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md), [0062](../03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md), [0063](../03-adr/0063-tarjeta-de-resumen-para-redes-sociales.md), [0064](../03-adr/0064-analitica-regional-anonimizada.md), [0067](../03-adr/0067-observabilidad-con-trazas-y-metricas.md) |
| Seguridad | Revocar el acceso | El dueño revoca con efecto en la siguiente lectura; revocación del token de renovación | QA-7 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md), [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md) |
| Seguridad | Auditar | Registro de solo agregado de todos los accesos a viajes compartidos, escrito antes de responder | QA-7 | [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md) |
| Seguridad | Validar la entrada | Los detalles por tipo se validan contra su esquema | QA-9 | [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) |
| Modificabilidad | Abstraer servicios comunes | Campos comunes que usa toda la lógica del núcleo | QA-9 | [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) |
| Modificabilidad | Encapsular y restringir dependencias | Lo propio de cada medio queda en `details`; el núcleo y el panel no dependen de esos campos | QA-9 | [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) |
| Modificabilidad | Diferir el enlace | Esquemas registrados por configuración; catálogos de textos descargados en ejecución | QA-9, QA-10 | [0065](../03-adr/0065-internacionalizacion-en-el-cliente.md), [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) |
| Integrabilidad | Adherir a estándares | OpenID Connect, ISO 8601, ISO 4217, Unicode CLDR, JSON Schema, Open Graph, OpenTelemetry | QA-7, QA-9, QA-10, CRN-2 | 0060, 0063, 0065, 0066, 0067 |
| Performance | Mantener múltiples copias de los datos | Almacén analítico separado de la base operativa; el panel en caché sirve para cualquier idioma | QA-5, QA-3 | [0064](../03-adr/0064-analitica-regional-anonimizada.md), [0065](../03-adr/0065-internacionalizacion-en-el-cliente.md) |
| Disponibilidad | *Monitor* | Métricas de disponibilidad, conmutaciones y colas, con alertas | QA-4, CRN-2 | [0067](../03-adr/0067-observabilidad-con-trazas-y-metricas.md) |
| Disponibilidad | *Redundant spare* | Proveedor de identidad en dos zonas por región | QA-4 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md) |
| Testeabilidad | Grabar y reproducir | Trazas y logs estructurados que reconstruyen cada recorrido | CRN-2, QA-1 | [0067](../03-adr/0067-observabilidad-con-trazas-y-metricas.md) |

## Paso 5 — Instanciación

### Elementos nuevos o refinados

| Elemento | Tipo | Responsabilidades |
|---|---|---|
| Proveedor de identidad | Proceso nuevo, por región, en dos zonas | Login, emisión y renovación de tokens, revocación; guarda credenciales y emails de los usuarios de su región |
| Directorio global de regiones | Componente global nuevo, mínimo | Traduce `hash(email)` a región de origen para el login; sin datos personales legibles |
| Entrada global | Refinada | Elige la región por `homeRegion` del token, o por el directorio en el login |
| Puerta de entrada | Refinada | Valida firma y vencimiento de los tokens; rechaza tokens de otra región; reenvía por mTLS a la región del dueño los recursos con otro prefijo de región; valida tickets SSE; sirve los catálogos de textos |
| Núcleo / `usuarios` | Módulo refinado | Perfil con idioma y país; referencias a viajes compartidos conmigo |
| Núcleo / `comparticion` | Módulo con contenido (estaba vacío) | Invitaciones, aceptación, permisos, revocación, vista compartida y tarjeta para redes; escribe la auditoría |
| Registro de auditoría | Almacén nuevo, por región, replicado en dos zonas | Registros de solo agregado de los accesos a viajes compartidos ([access-audit.md](../../specs/access-audit.md)) |
| Núcleo / `reservas` | Módulo refinado | Campos comunes; valida y guarda `details` según el esquema registrado; publica `booking.facts.v1` |
| Analítica | Proceso refinado | Consume `booking.facts.v1` y `trip.changed.v1`, anonimiza y guarda |
| Almacén analítico | Almacén nuevo, por región | Hechos anonimizados para consultas pesadas |
| Colector de observabilidad | Componente nuevo, por región | Recibe trazas, métricas y logs de todos los procesos; alertas |
| Clientes web y móvil | Refinados | Login con el proveedor de su región, renovación del token, ticket SSE, catálogos, formato CLDR, vista genérica de reservas |

### Reglas de interacción

| Regla | Justificación |
|---|---|
| Ninguna solicitud externa llega al núcleo ni al notificador sin pasar por la puerta de entrada con un token válido (o un ticket SSE) | Autenticar actores (ADR-0060) |
| Un recurso con prefijo de otra región se reenvía a esa región; la respuesta no se guarda en la región del lector | No copiar datos personales (ADR-0062, CON-3) |
| Toda lectura de un viaje compartido verifica el permiso y escribe la auditoría antes de responder; si la auditoría falla, se rechaza | QA-7 al 100 % (ADR-0061) |
| La analítica no lee la base operativa; solo consume eventos y guarda lo anonimizado | Separar cargas y no guardar datos personales (ADR-0064) |
| El núcleo y el panel no interpretan `details` | QA-9 (ADR-0066) |
| El backend no devuelve textos traducidos ni fechas formateadas | El panel no depende del idioma (ADR-0065) |
| Ningún log, traza ni métrica lleva emails, nombres, códigos de reserva ni tokens | CON-3 (ADR-0067) |

### Tiempos y valores de diseño

| Qué | Valor | Origen |
|---|---|---|
| Vida del token de acceso | 15 min | Ventana máxima de un token revocado (ADR-0060) |
| Vida del token de renovación | 30 días, revocable | Valor de producto (suposición) |
| Vida del ticket SSE | 30 s, un solo uso | Alcanza para abrir la conexión (ADR-0060) |
| Vigencia de una invitación | 7 días | Valor de producto (suposición, ADR-0061) |
| Retención de la auditoría | 1 año | Mismo plazo que los viajes (ADR-0045; suposición) |
| Cambio y destrucción de la clave de anonimización | Anual | Alinea la analítica con la eliminación de viajes (ADR-0064) |
| Muestreo de trazas | Todas las lentas o con error; 10 % de las normales | Costo de almacenamiento (suposición, ADR-0067) |

### Contratos nuevos o modificados

| Contrato | Archivo | Cambio |
|---|---|---|
| API de itinerarios | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) | 0.2.0: `bearerAuth` concreto (JWT de 15 min); ticket SSE; invitaciones, aceptación, revocación y viajes compartidos; tarjeta para redes; `type` como código abierto, `details`, `arrivalLocation` y `price` (ISO 4217); identificadores con prefijo de región |
| Hechos de reservas para la analítica | [booking-facts.v1.yaml](../../specs/asyncapi/booking-facts.v1.yaml) | Nuevo; solo campos permitidos, sin códigos ni textos |
| Novedades de reservas | [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml) | 0.2.0: tipo abierto, `arrivalLocation` y `details` (cambio sobre el contrato de la iteración 2, ver el registro de impactos) |
| Esquemas de detalles | [specs/schemas/](../../specs/schemas/README.md) | Nuevos: `flight.v1` y `train.v1` como ejemplos del formato |
| Registro de auditoría | [access-audit.md](../../specs/access-audit.md) | Nuevo: acciones, campos y reglas |
| Cambios confirmados de reservas y viajes | `booking-confirmed.v1.yaml`, `trip-changed.v1.yaml` | Sin cambios; `trip.changed.v1` lo consume la analítica |

## Paso 6 — Vistas actualizadas y ADRs creadas

| Vista | Qué cambió |
|---|---|
| [Vista C&C](../02-views/cc-view.md) | Proveedor de identidad, registro de auditoría, almacén analítico, colector de observabilidad, reenvío entre regiones, `booking.facts.v1` |
| [Vista de despliegue](../02-views/deployment-view.md) | Directorio global, proveedor de identidad en dos zonas, almacenes de auditoría y analítica, colector, canal mTLS entre regiones |
| [Vista de módulos](../02-views/module-view.md) | Contenido de `comparticion`, refinamiento de `usuarios` y `reservas`, esquemas por tipo |
| [Vistas de secuencia](../02-views/sequence-views.md) | SEQ-5 (compartir y leer un viaje desde otra región) y SEQ-7 (login y conexión SSE) |
| [Modelo de dominio](../02-views/domain-model.md) | Invitación y permiso, referencia a viaje compartido, registro de auditoría, detalles por tipo, preferencias de idioma |
| [Interfaces](../02-views/interfaces.md) | API 0.2.0, `booking.facts.v1`, esquemas de detalles |

| ADR | Título | Estado |
|---|---|---|
| [0060](../03-adr/0060-identidad-por-region-con-tokens.md) | Autenticación con un proveedor de identidad por región y tokens de vida corta | Propuesta |
| [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md) | Compartición con personas designadas con cuenta, control en el núcleo y auditoría | Propuesta |
| [0062](../03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md) | Lectura remota de viajes compartidos en la región del dueño | Propuesta |
| [0063](../03-adr/0063-tarjeta-de-resumen-para-redes-sociales.md) | Tarjeta de resumen pública para compartir en redes sociales | Propuesta |
| [0064](../03-adr/0064-analitica-regional-anonimizada.md) | Almacenes analíticos regionales, con los eventos anonimizados al entrar | Propuesta |
| [0065](../03-adr/0065-internacionalizacion-en-el-cliente.md) | Internacionalización: catálogos remotos, datos neutros y formato en el cliente | Propuesta |
| [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) | Reserva con campos comunes y detalles con esquema propio por tipo | Propuesta |
| [0067](../03-adr/0067-observabilidad-con-trazas-y-metricas.md) | Observabilidad con trazas distribuidas, métricas por etapa y logs estructurados | Propuesta |

## Paso 7 — Análisis

Recorrido de escenarios sobre el diseño (*Scenario Walkthrough*). Son resultados esperados por diseño, no
mediciones.

### Recorridos

| Escenario | Recorrido | Resultado esperado | Límite o riesgo |
|---|---|---|---|
| QA-7: una persona no designada abre el enlace de un viaje compartido | Puerta de entrada valida su token → (reenvío si el viaje es de otra región) → `comparticion` no encuentra permiso → escribe la auditoría → `404` | Rechazado y registrado | — |
| QA-7: alguien reenvía el email de invitación ya aceptada | `POST /shares/{id}/accept` con otra cuenta → la invitación ya está atada a otro `userId` → auditoría → `404` | El enlace no da acceso a una segunda persona | Si la invitación no fue aceptada todavía, quien tenga el email la puede aceptar primero: el dueño ve quién aceptó y puede revocar |
| QA-7: el dueño revoca y la persona intenta leer | El permiso ya no existe → auditoría → `404` | Efecto en la siguiente lectura | — |
| QA-7: la auditoría no se puede escribir | El núcleo no responde con datos → `503` | Ningún acceso sin registrar | Disminuye la disponibilidad de la lectura compartida mientras falle la auditoría |
| QA-7: solicitud sin token o con token vencido | La puerta de entrada responde `401` y lo registra en sus logs y métricas | Rechazado y registrado, sin llegar al núcleo | — |
| QA-7: token robado | Sirve hasta 15 minutos; el token de renovación se revoca | Ventana acotada | Riesgo aceptado (ADR-0060) |
| RF-08: Ana (Europa) ve un viaje de Juan (Sudamérica) | Puerta de Europa → mTLS → puerta de Sudamérica valida el token de Ana → núcleo verifica, audita y responde | Ana ve el viaje sin que se copie a Europa | Suma la red entre regiones (100 a 250 ms, suposición); si Sudamérica no responde, `503` |
| Redes sociales: Juan publica su viaje | `POST /trips/{id}/social-card` → enlace `/cards/{id}` → la red muestra la vista previa | Se publica destino, mes y días | El itinerario no se publica: es la interpretación elegida |
| RF-07: el equipo de datos consulta destinos más reservados del año | Consulta pesada en el almacén analítico de cada región; se combinan los resultados | Sin efecto en el panel de los viajeros | Tendencias globales armadas fuera del sistema |
| RF-07: se elimina un viaje (ADR-0045) | No se toca la analítica; la clave con la que se anonimizaron sus datos ya se destruyó | Datos analíticos no vinculables | Si se elimina una cuenta antes, sus datos siguen seudonimizados hasta destruir la clave (a lo sumo un año) |
| QA-10: un usuario argentino usa la app en inglés durante un viaje a Japón | La entrada global lo envía a Sudamérica (su región); el panel llega con fechas ISO 8601 con zona y montos con moneda; la app formatea en inglés y muestra cada hora en la zona del lugar | Textos y formatos según su configuración | QA-2 desde Japón suma la latencia hasta su región (aceptado en las iteraciones 1 y 3) |
| QA-10 con QA-3: abrir la app | Usa el panel en caché y el catálogo ya guardado; nada depende del idioma | QA-3 sin cambios | Un idioma recién agregado se descarga en segundo plano |
| QA-9: agregar ferry | Esquema `details-ferry.v1.json` y código `ferry` → adaptador nuevo en la ingesta → registro del esquema en el núcleo por configuración → vista del detalle en clientes y textos en catálogos | Sin cambios en el código de los otros medios ni en `viajes`, `reservas` y `panel`; entre 8 y 10 días-persona (suposición) | Si el proveedor solo manda correos, el extractor puede superar los 10 días. Si la app vieja recibe `ferry`, lo muestra con la vista genérica |
| CRN-2 con QA-1: medir una novedad | El `correlationId` nace en la ingesta y viaja por los tres eventos; la app informa cuándo mostró la versión nueva | Tiempo por etapa del presupuesto de 300 s | Hay que propagar el contexto a través de RabbitMQ en todos los procesos |
| CRN-2 con QA-4: medir la inactividad | Disponibilidad de la puerta de entrada por minuto y conmutaciones del monitor | Minutos de inactividad por mes medidos | — |

### Estado de los drivers

| Driver | Estado | Qué falta |
|---|---|---|
| QA-7 | Cumplido por diseño | Pruebas del prototipo (designado, no designado, revocado, reenvío del enlace); la ventana de 15 minutos de un token robado es un riesgo aceptado |
| RF-08 | Cumplido por diseño | Sin avisos en vivo de viajes compartidos |
| Redes sociales | Cumplido con la interpretación de la tarjeta | Confirmar la interpretación con la cátedra |
| RF-07 | Cumplido por diseño | Validar con el equipo de datos qué consultas necesita; no hay vista global automática |
| QA-10 | Cumplido por diseño | Probar dos idiomas y zonas horarias; la latencia fuera de la región ya estaba analizada en la iteración 3 |
| QA-9 | Cumplido por diseño | Medir el esfuerzo real agregando un medio al prototipo |
| CRN-2 | Cumplido por diseño | Implementar la propagación en el prototipo |

### Riesgos

| Riesgo | Driver | Tratamiento |
|---|---|---|
| Un token de acceso robado o revocado sirve hasta 15 minutos | QA-7 | Aceptado; la vida corta acota la ventana |
| Una invitación no aceptada la puede aceptar cualquiera que tenga el email | QA-7 | Aceptado; vence en 7 días, el dueño ve quién aceptó y revoca |
| Si la auditoría falla, las lecturas compartidas se rechazan | QA-7 frente a QA-4 | Aceptado: QA-7 exige el 100 %; el registro de auditoría se replica en dos zonas de la región, igual que la base |
| La lectura compartida entre regiones depende de la otra región y suma latencia | RF-08, QA-2 | Aceptado; medir la latencia entre regiones |
| El directorio global es un componente global; si cae, no se puede iniciar sesión (quien ya tiene token sigue) | QA-4 | Mitigado: sin datos personales, se puede replicar en varias regiones; la app recuerda la región del último login |
| Datos de una cuenta eliminada quedan seudonimizados en la analítica hasta un año | CON-3 | Aceptado; validar contra la normativa elegida (CON-3 sigue siendo suposición) |
| Un medio que solo llega por correo puede superar los 10 días-persona | QA-9 | Registrar el esfuerzo real con el prototipo |
| El núcleo no puede aplicar reglas sobre los detalles de un medio | QA-9 | Aceptado; una regla así es un cambio explícito del núcleo |
| Interpretación de "compartir en redes" como tarjeta de resumen | Interoperabilidad | Confirmar con la cátedra |

### Supuestos de esta iteración

Son estimaciones o valores de producto, no comportamientos garantizados. Cada uno indica de qué dato del enunciado o
de los QA parte.

| Supuesto | De dónde parte | Uso |
|---|---|---|
| Los datos personales no deben salir de la región de origen | CON-3, que sigue como suposición (falta fijar la normativa) | Identidad por región, lectura remota, analítica regional, observabilidad regional |
| La latencia entre regiones es de 100 a 250 ms | Ninguno del enunciado; depende de la distancia entre regiones | Lectura de viajes compartidos (ADR-0062) |
| La vida del token de renovación es de 30 días y la de una invitación, 7 días | Ninguno; valores de producto | ADR-0060, ADR-0061 |
| La auditoría se conserva 1 año | QA-7 ("queda registrado") no fija un plazo; se usa el de ADR-0045 | ADR-0061 |
| La analítica tolera un atraso de hasta 15 minutos | RF-07 ("consultas pesadas") no pide datos en tiempo real | ADR-0064 |
| Agregar un medio con API cuesta entre 8 y 10 días-persona | QA-9 (10 días-persona); estimación por partes | ADR-0066 |
| Se guarda el 10 % de las trazas normales | CRN-2; costo de almacenamiento | ADR-0067 |
| La persona designada acepta crear una cuenta | QA-7 ("personas específicas designadas") pide identificarla | ADR-0061 |

### Impacto en otras iteraciones

Registrado en el [registro de impactos](impact-log.md):

* **Iteración 1:** la entrada global también usa `homeRegion` del token y el directorio de regiones para el login;
  la puerta de entrada reenvía entre regiones.
* **Iteración 2:** `booking.change.detected.v1` pasa a 0.2.0 (tipo abierto, `arrivalLocation`, `details`); los
  adaptadores producen los detalles según `specs/schemas/`. El recorrido de QA-9 de la iteración 2 (trenes) pasa a
  usar un medio que no existe (ferry), porque `train` ya está en el vocabulario. El `correlationId` se propaga además
  con `traceparent`.
* **Iteración 3:** `bearerAuth` y la autenticación SSE quedan definidas (ticket); la lectura de un viaje compartido
  se hace en la partición del dueño; el núcleo publica además `booking.facts.v1`; la analítica consume
  `trip.changed.v1`.
* **Segunda entrega (opción A):** un sistema de recomendación no puede usar el almacén analítico para perfiles por
  usuario; tendrá que guardar su propio perfil resumido por usuario (métricas comprimidas), calculado desde los datos
  operativos, en la región del usuario y eliminado con su cuenta.

### ¿Se sigue iterando?

Los drivers de la primera entrega quedan cubiertos por diseño. Queda una iteración 5 opcional para el riesgo de
QA-1 a escala, y después la evaluación final.

### Evaluación final de la arquitectura

Antes de entregar, repasar todos los escenarios (H, H) con *Scenario Walkthrough* y hacer una sesión de
*Risk Storming* sobre la vista C&C y la de despliegue.

### Prototipo

| Qué demuestra | Cómo | Spec | ADRs |
|---|---|---|---|
| Validación de tokens | Proveedor de identidad local; la puerta rechaza tokens vencidos, con firma inválida y de otra región | `itinerary-api.v1.yaml` | 0060 |
| Ticket SSE | Un ticket abre una conexión una sola vez | `itinerary-api.v1.yaml` | 0060 |
| Compartición y auditoría | Invitar, aceptar, leer, reenviar el enlace a otra cuenta, revocar; cada intento queda en la auditoría | `itinerary-api.v1.yaml`, `access-audit.md` | 0061 |
| Lectura entre regiones | Dos instancias locales como dos regiones; reenvío por prefijo | `itinerary-api.v1.yaml` | 0062 |
| Anonimización | Un `booking.facts.v1` se guarda sin identificadores ni `correlationId` | `booking-facts.v1.yaml` | 0064 |
| Medio nuevo | Agregar `ferry` con su esquema y un adaptador simulado, y verificar en el historial que no cambió código de los otros medios | `specs/schemas/` | 0066 |
| Trazas | Una novedad simulada genera una traza con el mismo `correlationId` en ingesta, núcleo y notificador | `ingestion-operations.md` | 0067 |

El directorio global, el canal mTLS real y el despliegue multirregión se documentan, pero no se simulan en el
prototipo local.
