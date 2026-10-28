# Iteración 2 — Ingesta de reservas

**Responsable de la iteración:** Tomas Lateana (integrante A).
**Preparación documental:** 2026-10-27, con asistencia de ChatGPT/Codex.
**Estado:** diseño integrado en `main` mediante PR #4; ADRs aceptadas documentalmente.
Validación de implementación y riesgos pendientes según [cierre de primera entrega](../04-evaluation/first-delivery-review.md).
**ADRs:** 0020 a 0028, dentro del bloque 0020–0039.

## Base y alcance

Base de integración: primera iteración revisada e incorporada a `main` en
`05a8fd737847cecc89722ccde9cd0824e5ffbd0f`. Se preservan el núcleo modular como único dueño del estado,
la publicación/suscripción y las regiones de origen. ADR-0003 es despliegue; ADR-0004 es clientes y API Gateway.
La separación lectura/escritura y el almacenamiento analítico no se presuponen: corresponden a 3 y 4.

Los RF/QA son los del repo. No se cambia el documento de requisitos ni se trasladan IDs de ejemplos anteriores.
Ingesta publica novedades; solo el núcleo escribe el estado autoritativo y decide la asociación reserva-viaje.
Se elige RabbitMQ como broker en ADR-0028; nube, motor de datos y proveedor de correo real se fijan al implementar sus interfaces, sin alterar los contratos.

## Paso 2 — Objetivo y drivers

Diseñar la obtención y el procesamiento de reservas desde correos autorizados y APIs de terceros, normalizando
las novedades y entregándolas al núcleo mediante mensajería persistente. Contemplar filtros, fallos, reintentos,
revocación y el plazo de actualización, sin bloquear las consultas de viajeros.

| Driver | Papel |
|---|---|
| RF-01 | Sondeo y procesamiento automático del correo |
| RF-02 | Filtros y listas de remitentes seguros configurables por usuario |
| RF-03 | Detalles, cambios y cancelaciones desde terceros |
| RF-06 | Integración con la agencia preferida para asistencia |
| QA-1 (H,H) | Frescura: cinco minutos desde generación externa hasta visualización |
| QA-6 (H,M) | El 99,9 % de los mensajes válidos se procesa sin pérdida ni duplicación |
| QA-8 (H,M) | Acceso autorizado y tratamiento limitado de correos |
| QA-5 | Escalabilidad: dimensionar consultas de detección además de novedades |
| QA-9 | Agregar un medio como trenes en 10 días-persona o menos, sin modificar el código de los medios existentes |
| CRN-3 | Errores y reintentos externos |
| CRN-4 | Configuración y secretos; ID vigente en el repo |

El percentil 99 de QA-1 es un supuesto existente, no una relajación confirmada por la consigna. Faltan cuotas y
carga concurrente para comprobar viabilidad. Detección + cola + aplicación + visualización comparten 300 segundos;
no se fija un intervalo universal sin conocer esas condiciones.

## Paso 3 — Elementos a refinar

| Elemento | Motivo |
|---|---|
| Proceso de ingesta | Obtener información y transformar novedades externas |
| Adaptadores | Encapsular contratos de cada proveedor |
| Estado de ingesta | Vinculaciones, cursores, resultados y publicación pendiente |
| Interfaz ingesta-núcleo | Acordar qué se entrega y cómo se toleran errores/reentregas |

## Paso 4 — Patrones y tácticas elegidos

| Concepto y justificación | Patrón | Táctica y aplicación | Alternativas | ADR |
|---|---|---|---|---|
| Avisos principales y reconciliación adaptable; evitar sondeo uniforme masivo | Event-Driven Consumer; consumo periódico de reconciliación | Manage sampling rate y Limit event response: frecuencia y concurrencia por cuota; QA-1 sigue condicionado | Solo sondeo; solo avisos | [0020](../03-adr/0020-obtener-novedades.md) |
| Autorización delegada del buzón | OAuth 2.0 es protocolo de autorización, no patrón arquitectónico | Authorize actors, Limit access y Revoke access: permisos mínimos y revocación coordinada | Contraseña; reenvío manual | [0021](../03-adr/0021-autorizacion-correo.md) |
| Etapas internas separadas | Pipes and Filters | Increase cohesion: cada etapa tiene una transformación definida | Rutina única; servicio por etapa | [0022](../03-adr/0022-tuberia-ingesta.md) |
| Aislar contratos de proveedores | Ports and Adapters; Adapter; Canonical Data Model | Tailor interface y Adhere to standards: mapeos específicos a contratos estables | Condicionales dispersos; modelo de un proveedor | [0023](../03-adr/0023-adaptadores-proveedores.md) |
| Resultados, cursor y publicación recuperables | Transactional Outbox; Idempotent Receiver | Retry y Exception handling: reintentos limitados y clasificación | Avanzar antes de persistir; publicar sin recuperación | [0024](../03-adr/0024-avance-y-publicacion-durable.md) |
| Resolver una región antes de recibir trabajo | Message Router | Limit access y Restrict dependencies: directorio mínimo y entrada controlada | Ingesta pública; difusión global | [0025](../03-adr/0025-enrutamiento-de-avisos.md) |
| Asistencia saliente del núcleo | Ports and Adapters; Transactional Outbox | Tailor interface, Schedule resources y Bound queue sizes: trabajador acotado separado de atención HTTP | Cliente directo; ingesta; proceso independiente | [0026](../03-adr/0026-integracion-agencia.md) |
| Publicar cambios oficiales recuperables | Transactional Outbox; Idempotent Receiver | Retry y Exception handling: publicación tras commit y reentrega segura | Publicar antes; guardar y enviar sin recuperación | [0027](../03-adr/0027-publicacion-del-nucleo.md) |
| Aislar mensajes que no se pueden aplicar | Dead Letter Channel, realizado mediante caso aparcado y aviso mínimo | Exception handling: registrar fallo durable antes del ACK, sin bucle infinito | Descartar; reintentar sin límite | [0028](../03-adr/0028-rabbitmq-y-politicas.md) |
| Broker replicado con mayoría | Cola durable replicada con líder y seguidores | Redundancia con réplica de estado y elección de líder; no se equipara a ejecución activa de negocio en todos los nodos | Kafka; cola en base | [0028](../03-adr/0028-rabbitmq-y-politicas.md) |

El canal de errores se implementa en aplicación y outbox, no se presupone un DLX automático de RabbitMQ. Los nombres
son una trazabilidad de mecanismos concretos; no sustituyen la evaluación de escenarios ni las medidas de calidad.

## Paso 5 — Componentes e interfaces

| Componente | Responsabilidad |
|---|---|
| Planificador | Elegir vinculaciones e intervalos según prioridad, cuotas y avance |
| Coordinador | Ejecutar una consulta con exclusión/versionado por vinculación |
| Gestor de vinculaciones | Consultar configuración autoritativa del núcleo mediante interfaz interna; coordinar acceso/revocación y renovación de secretos de ingesta |
| Adaptadores de acceso | Obtener correos o datos de APIs con paginación y límites |
| Receptor de avisos | Recibir desde el Gateway, verificar origen/repetición y registrar trabajo durable antes de confirmar recepción |
| Resolución regional | Usar la vinculación de suscripción a región; tratar avisos sin región como pendientes, sin difusión global |
| Asistencia saliente del núcleo (fuera de ingesta) | Autorizar solicitudes, ejecutarlas con trabajadores acotados y aplicar resultados de agencia |
| Procesador | Seleccionar, extraer, normalizar y validar; distinguir descarte de fallo |
| Registro de sincronización | Persistir cursores, resultados, casos pendientes y outbox |
| Publicador | Entregar mensajes de outbox y marcar envío tras confirmación del canal |

Los componentes de ingesta pueden compartir proceso y código. Asistencia es un módulo del desplegable del núcleo,
con un trabajador asíncrono; no se añade un proceso saliente ni se amplía la responsabilidad de ingesta.

| Interfaz interna | Entrada → salida |
|---|---|
| Ejecutar sincronización | Vinculación, versión/cursor → resultado y próxima planificación |
| Autorizar consulta | Vinculación, operación → acceso autorizado o rechazo clasificado |
| Obtener novedades | Cursor y límite → página, siguiente avance propuesto y condiciones de cuota |
| Procesar novedad | Datos externos mínimos → evento válido, descarte justificado o caso pendiente |
| Guardar avance | Resultados de la página y versión esperada → transacción confirmada o conflicto |
| Publicar pendiente | Evento con ID estable → confirmación durable del canal o fallo reintentable |

### Contrato compartido

[Contrato de ingesta](../../specs/ingestion-contract.md) y
[AsyncAPI propuesto](../../specs/asyncapi/booking-change-detected.v1.yaml). La iteración 4 lo amplió a 0.2.0 con
campos opcionales (tipo abierto, `arrivalLocation`, zonas horarias y `details`) y agregó el contexto de traza en los
encabezados de los mensajes; ver [cambios de la versión 0.2.0](../../specs/ingestion-contract.md#cambios-de-la-versión-020).
El evento `booking.change.detected.v1` no afirma que la reserva ya cambió. No exige `tripId`.
El consumidor valida vinculación/usuario, aplica reglas e idempotencia y confirma después del resultado durable.
Identidad del mensaje e identidad de la reserva son diferentes; conciliación correo/API se acuerda con iteración 3.

## Paso 6 — Vistas y decisiones registradas

| Artefacto | Contenido |
|---|---|
| [Vista de ingesta](../02-views/ingestion-view.md) | Componentes/conectores, persistencia, propiedad e interfaces |
| [Secuencias de ingesta](../02-views/ingestion-sequences.md) | Correo, avisos externos, recuperación de publicación y revocación |
| [Interfaces compartidas](../02-views/interfaces.md) | Refinamiento ingesta-núcleo y dependencia con 3 |
| ADR-0020 a 0028 | Contexto, drivers, alternativas, consecuencias y confirmación futura |
| [Impactos](impact-log.md) | Cambios que deben revisar los responsables de 1 y 3 |

Las ADR de esta iteración están aceptadas documentalmente tras la integración del PR #4 y sus refinamientos
coordinados con 3 y 4. La verificación de cuotas, carga y recuperación mantiene sus pendientes.

## Paso 7 — Análisis del diseño y cierre de la iteración

Se realiza un recorrido analítico de escenarios sobre contratos/vistas, no una prueba de software. Se seleccionó
RabbitMQ en ADR-0028 y se fijaron hipótesis operativas en [ingestion-operations.md](../../specs/ingestion-operations.md).
El análisis distingue resultados del razonamiento y evidencia que deberá producir el prototipo.

### Recorridos y resultados

| Caso analizado | Recorrido y resultado esperado por diseño | Límite o riesgo |
|---|---|---|
| Aviso perdido o suscripción vencida | Reconciliar desde cursor y renovar; prioridades distribuyen consultas | Una cuenta con respaldo de 15 min o 6 h puede incumplir QA-1; el sondeo adaptativo no resuelve el requisito a escala |
| Nuevo transporte: trenes | Implementar adaptador y mapeo contra puertos comunes; ejecutar regresión de medios existentes | QA-9 exige registrar esfuerzo real ≤10 días-persona y ausencia de cambios en medios existentes |
| Correo nuevo sin versión externa | Autorizar, filtrar, extraer identidad, deduplicar fuente, guardar outbox/cursor, publicar; núcleo puede crear reserva si datos suficientes | No se inventa versión; cambios contradictorios requieren conciliación |
| Cancelación de tercero | Entrada global resuelve suscripción, Gateway valida, ingesta normaliza; núcleo aplica o conserva cancelación pendiente hasta identificar reserva | Un aviso sin región válida no se difunde globalmente; directorio protegido es dependencia |
| Duplicado o caída tras publicar | Outbox conserva eventId; consumidor guarda control y resultado antes del ACK | Igual reserva desde dos fuentes requiere conciliación de negocio, no solo dedupe de mensaje |
| Novedades desordenadas | Shard de usuario estabiliza publicación; núcleo compara versión si existe y serializa por reserva; conflicto sin orden no sobrescribe a ciegas | RabbitMQ no reconstruye orden temporal de una fuente ni resuelve competencia con cambios manuales |
| Broker o consumidor fuera de servicio | Trabajo permanece en outbox/cola; se rechaza publicación sin espacio y se recupera consumo | Una caída prolongada viola frescura aunque no se pierda trabajo; alertar sin ocultarlo |
| Correo desvinculado | Núcleo pasa a revoking y coordina barrera; sin respuesta no confirma revocación completa; nuevos inicios denegados | Operaciones enviadas antes pueden terminar; no se promete retirar mensajes ya publicados |
| Agencia indisponible | Solicitud autorizada permanece en trabajo persistente; reintento conserva requestId; respuesta incierta se concilia | Agencia sin idempotencia exige consulta/revisión antes de duplicar una solicitud |
| Caída de nodo/zona | Quorum de tres miembros en tres zonas conserva mayoría tras una pérdida; consumidor de respaldo retoma | Failover/throughput se deben medir; demo local no prueba independencia de zonas |
| Error de datos repetido | Tras intentos acotados se aparca resultado durable y emite aviso mínimo antes de ACK | Si falla la persistencia no se confirma; contenido personal minimizado y revisión obligatoria |

### Evaluación driver por driver

| Driver | Resultado de diseño | Estado del requisito y validación futura |
|---|---|---|
| RF-01/02/03 | Recorrido de correo/APIs, filtros, adaptadores y contratos definidos | Abordados en diseño; validar con al menos dos fuentes simuladas y un correo sin versión |
| RF-06 | Contrato de asistencia y adaptador con autorización/seguimiento definidos | Abordado en diseño; agencia real/API y ensayo de fallos antes de producción |
| QA-1 | Avisos principales, recuperación y presupuesto de 300 s | Conflicto abierto: respaldo de 15 min o 6 h incumple si falta un aviso; no hay demostración universal de cuotas ni recuperación acotada |
| QA-5 | Modelo de consultas, renovaciones y carga de novedades separado | Parcial: validar distribución de buzones y cuotas por proveedor, además de carga regional del broker |
| QA-9 | Adaptadores y puertos aíslan un nuevo transporte | Agregar trenes sin editar medios existentes y registrar esfuerzo; objetivo de 10 días-persona aún sin medir |
| QA-6 | Identidad separada, normalización, dedupe durable, conciliación y outboxes definidos | Parcial hasta pruebas de contrato/reentrega/desorden; no prometer exactly-once |
| QA-8 | OAuth delegado, mínimo privilegio, propiedad y protocolo de revocación definidos | Parcial hasta pruebas de carrera, integración real, seguridad y conservación de datos |
| CRN-3 | Reintentos clasificados, pendientes y recuperación definidos | Resuelto al nivel de diseño; falta ejercitar fallos |
| CRN-4 | Secretos fuera de payload/log, roles del broker y vigencia de configuración definidos | Resuelto al nivel de diseño; infraestructura/secret store se verifica en implementación |

### Riesgos aceptados como pendientes de validación

1. QA-1 a escala sigue abierto: priorizar viajes reduce solicitudes, pero reconciliar cuentas cada 15 min o 6 h
   no recupera un aviso perdido dentro de cinco minutos. Hace falta recuperación acotada para todas las cuentas
   y cuotas verificadas, u otro diseño revisado. No se reduce el alcance por actividad del usuario.
2. Capacidad: 50/s normal, 250/s pico y 20 ms de servicio son hipótesis, no resultados. Pruebas de carga deben
   demostrar cola ≤40 s, publicación ≤10 s y recorrido ≤300 s bajo el escenario acordado con 3.
3. Política regional y secreto/token: CON-3 sigue como supuesto; los plazos operativos no prueban cumplimiento legal.
4. Broker en tres zonas y base altamente disponible: dependen del despliegue que refina 3; no hay recuperación
   entre regiones ni validación mensual en esta iteración.
5. Casos ambiguos entre correo y API: conservar y resolver evita corrupción, pero puede requerir intervención y
   no produce itinerario automáticamente hasta contar con evidencia suficiente.

### Dependencias de implementación y refinamientos pendientes

La iteración 3 implementa autorización por viaje, persistencia y consumidor con este contrato; elige actualización
visible del cliente dentro del presupuesto y demuestra latencia web. La 4 define autenticación del viajero,
compartición y almacén analítico. La seguridad OAuth del correo y la publicación confiable ya se deciden aquí.
La release/digest, secretos y configuración del despliegue se fijan al implementar y se comprueban con las fuentes
oficiales; no se dejan como elecciones arquitectónicas abiertas de broker.

### Prototipo y criterios de aceptación

[Plan de validación](../../prototype/ingestion-validation.md). Debe cubrir correo sin versión, dos fuentes,
duplicado, cancelación antes del alta, caídas antes/después de commit/confirm, mensaje no enrutado, revocación
concurrente, agencia con resultado incierto y carga de referencia. Resultados aún no ejecutados.

### ¿Se sigue iterando?

**El diseño quedó integrado mediante PR #4 y refinamientos posteriores. QA-1 a escala conserva su conflicto
de viabilidad y no se declara demostrado.** Las ADR-0020 a 0028 están aceptadas como decisiones de diseño; cuotas,
recuperación y pruebas de implementación continúan como pendientes. Ver el cierre global y su matriz de riesgos.
Si una prueba invalida una hipótesis, se documentará el refinamiento correspondiente.

## Acuerdos de integración actualizados

* [Contrato regional](../../specs/notification-routing.md): suscripción/vinculación y región se registran antes de
  recibir avisos. Entrada global y Gateway regional son los accesos de Internet; ingesta no se expone directamente.
* [Contrato de asistencia](../../specs/agency-assistance.md): solicitud creada y autorizada por el núcleo; adaptador
  saliente del módulo de asistencia del núcleo comunica con la agencia y devuelve resultado. No agrega reservas ni implementa el chatbot avanzado.
* [Publicación del núcleo](../../specs/core-publication.md): cambio, control de aplicación y evento pendiente en una
  transacción; el núcleo conserva propiedad y el publicador debe tolerar reentregas.
* [Configuración y propiedad](../../specs/notification-routing.md): el núcleo administra región, vinculación, filtros
  y estado de autorización. Ingesta conserva cursores, trabajos, outbox y referencias protegidas de tokens. No se
  accede directamente a tablas del otro proceso ni se usan copias sin vigencia para confirmar revocación.
* La versión externa no es condición universal para incorporar reservas. Un correo con referencia y datos
  suficientes puede crear una reserva; cambios conflictivos sin orden confiable requieren conciliación controlada.
* RabbitMQ, políticas operativas y paso 7 se completan en ADR-0028 y el contrato de operación. Sus garantías requieren las pruebas declaradas, no se presentan como observadas.
