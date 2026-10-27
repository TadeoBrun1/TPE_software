# Contrato propuesto de ingesta

**Versión:** 0.1.0, propuesta. **Productor:** ingesta. **Consumidor:** núcleo de itinerarios.
**Responsable de elaboración:** iteración 2; revisión de identidad/errores con iteración 3 pendiente.
**Esquema:** [booking-change-detected.v1.yaml](asyncapi/booking-change-detected.v1.yaml).
`v1` identifica la familia del mensaje; `0.1.0` indica borrador sin aprobación ni compatibilidad estable prometida.

## Semántica y propiedad

`booking.change.detected.v1` comunica información externa para evaluar y aplicar. No confirma que una reserva
operativa haya cambiado. Solo el núcleo asigna viajes, concilia referencias y escribe su estado oficial. Los
cambios confirmados, incluidos manuales, se publicarán por otro contrato para analítica; no se confunden con este.

Un `upsert` describe estado observado, no una orden de crear siempre. Una cancelación requiere información suficiente
para localizar la reserva; si no existe o hay ambigüedad, conservar una resolución pendiente sin inventar asociaciones.

## Identidad y datos faltantes

* `eventId` permanece estable al republicar una misma fila outbox. Reobtener una misma página requiere además
  reconocer elementos ya procesados según ID/versión externa o registro durable; generar UUID distinto en cada
  intento no evita duplicaciones.
* `sourceMessageId` identifica un correo, no una reserva. `externalReservationId` identifica la referencia de una
  reserva en una vinculación/proveedor. La clave propuesta es `(connectionId, providerId, externalReservationId)`.
* `userId` es contexto declarado; el núcleo verifica que corresponda a `connectionId` y al productor autenticado.
  No basta aceptar el usuario incluido en el cuerpo del mensaje.
* API de proveedor requiere referencia externa estable. Correo puede no permitir extraerla; en ese caso
  `requiresResolution=true` y no se debe crear una reserva automáticamente solo con el ID del correo.
* `tripId` no se exige ni lo asigna ingesta. El núcleo puede mantener el caso pendiente de asociación.
* `sourceVersion` es opaca y solo ordenable según contrato del proveedor. No comparar versiones de fuentes
  distintas. Si no hay orden confiable, consultar estado actual o resolver conflicto según política acordada.
* `occurredAt` se omite si no se conoce el instante externo; `detectedAt` nunca lo sustituye silenciosamente.
  Sin una marca externa confiable no se puede afirmar cumplimiento extremo a extremo de QA-1 para ese caso.
* Fechas-horas con offset. No inferir una zona horaria ni datos ausentes sin política explícita. Se comienza con
  vocabulario común y campos opcionales; cada adaptador tendrá reglas de suficiencia por tipo antes de implementar.

## Publicación y persistencia

Resultados de cada página (incluyendo descartes y pendientes), cursor/versión y outbox se confirman juntos en el
registro de ingesta. Si no puede hacerse una única transacción, se necesita un protocolo equivalente probado antes
de avanzar: no se afirma atomicidad entre proveedores, broker y base.

El publicador marca enviado tras confirmación durable del canal. Si cae en ese intervalo, reenvía el mismo ID.
El núcleo confirma al canal después de guardar atómicamente resultado y control de aplicación; debe tolerar duplicados.
Mensajes inválidos se apartan con causa y acceso limitado; no se reintentan sin fin ni se descartan silenciosamente.

## Errores y seguridad

| Categoría | Tratamiento |
|---|---|
| Timeout/fallo temporal | Backoff con variación y presupuesto de intentos configurable |
| Cuota agotada | Respetar espera de proveedor y ajustar planificación |
| Autorización inválida | Detener consultas; renovar solo si es válido o pedir revinculación |
| Dato inválido/formato desconocido | Registro de resolución con motivo, contenido mínimo y retención limitada |
| Canal no disponible | Mantener outbox y observar antigüedad/tamaño; no adelantar avance sin registro durable |
| Cambio de esquema incompatible | Rechazar o apartar con causa; nueva versión y coordinación de consumidores |

Receptor de avisos valida origen según el proveedor y confirma después de registrar trabajo durable. Los mensajes no
llevan tokens, contraseñas ni cuerpo completo de correo. La referencia externa de reserva también puede ser sensible:
acceso restringido al destino, sin incluirla indiscriminadamente en logs o analítica. El esquema de payload no sustituye
la autenticación/autorización del productor al canal; su transporte y permisos se especifican al elegir infraestructura.

## Desvinculación

Comprobar vigencia al iniciar cada consulta y antes de publicar trabajo aún pendiente. Coordinar confirmación de
revocación con esos inicios. No prometer cancelar solicitudes ya enviadas ni retirar eventos ya publicados. La
retención de reservas importadas y el tratamiento de mensajes en tránsito se acuerdan con 3/4, por separado.

## Pruebas futuras de aceptación

1. Un correo y una respuesta de API se normalizan a este contrato y llegan a una reserva correcta.
2. La misma novedad se reentrega sin duplicar efectos; dos fuentes de una misma reserva se concilian según regla.
3. Fallar antes y después de persistir cursor/outbox no salta novedades.
4. Fallar tras recepción del broker no pierde publicación; consumidor soporta republicación.
5. Un aviso repetido y uno inválido no originan consultas/publicaciones indebidas.
6. Revocación bloquea nuevos accesos/publicaciones pendientes con el alcance declarado.
7. Medir cuota, antigüedad de outbox/canal y generación a visualización con relojes comparables.

Son criterios de validación para paso 7/prototipo, no pruebas ejecutadas. No se fija todavía un número universal
para concurrencia, frecuencia, tamaño, retención o reintentos; se elige y prueba por proveedor/carga acordada.

## Región, identidad e idempotencia

* ADR-0003 define región de origen; ADR-0004 define la puerta de entrada. `homeRegion` proviene de configuración
  autoritativa, no del GPS ni de un campo externo sin verificar. Ver [enrutamiento](notification-routing.md).
* `eventId` se conserva en reentregas. Reconocer correos reconsultados requiere además un registro durable de
  `connectionId + sourceMessageId + referencia de reserva extraída`; un correo puede contener varias reservas.
* `reservationKey` identifica una reserva dentro del ámbito usuario/vinculación/proveedor y región. La conciliación
  entre correo y API puede necesitar localizar una reserva existente por reglas de negocio, no solo por esa clave.
* `businessChangeKey` identifica una novedad a partir de una referencia de cambio estable si existe; para correo,
  mensaje y reserva extraída. Cuando una API no ofrece ID de cambio ni versión, puede usarse una huella canónica
  de los campos normalizados relevantes, excluyendo horas de detección y datos variables del procesamiento.
  La codificación exacta y los campos de esa huella deben acordarse con el consumidor antes de implementar.
* `sourceVersion` es opcional. No se fabrica una versión externa con el orden de llegada. Un correo sin versión,
  con identidad y datos suficientes para una reserva nueva, puede incorporarse automáticamente.
* Si la reserva existe y el estado normalizado es equivalente, no se duplica el efecto. Si el cambio sin versión
  contradice el estado actual y no hay orden confiable, se conserva para conciliación. La consulta externa que
  haga falta la ejecuta ingesta mediante su adaptador, no el núcleo directamente contra el proveedor.
* Ausencia de versión por sí sola no exige `requiresResolution=true`. Sí lo exigen identidad insuficiente,
  contradicciones no resueltas o datos requeridos ausentes. Una cancelación anterior al alta queda pendiente
  hasta poder asociarla; una confirmación vieja no debe reactivar una cancelación sin evidencia suficiente.
* El canal conserva el orden de publicación por reserva donde corresponda; eso no determina el orden real en
  la fuente. El núcleo controla concurrencia y estados en su transacción. No se promete exactly-once.

## Otros contratos de integración

[Asistencia con agencias](agency-assistance.md), [publicación del núcleo](core-publication.md) y
[enrutamiento/configuración](notification-routing.md). La autenticación de usuarios de la aplicación, pendiente
para la iteración 4, es distinta de OAuth para autorizar correo, propuesto en ADR-0021.

## Transporte y cierre de diseño

RabbitMQ y límites iniciales: [ingestion-operations.md](ingestion-operations.md), ADR-0028. `booking.change.detected.v1`
es el tipo lógico; routing keys terminan en `.s0` a `.s7` según shard de usuario. El algoritmo no exige
sourceVersion y no inventa orden temporal. El payload del evento se conserva; cambia su descripción de transporte.
[Revocación coordinada](ingestion-authorization.md) completa la autoridad de configuración. El paso 7 ya está
analizado; las pruebas de implementación siguen en [el plan](../prototype/ingestion-validation.md).
