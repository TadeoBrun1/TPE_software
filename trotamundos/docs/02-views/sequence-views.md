# Vistas de secuencia

**Tipo:** Comportamiento
**Mantiene:** quien documenta cada escenario
**Estado:** SEQ-1 y SEQ-2 en la iteración 2; SEQ-3, SEQ-4 y SEQ-6 en la iteración 3; SEQ-5 pendiente

Un diagrama por escenario clave. Debajo de cada uno, una descripción de qué representa y qué driver demuestra.

## Índice de secuencias

| ID | Escenario | Driver | Iteración | Estado |
|---|---|---|---|---|
| SEQ-1 | Llega un correo de reserva y se agrega al itinerario | RF-01, QA-1 | 2 | Propuesta documentada; evaluación pendiente |
| SEQ-2 | Un tercero informa una cancelación | RF-03, QA-6 | 2 | Propuesta documentada; evaluación pendiente |
| SEQ-3 | El viajero abre el panel y recibe un cambio | QA-2, QA-3, QA-1 | 3 | Propuesta |
| SEQ-4 | Falla la primaria de una partición | QA-4 | 3 | Propuesta |
| SEQ-5 | Se comparte un itinerario con otra persona | QA-7 | 4 | Pendiente |
| SEQ-6 | Una novedad pisa un campo editado por el usuario | RF-04, QA-6 | 3 | Propuesta |

## Refinamiento de SEQ-1 y SEQ-2

Los recorridos de ingesta están en [ingestion-sequences.md](ingestion-sequences.md): son diseño propuesto, no
pruebas. Incluyen sondeo autorizado del correo, avisos de terceros y consulta de detalles, recuperación de
publicación y revocación. Reemplazan el ejemplo anterior que dibujaba un correo como aviso iniciado por el proveedor
y confundía novedad detectada con cambio aplicado. SEQ-5 queda para la iteración 4.

## SEQ-3 — El viajero abre el panel y recibe un cambio

```mermaid
sequenceDiagram
    participant App as App móvil
    participant G as Puerta de entrada
    participant N as Núcleo
    participant DB as Partición del usuario
    participant B as Broker
    participant NT as Notificador
    App->>App: Muestra el panel guardado (versión 42)
    App->>G: GET /panel con If-None-Match 42
    G->>N: Solicitud (prioridad alta)
    N->>DB: Lee panel_por_usuario por clave
    DB-->>N: Documento versión 42
    N-->>App: 304 sin cambios
    App->>G: Abre SSE /panel/events
    G->>NT: Conexión del usuario
    Note over N,DB: Más tarde se aplica una novedad
    N->>DB: Transacción con reserva, panel versión 43 y outbox
    N->>B: Publica el evento de la outbox
    B->>NT: booking.changed.v1 del usuario
    NT-->>App: panel-changed, versión 43
    App->>G: GET /panel con If-None-Match 42
    N-->>App: 200 con el panel versión 43
```

**Qué representa:** la app muestra contenido sin esperar la red (QA-3), la lectura es por clave (QA-2) y un cambio
llega a la pantalla sin consultas periódicas (etapa de cliente de QA-1). ADR-0040 y ADR-0041.

## SEQ-4 — Falla la primaria de una partición

```mermaid
sequenceDiagram
    participant MB as Monitor de base
    participant P as Primaria de la partición 3 (zona A)
    participant R as Réplica de la partición 3 (zona B)
    participant N as Núcleo
    participant App as App del usuario
    MB->>P: Heartbeat
    P--xMB: Sin respuesta
    Note over MB: Falla confirmada en 30 s o menos
    MB->>R: Promover a primaria
    R-->>MB: Primaria activa
    MB->>N: Actualiza el ruteo de la partición 3
    Note over MB,N: Servicio restablecido en 60 s o menos
    App->>N: GET /panel
    N->>R: Lee panel_por_usuario
    R-->>N: Documento sin pérdida de datos
    N-->>App: 200
    Note over App: Mientras tanto la app mostró su caché
```

**Qué representa:** la falla afecta solo a los usuarios de una partición y solo durante la conmutación; la réplica
sincrónica no pierde escrituras confirmadas (QA-4). Después se crea una réplica nueva. ADR-0042.

## SEQ-6 — Una novedad pisa un campo editado por el usuario

```mermaid
sequenceDiagram
    participant B as Broker
    participant N as Núcleo, módulo reservas
    participant DB as Partición del usuario
    participant NT as Notificador
    participant App as App del usuario
    B->>N: booking.change.detected.v1 (hotel cambia la fecha)
    N->>DB: ¿Ya se aplicó este evento?
    DB-->>N: No
    N->>N: Fecha es campo del proveedor, el usuario la había editado
    N->>DB: Transacción con fecha nueva, notas sin cambios, panel, aviso y outbox
    N-->>B: ACK después del commit
    B->>NT: booking.changed.v1
    NT-->>App: panel-changed y aviso de la fecha modificada
```

**Qué representa:** la novedad cambia los datos del proveedor y conserva los del usuario, con aviso; el control de
entrada evita aplicarla dos veces (QA-6). ADR-0044.
