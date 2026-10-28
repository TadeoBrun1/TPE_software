# Vistas de secuencia

**Tipo:** Comportamiento
**Mantiene:** quien documenta cada escenario
**Estado:** SEQ-1 y SEQ-2 en la iteración 2; SEQ-3, SEQ-4 y SEQ-6 en la iteración 3; SEQ-5 y SEQ-7 en la iteración 4

Un diagrama por escenario clave. Debajo de cada uno, una descripción de qué representa y qué driver demuestra.

## Índice de secuencias

| ID | Escenario | Driver | Iteración | Estado |
|---|---|---|---|---|
| SEQ-1 | Llega un correo de reserva y se agrega al itinerario | RF-01, QA-1 | 2 | Propuesta documentada; evaluación pendiente |
| SEQ-2 | Un tercero informa una cancelación | RF-03, QA-6 | 2 | Propuesta documentada; evaluación pendiente |
| SEQ-3 | El viajero abre el panel y recibe un cambio | QA-2, QA-3, QA-1 | 3 | Propuesta |
| SEQ-4 | Falla la primaria de un nodo de la base | QA-4 | 3 | Propuesta |
| SEQ-5 | Se comparte un itinerario con una persona de otra región | QA-7, RF-08 | 4 | Propuesta |
| SEQ-6 | Una novedad pisa un campo editado por el usuario | RF-04, QA-6 | 3 | Propuesta |
| SEQ-7 | El viajero inicia sesión y abre la conexión de avisos | QA-7 | 4 | Propuesta |

## Refinamiento de SEQ-1 y SEQ-2

Los recorridos de ingesta están en [ingestion-sequences.md](ingestion-sequences.md): son diseño propuesto, no
pruebas. Incluyen sondeo autorizado del correo, avisos de terceros y consulta de detalles, recuperación de
publicación y revocación. Reemplazan el ejemplo anterior que dibujaba un correo como aviso iniciado por el proveedor
y confundía novedad detectada con cambio aplicado.

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
    App->>G: Abre SSE /panel/events
    G->>NT: Conexión del usuario
    NT-->>App: ready
    App->>G: GET /panel con If-None-Match 42
    G->>N: Solicitud (prioridad alta)
    N->>DB: Lee panel_por_usuario por clave
    DB-->>N: Documento versión 42
    N-->>App: 304 sin cambios
    Note over N,DB: Más tarde se aplica una novedad
    N->>DB: Transacción con reserva, panel versión 43 y outbox
    N->>B: Publica el evento de la outbox
    B->>NT: panel.changed.v1 (llega a todas las instancias)
    NT->>NT: La instancia con la conexión del usuario avisa, las demás descartan
    NT-->>App: panel-changed, versión 43
    App->>G: GET /panel con If-None-Match 42
    N-->>App: 200 con el panel versión 43
    Note over App,NT: Si la conexión SSE se corta, al reconectar llega ready y la app revalida de nuevo
```

**Qué representa:** la app muestra contenido sin esperar la red (QA-3), la lectura es por clave (QA-2) y un cambio
llega a la pantalla sin consultas periódicas (etapa de cliente de QA-1). La app abre SSE **antes** de revalidar, para
que un cambio entre ambos pasos no se pierda, y revalida de nuevo cada vez que SSE reconecta. ADR-0040, ADR-0041 y
ADR-0046.

## SEQ-4 — Falla la primaria de un nodo de la base

```mermaid
sequenceDiagram
    participant MB as Monitor de base (3 instancias)
    participant P as Primaria del nodo 3 (zona A)
    participant R as Réplica del nodo 3 (zona B)
    participant N as Núcleo
    participant App as App del usuario
    MB->>P: Ping cada 5 s
    P--xMB: Sin respuesta
    Note over MB: 6 pings sin respuesta, falla confirmada en 30 s
    MB->>MB: Acuerdo de 2 de las 3 instancias
    MB->>P: Aislar la primaria anterior
    MB->>R: Promover a primaria
    R-->>MB: Primaria activa
    MB->>N: Actualiza el ruteo de las particiones del nodo 3
    Note over MB,N: Servicio restablecido en 60 s o menos
    App->>N: GET /panel
    N->>R: Lee panel_por_usuario
    R-->>N: Documento sin pérdida de datos
    N-->>App: 200
    Note over App: Mientras tanto la app mostró su caché
```

**Qué representa:** la falla afecta solo a los usuarios de una partición y solo durante la conmutación; la réplica
sincrónica no pierde escrituras confirmadas (QA-4). La falla afecta a los usuarios de todas las particiones de ese
nodo. Después se crea una réplica nueva (en la zona C si cayó una zona entera). ADR-0042.

## SEQ-5 — Se comparte un itinerario con una persona de otra región

```mermaid
sequenceDiagram
    participant J as App de Juan (Sudamérica)
    participant A as App de Ana (Europa)
    participant X as Desconocido (Europa)
    participant GE as Puerta de entrada Europa
    participant GS as Puerta de entrada Sudamérica
    participant N as Núcleo Sudamérica (comparticion)
    participant AU as Auditoría Sudamérica
    participant NE as Núcleo Europa (usuarios)
    J->>GS: POST /trips/sa-east:7/shares con el email de Ana
    GS->>N: Crea la invitación pendiente
    N->>AU: share.invite
    N-->>J: 201, se envía el email con el secreto
    A->>GE: POST /shares/sa-east:s1/accept con el secreto
    GE->>GE: Valida el token de Ana, prefijo de otra región
    GE->>GS: Reenvía por mTLS con el token de Ana
    GS->>GS: Valida el token con las claves de Europa
    GS->>N: Acepta, permiso atado al userId de Ana
    N->>AU: share.accept permitido
    N-->>GE: 200
    GE->>NE: Guarda la referencia en la partición de Ana
    GE-->>A: 200
    A->>GE: GET /shared/trips/sa-east:7
    GE->>GS: Reenvía por mTLS
    GS->>N: Lectura compartida
    N->>N: Verifica el permiso de Ana
    N->>AU: share.read permitido (antes de responder)
    N-->>A: 200 viaje sin notas ni códigos (vía GS y GE)
    X->>GE: GET /shared/trips/sa-east:7 con el enlace reenviado
    GE->>GS: Reenvía por mTLS
    GS->>N: Lectura compartida
    N->>N: Sin permiso para ese userId
    N->>AU: share.read rechazado
    N-->>X: 404 (vía GS y GE)
    Note over N,AU: Si la auditoría no se puede escribir, la respuesta es 503 y no se devuelven datos
```

**Qué representa:** el permiso queda atado a la cuenta que aceptó, así que reenviar el enlace no da acceso; cada
intento, permitido o rechazado, queda registrado antes de responder (QA-7). Los datos de Juan se leen en su región y
no se copian a Europa; Europa solo guarda la referencia al viaje (CON-3, RF-08). ADR-0060, ADR-0061 y ADR-0062.

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
    N->>DB: Transacción con fecha nueva, notas sin cambios, aviso en el panel y outbox
    N-->>B: ACK después del commit
    B->>NT: panel.changed.v1, relevancia important
    NT-->>App: panel-changed (SSE) o push si la app está cerrada
    App->>N: GET /panel
    N-->>App: Panel con el aviso de la fecha modificada
```

**Qué representa:** la novedad cambia los datos del proveedor y conserva los del usuario, con aviso; el control de
entrada evita aplicarla dos veces (QA-6). ADR-0044 y ADR-0046.

## SEQ-7 — El viajero inicia sesión y abre la conexión de avisos

```mermaid
sequenceDiagram
    participant App as App web
    participant E as Entrada global
    participant DIR as Directorio global de regiones
    participant IDP as Proveedor de identidad (su región)
    participant G as Puerta de entrada (su región)
    participant NT as Notificador
    App->>E: Región para hash(email)
    E->>DIR: Busca hash(email)
    DIR-->>E: sa-east
    E-->>App: Proveedor de identidad de sa-east
    App->>IDP: Login (OpenID Connect)
    IDP-->>App: Token de acceso 15 min (userId, homeRegion) y token de renovación
    App->>E: GET /panel con el token
    E->>G: Elige la región por homeRegion
    G->>G: Valida firma y vencimiento con claves en caché
    G-->>App: 200 panel
    App->>G: POST /panel/events/ticket con el token
    G-->>App: Ticket de un solo uso, 30 s
    App->>G: GET /panel/events?ticket=t
    G->>G: Valida y consume el ticket
    G->>NT: Conexión SSE del usuario
    NT-->>App: ready
    Note over App,IDP: A los 15 min la app renueva el token con el proveedor, sin volver a iniciar sesión
```

**Qué representa:** la puerta de entrada valida cada token sin consultar al proveedor de identidad ni guardar
sesiones (QA-5), y el navegador abre la conexión SSE con un ticket porque no puede enviar el encabezado
`Authorization` (QA-7). El directorio global solo guarda `hash(email)` y región (CON-3). ADR-0060.
