# Políticas operativas de ingesta y mensajería

**Estado:** decisión de diseño de iteración 2; valores iniciales son hipótesis para validar en prototipo, no cifras del
cliente ni mediciones de producción. **ADR:** 0028. No se modifica el texto de los requisitos.

## 1. Broker y topología

RabbitMQ con AMQP 0-9-1, TLS, exchanges tipo `topic` durables, colas quorum y confirmaciones de publicación.
Productores usan mensajes persistentes, publisher confirms y `mandatory=true`; un retorno por falta de ruta es
fallo aunque llegue confirm. No marcar outbox enviada sin confirmación y sin retorno de mensaje no enrutado.
Consumidores usan ACK manual posterior a resultado durable. La reentrega es normal; no hay exactly-once.

Cada región tiene su vhost y usuarios técnicos con permisos por exchange/cola. Ingesta publica novedades; el núcleo publica eventos confirmados y solicitudes de asistencia. El trabajador de
asistencia del núcleo publica sus resultados y tiene credenciales separadas de la atención HTTP. Consumidores reciben
solo las colas necesarias. Broker/management no son endpoints públicos; acceso externo por Gateway no equivale
a exponer AMQP en Internet. TLS y credenciales por servicio se mantienen fuera de código y payloads.

| Exchange durable | Routing keys | Colas / consumidor |
|---|---|---|
| `travel.ingestion` | `booking.change.detected.v1.s0` a `.s7` | `core.bookings.s0` a `.s7`, una por shard de usuario |
| `travel.domain` | `booking.changed.v1` | Cola independiente por consumidor autorizado, inicialmente analítica |
| `travel.assistance` | `assistance.requested.v1`, `assistance.result.v1` | Solicitudes para trabajador de asistencia del núcleo; resultados para seguimiento |
| `travel.errors` | `ingestion.error.v1` | Operación/revisión con acceso restringido, referencia mínima al caso durable |

El nombre lógico del evento y su routing key no son lo mismo. Shard del usuario: interpretar los primeros 16
hexadecimales de SHA-256(UTF-8 de JSON compacto `[homeRegion,userId]`) como entero y módulo 8. Todos los cambios
externos de un mismo usuario siguen esa asignación. No cambiar 8 ni migrar región sin drenar/coordinar colas y
configuración con 3. Un ID/versión externa no determina la partición ni se expone en la routing key.

Un consumidor activo por shard, con Single Active Consumer y respaldo en otra zona; ejecución secuencial de
aplicaciones por consumidor. Prefetch inicial 20 (controla mensajes en vuelo, no implica 20 escrituras paralelas).
El orden de la cola es orden de publicación: versiones atrasadas, múltiples fuentes y cambios manuales siguen
requiriendo conciliación y control transaccional de versión/bloqueo por reserva en el núcleo.

## 2. Disponibilidad objetivo y demo

Producción objetivo: quorum de tres miembros, un nodo en cada una de tres zonas por región. Perder una zona deja
dos miembros; no repartir tres miembros 2+1 entre solo dos zonas y afirmar tolerancia a cualquiera de esas zonas.
Esto refina el mínimo de dos zonas de ADR-0003 sin agregar replicación entre regiones. Si solo hay dos zonas,
registrar la limitación antes de aceptar QA-4; un tercero en la misma zona no crea otro dominio de fallo.

Prototipo funcional: un nodo local y colas quorum de un miembro, solo para durabilidad/reinicio y contratos.
Ensayo adicional de tres procesos permite explorar pérdida de nodo, pero una máquina no demuestra fallo de zona.
No se selecciona una etiqueta Docker `latest`: al implementar se fija release compatible y digest, sin cambiar
la decisión de broker ni dar por probada una versión que aún no se ejecutó.

## 3. Carga de referencia y capacidad

Hipótesis inicial por región activa: 50 novedades/s sostenidas y pico 250/s durante 15 minutos, manteniendo
consultas en paralelo con la carga que definirá 3. Es un punto de partida de prueba; no se deduce de 2 millones
semanales. Datos del cliente no determinan concurrencia ni frecuencia de cambios. Se conserva el pico supuesto 5x.

Payload normalizado medio de prueba: 4 KiB; límite de aplicación 16 KiB. Si se excede, conservar caso de
resolución con contenido mínimo; nunca truncar o descartar una reserva en silencio. Outbox lee lotes de 100,
con espera de confirmaciones asíncronas. Ocho consumidores activos con media hipotética de 20 ms/evento dan
400 eventos/s de capacidad modelada: 8/0,020. No es benchmark; distribución desigual por usuario, base y broker
pueden invalidarlo. Se exige medir throughput, p99 y backlog por shard antes de dimensionar producción.

El pico 250/s requiere menos del 70 % de esa capacidad modelada. Si un shard concentra carga y no cumple,
repartir/dimensionar exige una nueva evaluación, no aumentar consumidores a ciegas y perder serialización.
La latencia web de 800 ms se comprueba con el responsable de 3, no queda validada por esta cuenta aritmética.

## 4. Presupuesto de frescura

| Etapa | Objetivo inicial máximo |
|---|---:|
| Desde generación externa hasta detección (incluye espera de sondeo) | 120 s |
| Extracción, normalización y persistencia de resultado/outbox | 30 s |
| Publicación y confirmación de recepción | 10 s |
| Espera hasta iniciar aplicación en el núcleo | 40 s |
| Aplicación y confirmación durable | 30 s |
| Actualización visible en cliente | 30 s |
| Margen compartido para variación/reintentos | 40 s |
| **Total** | **300 s** |

Los avisos de correo son el mecanismo principal donde el proveedor los ofrece. Se persiste el aviso y se agrupa
trabajo por vinculación antes de consultar cambios desde el cursor. Un aviso no contiene necesariamente el correo.
Se renuevan suscripciones antes del vencimiento y se reconcilian huecos aunque no lleguen avisos.

El escenario vigente expresa 99 % de actualizaciones visibles en cinco minutos; ese percentil está identificado
como suposición en los requisitos. Para evaluarlo hay que medir la fracción de actualizaciones que supera 300 s,
incluyendo avisos perdidos, cuentas de baja frecuencia y otras etapas. Si esa fracción supera el 1 %, falla la
medida actual. Un único aviso perdido no prueba ese incumplimiento estadístico, pero demuestra que el respaldo
lento no garantiza el plazo por actualización. No se usa el percentil para excluir clases de cuentas ni se lo
presenta como una relajación confirmada del enunciado. El respaldo de 90 s para todas las cuentas es una condición
suficiente a evaluar, no la única solución posible; una alternativa basada en avisos necesita evidencia de su cola
de latencia y pérdidas recuperadas.

### Coste de detección, independiente de la carga de novedades

Para cada proveedor, `R_sondeo = suma(N_clase / intervalo_clase)` en consultas/s mínimas. La carga API real suma
consultas por aviso, páginas adicionales, lectura de mensajes, renovaciones y reintentos. Una cuenta de usuario
puede tener cero o varias vinculaciones: no se equiparan 15 millones de usuarios con buzones sin declararlo.
Los 2 millones semanales tampoco equivalen a 2 millones de buzones conectados simultáneamente.

| Hipótesis global, un buzón por cuenta | Consultas mínimas por segundo |
|---|---:|
| 15.000.000 de buzones cada 60 s | 250.000 |
| 2.000.000 de buzones cada 60 s | 33.333,3 |
| 15.000.000 de buzones cada 90 s | 166.666,7 |

Un perfil adaptable ilustrativo, no derivado del enunciado, divide 15 millones de vinculaciones así:

| Clase de reconciliación | Buzones hipotéticos | Intervalo | Consultas/s |
|---|---:|---:|---:|
| Viaje próximo o en curso | 100.000 | 90 s | 1.111,1 |
| Actividad reciente sin viaje próximo | 500.000 | 900 s | 555,6 |
| Inactiva, aún vinculada y autorizada | 14.400.000 | 21.600 s | 666,7 |
| **Total** | **15.000.000** | | **2.333,3** |

El perfil reduce sondeos vacíos, pero NO garantiza QA-1 para todas las cuentas si se pierde un aviso: las clases
de 15 minutos y 6 horas pueden incumplir cinco minutos. La prioridad no cambia el requisito. Para garantizar los cinco minutos incluso ante avisos perdidos debe demostrarse una recuperación acotada para todas las vinculaciones; aun consultar cada 90 s
requiere 166.666,7 consultas/s mínimas globales más el trabajo adicional y deja solo 30 s del presupuesto de
detección para espera, respuestas y paginación. Si las cuotas no lo permiten, el resultado del paso 7 es un
conflicto de viabilidad pendiente, que requiere otra solución o un cambio de requisito acordado por ambos.

Como referencia del coste de suscripciones, renovar diariamente 15 millones de vigilancias supone 173,6
renovaciones/s globales si todas usan ese plazo. Gmail recomienda renovación diaria y exige hacerlo antes de
su vencimiento; Graph usa plazos propios. No se aplica el plazo de Gmail a todos los proveedores. Para IMAP IDLE
se dimensionan además conexiones simultáneas, memoria, keepalives y reconexiones; no se elige una conexión por
cuenta como solución universal.

Antes de admitir producción se necesita una ficha por proveedor con número de buzones, cuotas por usuario y
proyecto, amplificación por páginas, tasa de avisos, vencimientos y recuperación de cursores inválidos. Se limita
concurrencia con presupuesto de solicitudes por proveedor y se distribuyen vencimientos para evitar ráfagas.
Gmail puede entregar por Google Cloud Pub/Sub: ese transporte externo alimenta el receptor y no reemplaza al
RabbitMQ interno. Si el histórico incremental deja de estar disponible, se ejecuta una resincronización acotada
y se registra su impacto temporal. Un sondeo incremental vacío también consume solicitudes.

Las 50–250 novedades/s anteriores solo ejercitan el broker y sus consumidores por región. No validan la detección
global. Deben medirse por separado ambos caminos y luego el recorrido integrado. Los avisos perdidos, las cuotas
y las cuentas inactivas son parte de la evaluación de QA-1 y QA-5.

Sondeo obtiene solo cambios desde cursor donde exista; máximo inicial 100 mensajes por página. Si la página
requiere más trabajo que el presupuesto, conservarla como trabajo durable y repartirlo sin avanzar cursor antes
de representar todos sus resultados. Limitar concurrencia por vinculación y proveedor; no iniciar dos avances
con la misma versión esperada. No inventar occurredAt para medir frescura: si se desconoce, reportar por separado
el tiempo desde detección y la imposibilidad de probar generación a visualización en ese caso.

## 5. Reintentos y fallos permanentes

HTTP inicial: timeout 3 s por intento de consulta de metadata/API; operaciones que requieran otro tiempo tienen
contrato propio y se vuelven a evaluar contra los 300 s. Hasta cuatro intentos en la ronda (inicial + tres),
esperas con variación acotada de 0–1, 0–5 y 0–15 s. Peor presupuesto de esa ronda: 12 + 21 = 33 s, dentro del margen
si no se consumió en otras etapas. No sumar ese margen una vez por etapa. Agotarlo conserva el trabajo para ronda
posterior y registra incumplimiento potencial; no convierte los 5 minutos en 5 minutos desde el último intento.

`Retry-After` y cuota del proveedor prevalecen; si exceden presupuesto se mantiene pendiente y alerta. Un error
401/403 no se reintenta como timeout: renovar solo cuando corresponda, de modo coordinado, y después pedir
revinculación si el permiso no es válido. Formatos inválidos, referencias ambiguas y datos insuficientes se
clasifican para resolución, no reintento automático eterno.

Publicación sin confirm o sin ruta conserva outbox. Reintentos del mismo evento usan el mismo eventId. El broker
no duplica por sí solo el efecto de negocio: el consumidor guarda identidad/resultado de modo atómico. Para un
mensaje problemático: hasta cinco intentos de aplicación contabilizados duraderamente, luego estado `parked` con
motivo en inbox/resoluciones y aviso mínimo por outbox de errores. ACK original solo después de ese registro.
Si falla el almacenamiento, no confirmar: pausar consumo y recuperar servicio, sin contar indisponibilidad de la
base como error permanente de datos. Evitar bucles `nack(requeue=true)` inmediatos.

No depender del límite de entregas predeterminado del broker para descartar mensajes: configurarlo sin descarte
automático por límite (delivery-limit=-1 donde corresponda) y controlar intentos en aplicación. Las colas de
negocio no usan TTL para desaparecer trabajo no resuelto. Los errores se aparcan duraderamente; no se requiere
un DLX con traslado potencialmente inseguro para conservar el caso. Si se cambia a DLX, justificar su fiabilidad.

## 6. Límites, retención y contrapresión

Hipótesis operativa: capacidad útil de backlog de 16 GiB por cola de novedades y 128 GiB agregados, antes de
replicación, con reserva física adicional para tres copias, WAL, índices y otros flujos. No es aprovisionamiento
final: 50/s * 86400 * 4 KiB son unos 16,5 GiB diarios de payload, sin overhead ni réplicas. Debe medirse skew por
shard y el crecimiento de outbox/errores, no suponer esa distribución uniforme.

Configurar overflow `reject-publish` y verificar comportamiento en la release elegida, nunca `drop-head` para
reservas. Ante rechazo, outbox no se marca enviada. Alertar al 70 % y limitar admisión al 85 % de capacidad
reservada; si no hay espacio seguro para resultados/outbox no adelantar cursor ni confirmar aceptación de trabajo.
La fuente externa puede tener retención limitada: alertar antes de perder su ventana y resolver recuperación.
Persistencia no significa espacio infinito ni garantía ante pérdida definitiva de la mayoría de nodos.

No eliminar outbox no publicada ni resoluciones pendientes automáticamente. Revisar su antigüedad diariamente;
objetivo de operación: recuperar/revisar antes de 24 h, pero excederlo no borra el trabajo. Outbox enviada: limpiar
payload tras 24 h conservando metadata mínima de resultado. Dedupe de eventos: 30 días de IDs/resultado mínimo;
una reproducción más antigua necesita conciliación contra estado y registro de negocio, no aplicación ciega.
Pendientes con contenido personal: revisar/minimizar dentro de 24 h; los plazos son decisiones de operación, no
una política legal aprobada. Los datos de reservas y conservación analítica pertenecen a 3/4 y sus políticas.

## 7. Señales y responsabilidades

Medir por región/proveedor/shard: demora de detección, edad de outbox, espera de cola, tiempo de aplicación,
confirmaciones fallidas, reentregas, pendientes, cuota y antigüedad extremo a extremo. Alertas iniciales:
outbox >10 s; cola >30 s advertencia y >40 s crítica; recorrido >240 s advertencia y >300 s incumplimiento.
Correlación por IDs técnicos sin cuerpos de correo/tokens en logs. Un ACK del broker no cierra el recorrido.

Ingesta controla detección, extracción y publicación. Núcleo controla asistencia saliente, aplicación y su outbox (3 implementa
sin cambiar contrato). Cliente debe refrescar dentro de 30 s de cambio disponible, por polling o notificación que
3 elegirá; sin ese acuerdo no se afirma QA-1 cumplido. Alertas son respuesta operativa, no cumplimiento automático.

## Fuentes técnicas y límites

RabbitMQ: https://www.rabbitmq.com/docs/quorum-queues ; https://www.rabbitmq.com/docs/confirms ;
https://www.rabbitmq.com/docs/exchanges . Kafka comparado: https://kafka.apache.org/42/getting-started/introduction/ .
Se usan sus capacidades documentadas, no cifras de rendimiento prometidas. Ningún parámetro anterior está medido.

Fuentes de detección: [Gmail push](https://developers.google.com/workspace/gmail/api/guides/push),
[notificaciones de Graph](https://learn.microsoft.com/en-us/graph/outlook-change-notifications-overview) y
[ciclo de vida](https://learn.microsoft.com/en-us/graph/change-notifications-lifecycle-events).
