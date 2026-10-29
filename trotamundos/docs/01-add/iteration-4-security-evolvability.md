# Iteración 4 — Seguridad, compartición, analítica, internacionalización y evolucionabilidad

**Responsable:** Ambos (Tadeo Brun y Tomas Lateana)
**Fecha:** 2026-10-28
**Estado:** diseño integrado en `main` mediante PR #7; ADRs aceptadas documentalmente.
Validación de implementación y riesgos pendientes según [cierre de primera entrega](../04-evaluation/first-delivery-review.md).
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
| CON-2 | Las redes sociales son sistemas externos que no podemos modificar: hay que usar lo que ya entienden para mostrar un enlace (metadatos estándar) |
| CON-3 (suposición, se mantiene) | Persistencia regional del estado autoritativo; el tránsito de respuestas compartidas y las excepciones de directorio e invitaciones se declaran en ADR-0062. Falta validar CON-3 |
| CON-4 | La app móvil nativa formatea con las librerías del sistema y guarda catálogos de textos |
| CON-5 (suposición) | No se reserva capacidad ociosa: el proveedor de identidad, la analítica y el colector escalan de forma reactiva como los demás procesos (ADR-0043) |

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
| Analítica | Fuente de datos, almacén y seudonimización |
| Clientes web y móvil | Login, ticket SSE, catálogos de textos, formato, vista genérica de reservas |
| Todos los procesos | Trazas, métricas y logs |

## Paso 4 — Patrones y tácticas elegidos

### 4.0 Arquitectura de referencia

Se mantiene la arquitectura de referencia de ADR-0004 (cliente rico, aplicación de servicios detrás de una puerta de
entrada única). Esta iteración la refina sin cambiarla: la puerta de entrada valida tokens, enruta por prefijo de
región y registra los rechazos previos al núcleo; los clientes ricos asumen el formato y los textos (ADR-0065). La
única excepción acotada es la página HTML de la tarjeta para redes, que sirve el núcleo porque los robots de las
redes no ejecutan la aplicación web (ADR-0063).

### 4.1 Patrones

| Patrón | Cómo se aplica | Drivers | ADR |
|---|---|---|---|
| *Federated Identity* (OpenID Connect / OAuth 2.0) con token firmado | Un proveedor de identidad por región emite tokens de 15 min; la puerta de entrada los valida sin consultar | QA-7, QA-5 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md) |
| *Gateway Routing* | La entrada global enruta por región de origen; la puerta de entrada reenvía a la región del dueño de un viaje compartido | CON-3, RF-08 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md), [0062](../03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md) |
| *Publish-Subscribe* y *Transactional Outbox* (iteraciones 1 y 2) | El núcleo publica `booking.facts.v1` para la analítica en la misma transacción que el cambio | RF-07 | [0064](../03-adr/0064-analitica-regional-seudonimizada.md) |
| Almacén analítico separado | Copia regional de los hechos, seudonimizada, para consultas pesadas | RF-07, QA-5 | [0064](../03-adr/0064-analitica-regional-seudonimizada.md) |
| Modelo con campos comunes y extensión por tipo (esquema por tipo) | Bloque `details` validado contra `specs/schemas/` | QA-9 | [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) |
| Catálogos de recursos externos (*externalized strings*) | Textos de la interfaz fuera del código, por idioma | QA-10 | [0065](../03-adr/0065-internacionalizacion-en-el-cliente.md) |
| *Distributed Tracing* con identificador de correlación | `correlationId` y `traceparent` desde la ingesta hasta el cliente | CRN-2, QA-1 | [0067](../03-adr/0067-observabilidad-con-trazas-y-metricas.md) |

### 4.2 Tácticas

Nombres según Bass, Clements y Kazman (4ta edición).

| Atributo | Táctica | Cómo se aplica | Drivers | ADR |
|---|---|---|---|---|
| Seguridad | Autenticar actores | Token firmado en cada solicitud; mTLS y validación del token entre regiones | QA-7 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md), [0062](../03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md) |
| Seguridad | Autorizar actores | Permiso por viaje y persona en `comparticion`, verificado en todo pedido sobre un viaje ajeno; aceptación solo con el email invitado (`emailHmac`); el dueño quita el permiso con efecto en la siguiente lectura | QA-7 | [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md) |
| Seguridad | Limitar el acceso | Solo la puerta de entrada recibe solicitudes externas; el ticket SSE solo abre la conexión de avisos; un token de otra región solo se acepta por el canal mTLS | QA-7 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md) |
| Seguridad | Limitar la exposición | Vista compartida sin notas ni códigos; `details` omitido de la vista compartida; `404` en lugar de `403`; tarjeta pública sin reservas; respuestas remotas sin persistencia en la puerta del lector; directorio con HMAC calculado en el servidor; analítica seudonimizada; logs sin datos personales | QA-7, CON-3 | [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md), [0062](../03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md), [0063](../03-adr/0063-tarjeta-de-resumen-para-redes-sociales.md), [0064](../03-adr/0064-analitica-regional-seudonimizada.md), [0067](../03-adr/0067-observabilidad-con-trazas-y-metricas.md) |
| Seguridad | Revocar el acceso (reaccionar a ataques) | Bloquear una cuenta comprometida revoca su token de renovación | QA-7 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md) |
| Seguridad | Auditar | Registro de solo agregado de cada intento sobre viajes compartidos, escrito antes de responder por el núcleo y por la puerta de entrada | QA-7 | [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md) |
| Seguridad | Detectar intrusiones | Alerta ante un aumento de rechazos sobre un mismo viaje o de un mismo actor | QA-7 | [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md), [0067](../03-adr/0067-observabilidad-con-trazas-y-metricas.md) |
| Modificabilidad | Abstraer servicios comunes | Campos comunes que usa toda la lógica del núcleo | QA-9 | [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) |
| Modificabilidad | Encapsular y restringir dependencias | Lo propio de cada medio queda en `details`; el núcleo y el panel no dependen de esos campos | QA-9 | [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) |
| Modificabilidad | Diferir el enlace | Esquemas registrados por configuración y cargados al arrancar; catálogos de textos descargados en ejecución | QA-9, QA-10 | [0065](../03-adr/0065-internacionalizacion-en-el-cliente.md), [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) |
| Integrabilidad | Adherir a estándares | OpenID Connect, ISO 8601, zonas IANA, ISO 4217, Unicode CLDR, JSON Schema, Open Graph, OpenTelemetry y W3C Trace Context | QA-7, QA-9, QA-10, CRN-2 | 0060, 0063, 0065, 0066, 0067 |
| Performance | Mantener múltiples copias de los datos | Almacén analítico separado de la base operativa | QA-5 | [0064](../03-adr/0064-analitica-regional-seudonimizada.md) |
| Disponibilidad | *Monitor* | Métricas, trazas y alertas de disponibilidad, conmutaciones, colas y tiempos por etapa de QA-1; el monitor de base también vigila el registro de auditoría | QA-4, QA-1, CRN-2 | [0067](../03-adr/0067-observabilidad-con-trazas-y-metricas.md), [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md) |
| Disponibilidad | *Redundant spare* | Proveedor de identidad en dos zonas por región; registro de auditoría con réplica sincrónica | QA-4 | [0060](../03-adr/0060-identidad-por-region-con-tokens.md), [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md) |

## Paso 5 — Instanciación

### Elementos nuevos o refinados

| Elemento | Tipo | Responsabilidades |
|---|---|---|
| Proveedor de identidad | Proceso nuevo, por región, en dos zonas | Login, emisión y renovación de tokens, revocación; guarda credenciales y emails de los usuarios de su región |
| Directorio global de regiones | Componente global nuevo, mínimo | Traduce `HMAC(email)` a región de origen para el login; guarda un seudónimo por usuario (aceptado por proporcionalidad frente a CON-3) |
| Entrada global | Refinada | Calcula el HMAC del email con su clave y consulta el directorio en el login (con límite de tasa); elige la región por `homeRegion` del token, o por el prefijo de región del recurso si no hay token |
| Puerta de entrada | Refinada | Valida firma y vencimiento de los tokens; rechaza tokens de otra región salvo por el canal mTLS; reenvía por mTLS a la región del dueño los recursos con otro prefijo de región; emite y valida tickets SSE firmados; registra en la auditoría los rechazos previos al núcleo; sirve los catálogos de textos |
| Núcleo / `usuarios` | Módulo refinado | Perfil con idioma y país; referencias a viajes compartidos conmigo, que registra la app con `POST /shared/trips` |
| Núcleo / `comparticion` | Módulo con contenido (estaba vacío) | Invitaciones (con `emailHmac`), aceptación, permisos, quita de permisos, vista compartida y tarjeta para redes; intercepta todo pedido sobre un viaje ajeno; escribe la auditoría |
| Registro de auditoría | Almacén nuevo, por región, operado como un nodo más de la base (ADR-0042) | Registros de solo agregado de los intentos sobre viajes compartidos ([access-audit.md](../../specs/access-audit.md)) |
| Núcleo / `reservas` | Módulo refinado | Campos comunes; valida y guarda `details` según el esquema registrado; publica `booking.facts.v1` |
| Analítica | Proceso refinado | Consume `booking.facts.v1` y `trip.changed.v1`, seudonimiza y guarda |
| Almacén analítico | Almacén nuevo, por región | Hechos seudonimizados para consultas pesadas |
| Colector de observabilidad | Componente nuevo, por región | Recibe trazas, métricas y logs de todos los procesos; alertas |
| Clientes web y móvil | Refinados | Login con el proveedor de su región, renovación del token, ticket SSE, catálogos, formato CLDR, vista genérica de reservas |

### Reglas de interacción

| Regla | Justificación |
|---|---|
| Ninguna solicitud externa llega al núcleo ni al notificador sin pasar por la puerta de entrada con un token válido (o un ticket SSE); la única excepción es la página pública de la tarjeta para redes | Autenticar actores (ADR-0060, ADR-0063) |
| Un token de otra región solo se acepta si llega por el canal mTLS entre puertas de entrada y para un recurso con el prefijo de la región que lo recibe | Reenvío entre regiones sin abrir la puerta a tokens ajenos (ADR-0060, ADR-0062) |
| Un recurso con prefijo de otra región se reenvía a esa región; la respuesta no se guarda en la región del lector; la puerta no aplica reglas de dominio | No copiar datos personales (ADR-0062, CON-3) |
| Todo pedido sobre un viaje ajeno, por cualquier endpoint, pasa por `comparticion`, que verifica el permiso y escribe la auditoría antes de responder; los rechazos previos al núcleo los registra la puerta de entrada; si la auditoría falla, se rechaza | QA-7 al 100 % (ADR-0061) |
| La analítica no lee la base operativa; solo consume eventos y guarda lo seudonimizado | Separar cargas y no guardar datos personales (ADR-0064) |
| El núcleo y el panel no interpretan `details` | QA-9 (ADR-0066) |
| El backend no devuelve textos traducidos ni fechas formateadas | El panel no depende del idioma (ADR-0065) |
| Ningún log, traza ni métrica lleva emails, nombres, códigos de reserva ni tokens | CON-3 (ADR-0067) |

### Tiempos y valores de diseño

| Qué | Valor | Origen |
|---|---|---|
| Vida del token de acceso | 15 min | Ventana máxima de un token revocado (ADR-0060) |
| Vida del token de renovación | 30 días, revocable | Valor de producto (suposición) |
| Vida del ticket SSE | 30 s, firmado, sin control de uso único | Alcanza para abrir la conexión y se valida sin estado compartido (ADR-0060) |
| Vigencia de una invitación | 7 días | Valor de producto (suposición, ADR-0061) |
| Retención de la auditoría | 1 año | Mismo plazo que los viajes (ADR-0045; suposición) |
| Cambio y destrucción de la clave de seudonimización | Anual | Alinea la analítica con la eliminación de viajes (ADR-0064) |
| Tamaño mínimo de un grupo para exportar agregados analíticos | 20 reservas | Evitar que un agregado identifique a una persona (suposición, ADR-0064) |
| Muestreo de trazas | Todas las lentas o con error; 10 % de las normales | Costo de almacenamiento (suposición, ADR-0067) |

### Contratos nuevos o modificados

| Contrato | Archivo | Cambio |
|---|---|---|
| API de itinerarios | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) | 0.3.0: `bearerAuth` concreto (JWT de 15 min con `emailHmac`, excepción por el canal entre regiones); ticket SSE firmado; invitaciones, aceptación, quita de permisos, viajes compartidos y referencias (`POST`/`DELETE /shared/trips`); tarjeta para redes; `POST /telemetry/panel-shown`; `correlationIds` en el evento SSE; `type` como código abierto, `details`, `arrivalLocation`, zonas IANA y `price` (ISO 4217); identificadores con prefijo de región |
| Hechos de reservas para la analítica | [booking-facts.v1.yaml](../../specs/asyncapi/booking-facts.v1.yaml) | Nuevo; solo campos permitidos, sin códigos ni textos; incluye la fecha de creación de la reserva |
| Novedades de reservas | [booking-change-detected.v1.yaml](../../specs/asyncapi/booking-change-detected.v1.yaml) | 0.2.0: tipo abierto, `arrivalLocation`, zonas IANA y `details` (cambio sobre el contrato de la iteración 2, ver el registro de impactos) |
| Avisos de cambio del panel | [panel-changed.v1.yaml](../../specs/asyncapi/panel-changed.v1.yaml) | 0.2.0: `correlationIds` opcional, para medir QA-1 de punta a punta (contrato de la iteración 3) |
| Todos los AsyncAPI | `specs/asyncapi/*.v1.yaml` | Encabezado `traceparent` declarado en cada mensaje (ADR-0067) |
| Esquemas de detalles | [specs/schemas/](../../specs/schemas/README.md) | Nuevos: `flight.v1` y `train.v1` como ejemplos del formato; reglas de versionado y de datos prohibidos |
| Registro de auditoría | [access-audit.md](../../specs/access-audit.md) | Nuevo: quién escribe (núcleo y puerta de entrada), acciones, campos y reglas |
| Cambios confirmados de reservas y viajes | `booking-confirmed.v1.yaml`, `trip-changed.v1.yaml` | Sin cambios; `trip.changed.v1` lo consume la analítica |

## Paso 6 — Vistas actualizadas y ADRs creadas

| Vista | Qué cambió |
|---|---|
| [Vista C&C](../02-views/cc-view.md) | Proveedor de identidad, registro de auditoría (escrito por el núcleo y la puerta), almacén analítico, colector de observabilidad, reenvío entre regiones, `booking.facts.v1` |
| [Vista de despliegue](../02-views/deployment-view.md) | Directorio global con HMAC, proveedor de identidad en dos zonas, auditoría como nodo de la base, almacén analítico, colector, canal mTLS entre regiones |
| [Vista de módulos](../02-views/module-view.md) | Contenido de `comparticion`, refinamiento de `usuarios` y `reservas`, esquemas por tipo |
| [Vistas de secuencia](../02-views/sequence-views.md) | SEQ-5 (compartir y leer un viaje desde otra región) y SEQ-7 (login y conexión SSE) |
| [Modelo de dominio](../02-views/domain-model.md) | Invitación y permiso, referencia a viaje compartido, registro de auditoría, detalles por tipo, preferencias de idioma |
| [Interfaces](../02-views/interfaces.md) | API 0.3.0, `booking.facts.v1`, esquemas de detalles |

| ADR | Título | Estado |
|---|---|---|
| [0060](../03-adr/0060-identidad-por-region-con-tokens.md) | Autenticación con un proveedor de identidad por región y tokens de vida corta | Aceptada documentalmente |
| [0061](../03-adr/0061-comparticion-con-cuenta-y-auditoria.md) | Compartición con personas designadas con cuenta, control en el núcleo y auditoría | Aceptada documentalmente |
| [0062](../03-adr/0062-lectura-de-viajes-compartidos-entre-regiones.md) | Lectura remota de viajes compartidos en la región del dueño | Aceptada documentalmente |
| [0063](../03-adr/0063-tarjeta-de-resumen-para-redes-sociales.md) | Tarjeta de resumen pública para compartir en redes sociales | Aceptada documentalmente |
| [0064](../03-adr/0064-analitica-regional-seudonimizada.md) | Almacenes analíticos regionales, con los eventos seudonimizados al entrar | Aceptada documentalmente |
| [0065](../03-adr/0065-internacionalizacion-en-el-cliente.md) | Internacionalización: catálogos remotos, datos neutros y formato en el cliente | Aceptada documentalmente |
| [0066](../03-adr/0066-detalles-de-reserva-extensibles-por-tipo.md) | Reserva con campos comunes y detalles con esquema propio por tipo | Aceptada documentalmente |
| [0067](../03-adr/0067-observabilidad-con-trazas-y-metricas.md) | Observabilidad con trazas distribuidas, métricas por etapa y logs estructurados | Aceptada documentalmente |

## Paso 7 — Análisis

Recorrido de escenarios sobre el diseño (*Scenario Walkthrough*). Son resultados esperados por diseño, no
mediciones.

### Recorridos

| Escenario | Recorrido | Resultado esperado | Límite o riesgo |
|---|---|---|---|
| QA-7: una persona no designada, con cuenta, abre el enlace de un viaje compartido | Puerta de entrada valida su token → (reenvío si el viaje es de otra región) → `comparticion` no encuentra permiso → escribe la auditoría → `404` | Rechazado y registrado | — |
| QA-7: alguien recibe el email de invitación reenviado e intenta aceptar, antes o después que la persona designada | `POST /shares/{id}/accept` → el `emailHmac` de su token no es el de la invitación → auditoría (`email_mismatch`) → `404` | Solo una cuenta con el email invitado puede aceptar | Si la persona designada comparte las credenciales de su email, no hay forma técnica de distinguirla |
| QA-7: un usuario pide un viaje ajeno por el endpoint del dueño (`GET /trips/{tripId}`) | El núcleo ve que el viaje no es suyo → `comparticion` → auditoría (`owner_endpoint`) → `404` | Rechazado y registrado, aunque tenga permiso de lectura compartida | — |
| QA-7: solicitud sin token o con token vencido sobre un recurso de compartición | La puerta de entrada responde `401` y registra `share.gateway_reject` (`unauthenticated`) en la auditoría de su región | Rechazado y registrado, sin llegar al núcleo | — |
| QA-7: la región del dueño no responde, o el identificador trae una región inexistente | La puerta de entrada del lector responde `503` o `404` y registra el rechazo en la auditoría de su región | Rechazado y registrado | — |
| QA-7: el dueño quita el permiso y la persona intenta leer | El permiso ya no existe → auditoría → `404` | Efecto en la siguiente lectura | — |
| QA-7: la auditoría no se puede escribir | El núcleo o la puerta no responden con datos → `503`; el evento queda en los logs estructurados con una alerta | Rechazado siempre; registrado en los logs | Si fallan a la vez la auditoría y los logs de la región, el rechazo no queda registrado (riesgo residual) |
| QA-7: token robado | Sirve hasta 15 minutos; el token de renovación se revoca | Ventana acotada | Riesgo aceptado (ADR-0060) |
| RF-08: Ana (Europa) acepta y ve un viaje de Juan (Sudamérica) | Acepta con su cuenta (reenvío por mTLS) → la app registra la referencia en Europa con `POST /shared/trips` → al abrirlo, puerta de Europa → mTLS → puerta de Sudamérica acepta el token de Ana por venir del canal → núcleo verifica, audita y responde | Ana ve la respuesta autorizada, que transita por Europa sin persistirse en su puerta | Suma la red entre regiones (100 a 250 ms, suposición); si Sudamérica no responde, `503` |
| Redes sociales: Juan publica su viaje | `POST /trips/{id}/social-card` → enlace `/cards/{id}` con prefijo de región → el robot de la red llega sin token, la entrada global lo enruta por el prefijo → página con Open Graph | Se publica destino, mes y días | El itinerario no se publica: es la interpretación elegida. Publicar el mes indica cuándo el viajero está de viaje; la app lo advierte |
| RF-07: el equipo de datos consulta destinos más reservados del año | Consulta pesada en el almacén analítico de cada región; se combinan los resultados | Sin efecto en el panel de los viajeros | Tendencias globales armadas fuera del sistema |
| RF-07: se elimina un viaje (ADR-0045) | Se mantiene retención de hechos seudonimizados, con control de recepción separado | No se afirma anonimato por destruir la clave | Falta validar retención y riesgo de reidentificación frente a CON-3; período cerrado sin clave produce resolución pendiente |
| RF-07: tasa de cancelación y anticipación | Cada hecho de cancelación trae la fecha de creación de la reserva | Se calcula sin vincular eventos | Una reserva creada y cancelada en períodos de clave distintos aparece con dos códigos |
| QA-10: un usuario argentino usa la app en inglés durante un viaje a Japón | La entrada global lo envía a Sudamérica (su región); el panel llega con fechas ISO 8601, zona IANA y montos con moneda; la app formatea en inglés y muestra cada hora en la zona del lugar | Textos y formatos según su configuración | Ver el presupuesto de latencia de QA-2 fuera de la región, abajo |
| QA-10 con QA-3: abrir la app | Usa el panel en caché y el catálogo ya guardado; nada depende del idioma | QA-3 sin cambios | Un idioma recién agregado se descarga en segundo plano |
| QA-9: agregar ferry | Esquema `details-ferry.v1.json` y código `ferry` → adaptador nuevo en la ingesta → registro del esquema en el núcleo por configuración → vista del detalle en clientes y textos en catálogos | Sin cambios en el código de los otros medios ni en `viajes`, `reservas` y `panel`; entre 8 y 10 días-persona (suposición) | Si el proveedor solo manda correos, el extractor puede superar los 10 días. Si la app vieja recibe `ferry`, lo muestra con la vista genérica |
| CRN-2 con QA-1: medir una novedad | El `correlationId` nace en la ingesta → `booking.change.detected.v1` → transacción del núcleo → `panel.changed.v1` (`correlationIds`) → evento SSE → la app lo informa con `POST /telemetry/panel-shown`; `traceparent` en todos los encabezados | Tiempo por etapa del presupuesto de 300 s | Hay que propagar el contexto a través de RabbitMQ en todos los procesos |
| CRN-2 con QA-4: medir la inactividad | Sondas externas cada 5 s por región y partición, intervalos consolidados y conmutaciones | Segundos de indisponibilidad comparables con 300 s/mes | Cobertura e incertidumbre declaradas; no confundir tasa de éxitos con minutos |

### Presupuesto de latencia de QA-2 fuera de la región (QA-10)

QA-10 pide cumplir QA-2 (800 ms) aunque el usuario esté fuera de su región. Las iteraciones 1 y 3 solo nombraron el
límite; acá se estima el peor caso habitual: un usuario de Sudamérica en Japón, con un tiempo de ida y vuelta (RTT)
de 260 a 300 ms (suposición) y 50 a 100 ms de servidor (lectura por clave, iteración 3).

| Situación | Viajes de ida y vuelta | Tiempo estimado | ¿Cumple 800 ms? |
|---|---|---|---|
| Conexión ya abierta (HTTP/2 reutilizado, el caso normal con la app en uso y SSE abierto) | 1 | 310 a 400 ms | Sí |
| Conexión nueva con TLS 1.3 (TCP + TLS + solicitud) | 3 | 830 a 1000 ms | No |
| Conexión nueva con reanudación de TLS 1.3 sin espera (0-RTT) | 2 | 570 a 700 ms | Sí, justo |

Resultado: con la conexión abierta se cumple; la primera solicitud de una conexión nueva desde muy lejos puede
superar los 800 ms. Como QA-2 se mide sobre el 95 % de las solicitudes, se cumple mientras esos casos sean menos del
5 % del total (suposición). Mitigación candidata, no decidida: terminar TLS en la entrada global cerca del usuario y
mantener conexiones abiertas entre la entrada y cada región. Queda como riesgo aceptado y para una iteración 5.

### Estado de los drivers

| Driver | Estado | Qué falta |
|---|---|---|
| QA-7 | Cumplido por diseño | Rechazo garantizado en todos los caminos y registro en todos (núcleo y puerta); riesgo residual si fallan a la vez la auditoría y los logs de la región; la ventana de 15 minutos de un token robado es un riesgo aceptado. Pruebas del prototipo (designado, no designado, enlace reenviado antes y después de aceptar, endpoint del dueño, sin token, permiso quitado) |
| RF-08 | Cumplido por diseño | Sin avisos en vivo de viajes compartidos |
| Redes sociales | Cumplido con la interpretación de la tarjeta | Confirmar la interpretación con la cátedra |
| RF-07 | Diseño propuesto con recepción idempotente y consultas delimitadas | Validar consultas, retención, reidentificación y hechos tardíos sin clave; no hay vista global automática |
| QA-10 | Parcial | Textos y formatos cumplidos por diseño; QA-2 fuera de la región se cumple con la conexión abierta, pero una conexión nueva desde muy lejos puede superar 800 ms (riesgo aceptado, ver el presupuesto). Probar dos idiomas y zonas horarias |
| QA-9 | Cumplido por diseño | Medir el esfuerzo real agregando un medio al prototipo |
| CRN-2 | Diseño de trazas y medición propuesto | Verificar propagación, sondas temporales, cobertura de telemetría y desfase de reloj según quality-measurement.md |

### Riesgos

| Riesgo | Driver | Tratamiento |
|---|---|---|
| Un token de acceso robado o revocado sirve hasta 15 minutos | QA-7 | Aceptado; la vida corta acota la ventana |
| Si la auditoría falla, las lecturas compartidas se rechazan | QA-7 frente a QA-4 | Aceptado: QA-7 exige el 100 %; el registro de auditoría se opera como un nodo de la base, con el mismo monitor y la misma conmutación |
| Si fallan a la vez la auditoría y los logs de la región, un rechazo no queda registrado | QA-7 | Riesgo residual aceptado; el rechazo igual ocurre |
| Las claves del directorio (entrada global) y de `emailHmac` (común a los proveedores de identidad) son secretos globales | QA-7, CON-3 | Custodia en el gestor de secretos (CRN-4); su filtración permite vincular seudónimos, no leer emails |
| Un ticket SSE copiado sirve 30 s para abrir otra conexión de avisos | QA-7 | Aceptado: los avisos no llevan datos de reservas |
| Una primera solicitud desde muy lejos de la región de origen puede superar 800 ms | QA-10, QA-2 | Aceptado; mitigación candidata para la iteración 5 (TLS en la entrada global cerca del usuario) |
| Hecho nuevo de período cuya clave ya se destruyó | RF-07 | Resolución durable; no regenerar clave ni cambiar período. Medir cobertura de hechos tardíos |
| La lectura compartida entre regiones depende de la otra región y suma latencia | RF-08, QA-2 | Aceptado; medir la latencia entre regiones |
| El directorio global guarda un seudónimo por usuario fuera de su región y, si cae, no se puede iniciar sesión desde un dispositivo nuevo | QA-4, CON-3 | Aceptado por proporcionalidad (ADR-0060); se replica en varias regiones y la app recuerda la región del último login |
| Retención de hechos tras eliminar una cuenta | CON-3 | La retención elegida requiere validación; destruir la clave no demuestra anonimato ni fija por sí solo un plazo suficiente |
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
| El RTT desde el lugar más lejano habitual hasta la región de origen es de 260 a 300 ms, y las primeras solicitudes de conexiones nuevas desde muy lejos son menos del 5 % | QA-10 ("aunque el usuario esté fuera de su región") | Presupuesto de latencia de QA-2 fuera de la región |
| Un agregado analítico exportable tiene al menos 20 reservas | RF-07 (tendencias de destinos); evitar identificar personas | ADR-0064 |
| La vida del token de renovación es de 30 días y la de una invitación, 7 días | Ninguno; valores de producto | ADR-0060, ADR-0061 |
| La auditoría se conserva 1 año | QA-7 ("queda registrado") no fija un plazo; se usa el de ADR-0045 | ADR-0061 |
| La analítica tolera un atraso de hasta 15 minutos | RF-07 ("consultas pesadas") no pide datos en tiempo real | ADR-0064 |
| Agregar un medio con API cuesta entre 8 y 10 días-persona | QA-9 (10 días-persona); estimación por partes | ADR-0066 |
| Se guarda el 10 % de las trazas normales | CRN-2; costo de almacenamiento | ADR-0067 |
| La persona designada acepta crear una cuenta | QA-7 ("personas específicas designadas") pide identificarla | ADR-0061 |

### Impacto en otras iteraciones

Registrado en el [registro de impactos](impact-log.md):

* **Iteración 1:** la entrada global también usa `homeRegion` del token, el prefijo de región de los recursos y el
  directorio de regiones para el login; la puerta de entrada reenvía entre regiones y registra rechazos en la
  auditoría; la tarjeta para redes es una excepción acotada a ADR-0004.
* **Iteración 2:** `booking.change.detected.v1` pasa a 0.2.0 (tipo abierto, `arrivalLocation`, `details`); los
  adaptadores producen los detalles según `specs/schemas/`. El recorrido de QA-9 de la iteración 2 (trenes) pasa a
  usar un medio que no existe (ferry), porque `train` ya está en el vocabulario. El `correlationId` se propaga además
  con `traceparent` en los encabezados de todos los mensajes.
* **Iteración 3:** `bearerAuth` y la autenticación SSE quedan definidas (ticket firmado); la lectura de un viaje
  compartido se hace en la partición del dueño; el núcleo publica además `booking.facts.v1`; la analítica consume
  `trip.changed.v1`; `panel.changed.v1` pasa a 0.2.0 con `correlationIds`; el monitor de base también vigila el
  registro de auditoría.
* **Segunda entrega (opción A):** un sistema de recomendación no puede usar el almacén analítico para perfiles por
  usuario; tendrá que guardar su propio perfil resumido por usuario (métricas comprimidas), calculado desde los datos
  operativos, en la región del usuario y eliminado con su cuenta.

### ¿Se sigue iterando?

Los drivers tienen diseño documentado con los refinamientos propuestos en esta revisión. QA-10 sigue parcial
por latencia internacional; QA-1 a escala sigue abierto y CON-3 requiere validar retención y transferencias. Las
pruebas de cobertura de auditoría, exposición compartida, recepción analítica y medición forman parte de la
evaluación antes de declarar cumplimiento. La iteración 5 puede refinar los riesgos registrados; no los elimina
por su sola clasificación como aceptados.

### Evaluación final de la arquitectura

La revisión analítica transversal y el recorrido de los escenarios están registrados en
[el cierre documental](../04-evaluation/first-delivery-review.md). Incluye riesgos sobre componentes y despliegue.
No se atribuye una sesión grupal de Risk Storming ni pruebas de prototipo que no se hayan realizado.

### Prototipo

| Qué demuestra | Cómo | Spec | ADRs |
|---|---|---|---|
| Validación de tokens | Proveedor de identidad local; la puerta rechaza tokens vencidos, con firma inválida y de otra región fuera del canal entre regiones | `itinerary-api.v1.yaml` | 0060 |
| Ticket SSE | Un ticket vencido no abre la conexión; uno vigente sí | `itinerary-api.v1.yaml` | 0060 |
| Compartición y auditoría | Invitar, aceptar con el email invitado, intentar aceptar con otra cuenta, leer, pedir por `/trips/{tripId}`, pedir sin token, quitar el permiso; cada intento queda en la auditoría | `itinerary-api.v1.yaml`, `access-audit.md` | 0061 |
| Lectura entre regiones | Dos instancias locales como dos regiones; reenvío por prefijo y registro de la referencia con `POST /shared/trips` | `itinerary-api.v1.yaml` | 0062 |
| Seudonimización y recepción | Un hecho se guarda con códigos, sin identificadores originales ni correlationId; reentrega no duplica y la rotación conserva el período de commit | `booking-facts.v1.yaml` | 0064 |
| Medio nuevo | Agregar `ferry` con su esquema y un adaptador simulado, y verificar en el historial que no cambió código de los otros medios | `specs/schemas/` | 0066 |
| Trazas | Una novedad simulada genera una traza con el mismo `correlationId` en ingesta, núcleo y notificador, y el cliente de prueba la cierra con `POST /telemetry/panel-shown` | `panel-changed.v1.yaml`, `itinerary-api.v1.yaml` | 0067 |

Estado: implementados los tokens, el ticket SSE, la compartición con auditoría, la lectura entre regiones y las
trazas, con pruebas en `prototype/tests/test_iteracion4_comparticion.py` y `test_contratos.py`. La seudonimización
y el medio nuevo (`ferry`) quedaron fuera del alcance del prototipo, así que QA-9 sigue sin medición de esfuerzo. El
prototipo simula dos regiones y el directorio global (en la entrada global); el canal entre regiones usa una clave
compartida en lugar de mTLS. Ver [prototype/README.md](../../prototype/README.md).

### Revisión de la iteración

La iteración se revisó con una auditoría independiente (un revisor sin el contexto de las decisiones). Antes de
corregir, el equipo decidió tres puntos:

* la invitación se ata al email invitado;
* se auditan todos los caminos de acceso;
* se mantiene la clave anual de la analítica, declarando su consecuencia.

Las correcciones aplicadas fueron:

* **QA-7:**
  * aceptación de invitaciones solo con el email invitado (`emailHmac`, ADR-0060 y ADR-0061);
  * todo pedido sobre un viaje ajeno pasa por `comparticion`;
  * la puerta de entrada registra los rechazos previos al núcleo (`access-audit.md`).
* **Entre regiones:**
  * excepción para tokens de otra región por el canal mTLS (ADR-0060, `bearerAuth`);
  * referencia del viaje compartido registrada por la app con `POST /shared/trips` y no por la puerta de entrada
    (ADR-0062).
* **Directorio global:** HMAC calculado en la entrada global, justificación frente a CON-3 y consecuencias negativas
  (ADR-0060).
* **Observabilidad:** `correlationIds` en `panel.changed.v1` y en el evento SSE, `traceparent` en los AsyncAPI y
  `POST /telemetry/panel-shown` (ADR-0067).
* **Analítica (ADR-0064):**
  * hechos tardíos y corte de cancelaciones por la rotación de la clave, declarados;
  * fecha de creación en `booking.facts.v1`;
  * regla de agregados exportables.
* **QA-10:** presupuesto de latencia fuera de la región; QA-10 pasa a parcial.
* **Registro de auditoría:** se opera como un nodo de la base, con el mismo monitor.
* **Enrutamiento sin token:** prefijo de región en `cardId` y en el ticket SSE; ticket firmado sin estado compartido.
* **Esquemas de detalles:** versionado sin ambigüedad, carga por configuración y prohibición de códigos y datos
  personales en `details`.
* **Tarjeta para redes:** excepciones explícitas a ADR-0004 y ADR-0065, y borrado con el viaje.
* **Nombres de tácticas según Bass:**
  * *revocar el acceso* solo para cuentas comprometidas;
  * *monitor* en lugar de *grabar y reproducir*;
  * se agrega *detectar intrusiones*;
  * se quitan las tácticas mal atribuidas.
* **Paso 2 y Paso 4:** restricciones CON-2 y CON-5 corregidas, y la arquitectura de referencia explicitada en el
  Paso 4.
* **Contratos:** zonas IANA, campos editables en `BookingPatch` y `503` al quitar un permiso.
* **Documentos desactualizados:** notas en ADR-0001, ADR-0003, ADR-0004, el contrato de ingesta y el registro de
  impactos.

## Correcciones de revisión — preparación 2026-10-28

Los ajustes de esta sección quedaron integrados en el PR #7. Su adopción documental no registra ejecución
de pruebas del prototipo:

| Tema | Decisión refinada | Contrato o evidencia futura |
|---|---|---|
| Identidad | Validar emisor, audiencia, tipo, firma, algoritmo y vigencia; principal regional estable | ADR-0060 y bearerAuth; rechazar ID token o aud incorrecta |
| Exposición de detalles | El dueño conserva details; SharedBooking lo omite siempre en esta entrega | ADR-0066; probar texto sensible válido por esquema y respuesta sin el bloque |
| Auditoría | Cubrir rechazos previos al núcleo por todas las rutas de viajes y reservas, incluso de la misma región | access-audit.md; probar sin token, token inválido y 429 |
| Enrutamiento | GET compartido remoto; DELETE del marcador local aun con prefijo ajeno | Tabla de ADR-0062; probar borrado con región del dueño caída |
| Analítica | Recepción y hecho atómicos antes de ACK; período committedAt; resolución si no existe clave histórica | analytics-processing.md; reentrega, carrera, caída y cambio de año |
| QA-4 | Segundos de indisponibilidad con sondas externas y consolidación de intervalos | quality-measurement.md; caída sin tráfico y fallos solapados |
| QA-1 | Reintentar reportes, confirmar recepción durable, contar faltantes e incertidumbre de reloj | quality-measurement.md; 503, repetición y desfase horario |
| CON-3 | Diferenciar estado persistido y tránsito; seudonimización no demuestra anonimato | ADR-0062 y ADR-0064; validación de criterio y riesgo pendiente |

Los resultados de diseño del paso 7 deben leerse con estos límites: medir no demuestra automáticamente cumplimiento,
una lectura remota transmite datos y la retención analítica necesita evaluación de reidentificación. Los escenarios
adicionales deben incorporarse a la implementación antes de afirmar cobertura efectiva.
