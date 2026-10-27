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

## Integración con ADR-0002 y ADR-0004 publicados en la primera iteración

* `homeRegion` identifica la región de origen del usuario obtenida de la configuración autoritativa de la
  vinculación/directorio, no la ubicación física del viajero. Se enruta al núcleo propietario de esa partición;
  el consumidor verifica región y usuario. Migración de región y enrutamiento en recuperación se refinan con 3/4.
* `eventId` evita repetir un efecto por reentrega del mismo evento, pero no reemplaza la clave de negocio de
  ADR-0002. `businessChangeKey` representa la tupla lógica de ámbito usuario/región/vinculación, proveedor, código
  de reserva y versión externa. La codificación canónica se acuerda con el consumidor antes de implementar.
* `reservationKey` identifica la misma reserva dentro de ese ámbito sin incluir la versión. El canal y sus
  consumidores deben conservar procesamiento ordenado por esa clave; múltiples trabajadores no aplican a la
  vez versiones de una misma reserva. El orden de publicación no arregla avisos que llegan ya desordenados:
  el núcleo valida la versión y conserva cancelaciones pendientes si el alta aún no existe.
* Si faltan referencia/versión confiables no se fabrica la clave ni se compara una hora de recepción como versión.
  `requiresResolution=true`; el núcleo mantiene el caso durable o consulta estado autoritativo mediante política
  coordinada con ingesta. Los cambios publicables automáticamente incluyen ambas claves y versión. Esto hace
  explícita una limitación de las fuentes de correo que ADR-0002 todavía no desarrollaba.
* El broker/tecnología concreta, partición física y parámetros de retención quedan pendientes de selección y
  prueba; el contrato expresa sus requisitos y no demuestra orden real ni exactly-once.
