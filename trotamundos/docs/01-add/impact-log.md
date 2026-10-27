# Registro de impactos entre iteraciones

**Qué es:** cada vez que una decisión de una iteración toca un elemento compartido o puede perjudicar a otra
iteración, se anota acá. Es la defensa contra "me rompieron mi iteración sin avisar".
**Cuándo se llena:** al crear el PR (ver [CONTRIBUTING §4](../../CONTRIBUTING.md)).

| Fecha | Iteración origen | Cambio o decisión | Iteración afectada | Impacto (positivo, neutro, negativo) | Resolución | ADR / PR |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## Elementos compartidos conocidos

Completar al cerrar la iteración 1.

| Elemento | Definido en | Quién lo cambia |
|---|---|---|
| Modelo de datos de reservas | Iteración 1 | Cualquiera, con aviso |
| Bus o cola de eventos | Iteración 1 | Cualquiera, con aviso |
| Contratos de `specs/` | Iteración que los crea | Su dueño, con aviso |
| Modelo canónico de reserva | Iteración 1 | Cualquiera, con aviso |
| Esquema de mensajes (novedades y eventos de dominio) | Iteración 1 | Cualquiera, con aviso |
| Clave de partición por usuario y región de origen | Iteración 1 | Cualquiera, con aviso |
| Perfiles de consulta y de gestión del núcleo | Iteración 1 | Iteración 3, con aviso |

## Propuestas de la iteración 2 (2026-10-27)

| Cambio | Afecta | Resolución por acordar | Estado |
|---|---|---|---|
| `booking.change.detected.v1` reemplaza el ejemplo genérico como interfaz de ingesta | 1 y 3 | Revisar nombre/campos, productor y consumidor contra base de 1 | Revisión pendiente |
| `tripId` no obligatorio, referencia externa y casos incompletos explícitos | 3 | Núcleo decide conciliación/asociación y conserva pendientes | Revisión pendiente |
| Outbox de ingesta con cursores/resultados coordinados | 3 y 4 | El consumidor debe confirmar después de resultado durable e idempotente | Revisión pendiente |
| Presupuesto completo de cinco minutos | 2 y 3 | Distribuir detección, cola, aplicación y presentación; conocer cuota/carga | Sin cifras acordadas |
| Revocación impide nuevos accesos/publicación de pendientes con alcance explícito | 3 y 4 | Definir mensajes en tránsito y conservación de reservas; no prometer borrado retroactivo | Revisión pendiente |

Base actualizada a `main` en `5e3c0c377280046e934fad1d1e13c0d31711c5c5`, con la primera iteración publicada
como propuesta. Se preservan sus documentos y los drivers. La revisión cruzada se realizará en el PR de iteración 2. Ver [contrato](../../specs/ingestion-contract.md).

| Refinamiento adicional contra ADR-0002/0004 | Afecta | Resolución propuesta | Estado |
|---|---|---|---|
| Región de origen del usuario en el sobre del evento | 2 y 3 | `homeRegion` se obtiene de la vinculación/directorio autoritativo y el consumidor verifica propiedad/enrutamiento; nunca del GPS | Propuesto |
| Idempotencia proveedor + reserva + versión | 2 y 3 | Separar `eventId` de `businessChangeKey`, con ámbito usuario/vinculación/región; si falta identidad/versión, resolución pendiente | Propuesto |
| Orden por reserva | 2 y 3 | `reservationKey` estable para cambios conocidos; canal conserva orden de publicación por clave y núcleo verifica versión externa para avisos que ya llegaron desordenados | Propuesto |

La tecnología concreta de broker que ADR-0002 delega a la iteración 2 sigue pendiente, al igual que cuotas, capacidad
y políticas de retención; este PR no declara cerrada esa selección ni el paso 7.
