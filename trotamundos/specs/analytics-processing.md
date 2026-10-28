# Procesamiento idempotente de hechos analíticos

**Estado:** propuesta de corrección de iteración 4; ADR-0064. No es código ejecutado.

## Unidad durable y confirmaciones

Analítica consume `booking.facts.v1` y `trip.changed.v1` con ACK manual. La clave de recepción es
`(homeRegion, tipo lógico del evento, eventId)`. El registro técnico de recepción conserva esa clave con acceso
restringido, resultado y período de transformación; no conserva cuerpos de correo, tokens ni correlationId.
No se usa el código anual de bookingId para reconocer una entrega repetida.

1. Validar origen, región y esquema. Consultar el registro de recepción antes de transformar identificadores.
2. Si ya existe un resultado confirmado para esa clave, confirmar la entrega sin insertar otro hecho ni sumar
   otra vez a los agregados, incluso después de una rotación anual.
3. Si es nueva, transformar identificadores y guardar hecho inmutable y registro de recepción en una misma
   transacción del almacén analítico. Una restricción única sobre la clave resuelve carreras de consumidores.
   El producto elegido para ese almacén debe soportar esta unidad atómica; no se presuponen transacciones entre
   motores distintos. Si los agregados se calculan después, derivarlos de hechos únicos con avance recuperable.
4. Solo emitir ACK después del commit. Si falla antes del commit, reintentar. Si cae después del commit y antes
   del ACK, la reentrega sigue el paso 2.
5. Mensajes inválidos o pendientes quedan en una resolución durable de acceso restringido antes del ACK. No hay
   descarte silencioso ni creación de hechos parcialmente transformados.

El control de recepción se conserva mientras se retengan los hechos correspondientes, y su retención debe cubrir
las ventanas de republicación y reproceso. Es metadata operativa protegida, no parte de una exportación pública ni
una garantía de anonimato. Borrar un registro de recepción mientras todavía puede reproducirse su hecho obliga a
revisar la estrategia; los 30 días de deduplicación del consumidor del núcleo no se aplican automáticamente aquí.

## Período estable y claves anuales

El período de un hecho es el año UTC de `committedAt`, validado contra un rango de fechas admisible; no el año de
recepción en analítica. Tanto la transformación inicial como sus reintentos usan ese período. Identificadores de
usuario, viaje y reserva usan dominios separados en el cálculo seudónimo para no mezclar entidades.

Se mantiene la decisión de destruir la clave de un período al cerrarlo. Una entrega nueva y tardía de un período
cuya clave ya se destruyó no permite volver a crear esa clave ni usar la del año actual: queda pendiente de
resolución durable y se alerta. Una entrega ya procesada se reconoce por su clave de recepción aun sin la clave
anual. Este tratamiento puede dejar hechos tardíos fuera de los análisis y afectar el objetivo operativo de
15 minutos: ese coste queda explícito, no se prometen recuperación histórica completa ni continuidad de códigos
entre períodos. La retención del contenido de resoluciones pendientes se acota con el mismo criterio de mínima
información del resto de la integración.

## Semántica de consultas

Una fila es un cambio confirmado de reserva, no necesariamente una reserva nueva. Para contar altas se filtra
`changeType=created`; las ediciones no incrementan ese contador. Los conteos de cambios y los conteos de reservas
únicas son métricas distintas. No se usa el orden de entrega como versión de estado. Si se necesita una foto del
último estado por reserva, hay que definir una versión ordenable en el contrato antes de implementar ese análisis;
`booking.facts.v1` no la contiene y committedAt no sustituye una versión confiable.

Los códigos de reserva cambian entre períodos: no se promete un distinct global por reserva ni perfiles
históricos continuos. El valor `tripId=unassigned` representa ausencia de asignación, no un viaje compartido por
todos los usuarios; las consultas lo tratan como categoría sin asociación.

## Pruebas futuras

* Reentregar y republicar un evento: un único hecho y un único efecto en los agregados.
* Dos consumidores procesan el mismo ID: la restricción única evita duplicaciones.
* Caída antes y después del commit, y antes del ACK: recuperación con el mismo resultado.
* Reintento después del cambio de año: el hecho confirmado no cambia de código ni se inserta otra vez.
* Evento nuevo de período con clave destruida: resolución durable, sin regeneración ni cambio de período.
* Alta y dos ediciones de la misma reserva: una alta y tres eventos; no tres reservas nuevas.
