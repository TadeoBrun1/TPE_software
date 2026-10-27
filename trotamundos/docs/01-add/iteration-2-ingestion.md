# Iteración 2 — Ingesta de reservas

**Responsable de la iteración:** Tomas Lateana (integrante A).
**Preparación documental:** 2026-10-27, con asistencia de ChatGPT/Codex.
**Estado:** pasos 2 a 6 documentados como propuesta; paso 7 pendiente de evaluación conjunta.
**ADRs:** 0020 a 0024, dentro del bloque 0020–0039.

## Base y alcance

Se actualizó la base a `main` en `5e3c0c377280046e934fad1d1e13c0d31711c5c5`, que ya contiene la primera
iteración y ADR-0001 a 0004 como propuestas. Se conserva su contenido: núcleo modular, ingesta separada,
publicación/suscripción persistente, analítica aislada y región de origen por usuario. Este refinamiento incorpora
región, claves de negocio y orden por reserva al contrato; ver [impactos](impact-log.md).

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

## Paso 5 — Componentes e interfaces

| Componente | Responsabilidad |
|---|---|
| Planificador | Elegir vinculaciones e intervalos según prioridad, cuotas y avance |
| Coordinador | Ejecutar una consulta con exclusión/versionado por vinculación |
| Gestor de vinculaciones | Verificar estado/permisos, renovar autorización y entregar acceso controlado a secretos |
| Adaptadores de acceso | Obtener correos o datos de APIs con paginación y límites |
| Receptor de avisos | Verificar origen/repetición y registrar trabajo durable antes de confirmar recepción |
| Procesador | Seleccionar, extraer, normalizar y validar; distinguir descarte de fallo |
| Registro de sincronización | Persistir cursores, resultados, casos pendientes y outbox |
| Publicador | Entregar mensajes de outbox y marcar envío tras confirmación del canal |

Son componentes lógicos que pueden compartir proceso y código. No son ocho microservicios.

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
| ADR-0020 a 0024 | Contexto, drivers, alternativas, consecuencias y confirmación futura |
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
* Idempotencia y orden de ADR-0002: claves de negocio con ámbito, versión externa y resolución si faltan datos.
* Consumo idempotente, resultados durables y control de versiones/cambios simultáneos.
* Presupuesto de cola/aplicación/visualización dentro de QA-1.
* Cambios aplicados por el núcleo generan un evento distinto para analítica, también en operaciones manuales.
* Revocar correo detiene nuevas consultas; no equivale a borrar reservas importadas ni a retirar eventos ya publicados.

### Prototipo futuro

Simuladores de correo y terceros, almacenamiento con outbox, publicador/canal y consumidor acordado con 3.
Los casos de demostración están en el contrato. No se incorpora código ni se afirma integración con proveedores
reales en este paso. Las pruebas de carga/fallo son pendientes; no hay métricas observadas todavía.
