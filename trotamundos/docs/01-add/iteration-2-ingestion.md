# Iteración 2 — Ingesta de reservas

**Responsable de la iteración:** Tomas Lateana (integrante A).
**Preparación documental:** 2026-10-27, con asistencia de ChatGPT/Codex.
**Estado:** pasos 2 a 7 completados al nivel de diseño; listo para revisión cruzada en PR #4. Pruebas de prototipo pendientes.
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
| QA-6 (H,M) | Interpretación correcta de las interfaces externas |
| QA-8 (H,M) | Acceso autorizado y tratamiento limitado de correos |
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

## Paso 4 — Conceptos elegidos como propuesta

| Concepto | Justificación | Alternativas | ADR |
|---|---|---|---|
| Sondeo configurable y notificaciones donde existan | Mantener sondeo exigido sin asumir capacidades iguales en terceros | Solo sondeo; solo notificaciones | [0020](../03-adr/0020-obtener-novedades.md) |
| Autorización delegada y mínimo privilegio | No custodiar contraseña del buzón; manejar permisos y revocación | Contraseña; reenvío manual | [0021](../03-adr/0021-autorizacion-correo.md) |
| Tubería de etapas internas | Separar selección, extracción, normalización y validación | Rutina única; servicio por etapa | [0022](../03-adr/0022-tuberia-ingesta.md) |
| Puertos y adaptadores | Aislar acceso al buzón, formatos de emisores y APIs de viajes | Condicionales dispersos; formato externo como modelo interno | [0023](../03-adr/0023-adaptadores-proveedores.md) |
| Outbox y avance coordinados; reintentos por categoría | Recuperar publicación sin saltar novedades | Avanzar cursor antes de publicar; no persistir y reprocesar todo | [0024](../03-adr/0024-avance-y-publicacion-durable.md) |
| Enrutamiento por vinculación de suscripción | Encontrar región sin confiar en datos no autenticados | Difusión a regiones; confiar en región enviada por tercero | [0025](../03-adr/0025-enrutamiento-de-avisos.md) |
| Adaptador de agencia e interfaz de asistencia | Cubrir RF-06 conservando reglas en el núcleo | Integración desde clientes; asistencia mezclada con reservas | [0026](../03-adr/0026-integracion-agencia.md) |
| Outbox de cambios confirmados en el núcleo | No perder eventos entre guardar y publicar | Publicar antes o después sin registro atómico | [0027](../03-adr/0027-publicacion-del-nucleo.md) |
| RabbitMQ con topic exchanges y colas quorum | Entrega persistente y confirmaciones con políticas explícitas | Kafka; cola sobre base relacional | [0028](../03-adr/0028-rabbitmq-y-politicas.md) |

## Paso 5 — Componentes e interfaces

| Componente | Responsabilidad |
|---|---|
| Planificador | Elegir vinculaciones e intervalos según prioridad, cuotas y avance |
| Coordinador | Ejecutar una consulta con exclusión/versionado por vinculación |
| Gestor de vinculaciones | Consultar configuración autoritativa del núcleo mediante interfaz interna; coordinar acceso/revocación y renovación de secretos de ingesta |
| Adaptadores de acceso | Obtener correos o datos de APIs con paginación y límites |
| Receptor de avisos | Recibir desde el Gateway, verificar origen/repetición y registrar trabajo durable antes de confirmar recepción |
| Resolución regional | Usar la vinculación de suscripción a región; tratar avisos sin región como pendientes, sin difusión global |
| Adaptador de agencia | Enviar solicitudes autorizadas por el núcleo y normalizar respuestas de asistencia; no modifica reservas |
| Procesador | Seleccionar, extraer, normalizar y validar; distinguir descarte de fallo |
| Registro de sincronización | Persistir cursores, resultados, casos pendientes y outbox |
| Publicador | Entregar mensajes de outbox y marcar envío tras confirmación del canal |

Son componentes lógicos que pueden compartir proceso y código. No requieren un microservicio por componente.

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
[AsyncAPI propuesto](../../specs/asyncapi/booking-change-detected.v1.yaml).
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

Todas las ADR de esta iteración quedan `proposed`: no se inventa revisión cruzada ni aprobación del otro integrante.
Se preservan la primera iteración y sus ADR; la propuesta de ingesta debe revisarse con la tercera.

## Paso 7 — Análisis del diseño y cierre de la iteración

Se realiza un recorrido analítico de escenarios sobre contratos/vistas, no una prueba de software. Se seleccionó
RabbitMQ en ADR-0028 y se fijaron hipótesis operativas en [ingestion-operations.md](../../specs/ingestion-operations.md).
El análisis distingue resultados del razonamiento y evidencia que deberá producir el prototipo.

### Recorridos y resultados

| Caso analizado | Recorrido y resultado esperado por diseño | Límite o riesgo |
|---|---|---|
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
| QA-1 | Presupuesto de 300 s, alertas y carga hipotética definidos | Parcial/condicionado a cuotas y capacidad. No demostrado para millones de cuentas ni todos los proveedores |
| QA-6 | Identidad separada, normalización, dedupe durable, conciliación y outboxes definidos | Parcial hasta pruebas de contrato/reentrega/desorden; no prometer exactly-once |
| QA-8 | OAuth delegado, mínimo privilegio, propiedad y protocolo de revocación definidos | Parcial hasta pruebas de carrera, integración real, seguridad y conservación de datos |
| CRN-3 | Reintentos clasificados, pendientes y recuperación definidos | Resuelto al nivel de diseño; falta ejercitar fallos |
| CRN-4 | Secretos fuera de payload/log, roles del broker y vigencia de configuración definidos | Resuelto al nivel de diseño; infraestructura/secret store se verifica en implementación |

### Riesgos aceptados como pendientes de validación

1. Cuotas del proveedor y número de vinculaciones: pueden impedir detectar cambios en 120 s. Requisito QA-1 no
   se relaja; se valida antes de habilitar cada integración y se informa bloqueo si no es viable.
2. Capacidad: 50/s normal, 250/s pico y 20 ms de servicio son hipótesis, no resultados. Pruebas de carga deben
   demostrar cola ≤40 s, publicación ≤10 s y recorrido ≤300 s bajo el escenario acordado con 3.
3. Política regional y secreto/token: CON-3 sigue como supuesto; los plazos operativos no prueban cumplimiento legal.
4. Broker en tres zonas y base altamente disponible: dependen del despliegue que refina 3; no hay recuperación
   entre regiones ni validación mensual en esta iteración.
5. Casos ambiguos entre correo y API: conservar y resolver evita corrupción, pero puede requerir intervención y
   no produce itinerario automáticamente hasta contar con evidencia suficiente.

### Dependencias de implementación, no decisiones omitidas

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

**Se finaliza el diseño de la iteración 2 y se entrega para revisión cruzada en PR #4.** No queda pendiente elegir
broker ni redactar el paso 7. Los ADR-0020 a 0028 mantienen `proposed` hasta aceptación real por ambos; el cierre
administrativo se registra al aprobar. Si pruebas o cuotas invalidan las hipótesis, se crea un refinamiento/ADR,
no se afirma que el requisito estaba cumplido. Se continúa con implementación y las iteraciones 3/4.

## Acuerdos de integración actualizados

* [Contrato regional](../../specs/notification-routing.md): suscripción/vinculación y región se registran antes de
  recibir avisos. Entrada global y Gateway regional son los accesos de Internet; ingesta no se expone directamente.
* [Contrato de asistencia](../../specs/agency-assistance.md): solicitud creada y autorizada por el núcleo; adaptador
  de ingesta comunica con la agencia y devuelve resultado. No agrega reservas ni implementa el chatbot avanzado.
* [Publicación del núcleo](../../specs/core-publication.md): cambio, control de aplicación y evento pendiente en una
  transacción; el núcleo conserva propiedad y el publicador debe tolerar reentregas.
* [Configuración y propiedad](../../specs/notification-routing.md): el núcleo administra región, vinculación, filtros
  y estado de autorización. Ingesta conserva cursores, trabajos, outbox y referencias protegidas de tokens. No se
  accede directamente a tablas del otro proceso ni se usan copias sin vigencia para confirmar revocación.
* La versión externa no es condición universal para incorporar reservas. Un correo con referencia y datos
  suficientes puede crear una reserva; cambios conflictivos sin orden confiable requieren conciliación controlada.
* RabbitMQ, políticas operativas y paso 7 se completan en ADR-0028 y el contrato de operación. Sus garantías requieren las pruebas declaradas, no se presentan como observadas.
