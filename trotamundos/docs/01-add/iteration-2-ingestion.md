# Iteración 2 — Ingesta de reservas

**Responsable de la iteración:** Tomas Lateana (integrante A).
**Preparación documental:** 2026-10-27, con asistencia de ChatGPT/Codex.
**Estado:** pasos 2 a 6 documentados como propuesta; paso 7 pendiente de evaluación conjunta.
**ADRs:** 0020 a 0027, dentro del bloque 0020–0039.

## Base y alcance

Base de integración: primera iteración revisada e incorporada a `main` en
`05a8fd737847cecc89722ccde9cd0824e5ffbd0f`. Se preservan el núcleo modular como único dueño del estado,
la publicación/suscripción y las regiones de origen. ADR-0003 es despliegue; ADR-0004 es clientes y API Gateway.
La separación lectura/escritura y el almacenamiento analítico no se presuponen: corresponden a 3 y 4.

Los RF/QA son los del repo. No se cambia el documento de requisitos ni se trasladan IDs de ejemplos anteriores.
Ingesta publica novedades; solo el núcleo escribe el estado autoritativo y decide la asociación reserva-viaje.
No se eligen nube, motor de datos, broker ni proveedor de correo concreto en esta iteración documental.

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
| ADR-0020 a 0027 | Contexto, drivers, alternativas, consecuencias y confirmación futura |
| [Impactos](impact-log.md) | Cambios que deben revisar los responsables de 1 y 3 |

Todas las ADR de esta iteración quedan `proposed`: no se inventa revisión cruzada ni aprobación del otro integrante.
Se preservan la primera iteración y sus ADR; la propuesta de ingesta debe revisarse con la tercera.

## Paso 7 — Evaluación pendiente

No se declara cerrado: es el siguiente paso de trabajo. Esta tabla es agenda de evaluación, no resultado de pruebas.

| Driver | Evidencia futura requerida | Riesgo abierto |
|---|---|---|
| QA-1 | Medir generación externa a visualización, incluida recuperación | Cuotas, acumulación y actualización del cliente |
| QA-6 | Dos formatos, repetición, desorden y conciliación | Identidad ausente o misma reserva desde correo y API |
| QA-8 | Vincular, renovar, revocar y comprobar contenido conservado | Consultas ya iniciadas, permisos amplios del proveedor y retención |
| CRN-3/4 | Fallos transitorios/permanentes y ausencia de secretos en mensajes/logs | Reintentos ilimitados o exposición de tokens |

### Dependencias que deben acordarse con la iteración 3

* Esquema mínimo, región de origen y política de reservas sin identidad/viaje: no inventar asociaciones.
* Idempotencia/orden refinados por esta iteración: la versión externa es opcional; distinguir reentrega, identidad de reserva y conflicto de estados.
* Consumo idempotente, resultados durables y control de versiones/cambios simultáneos.
* Presupuesto de cola/aplicación/visualización dentro de QA-1.
* Cambios aplicados por el núcleo generan un evento distinto para analítica, también en operaciones manuales.
* Revocar correo detiene nuevas consultas; no equivale a borrar reservas importadas ni a retirar eventos ya publicados.

### Prototipo futuro

Simuladores de correo y terceros, almacenamiento con outbox, publicador/canal y consumidor acordado con 3.
Los casos de demostración están en el contrato. No se incorpora código ni se afirma integración con proveedores
reales en este paso. Las pruebas de carga/fallo son pendientes; no hay métricas observadas todavía.

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
* El broker concreto, los límites de carga, retención, reintentos y la evaluación del paso 7 siguen pendientes.
  Esta actualización alinea el diseño; no declara implementadas ni probadas sus garantías.
