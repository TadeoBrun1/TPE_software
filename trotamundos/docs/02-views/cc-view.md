# Vista de componentes y conectores

**Tipo:** C&C (en ejecución)
**Actualizada en la iteración:** 3
**Mantiene:** Ambos
**Estado:** Refinada en las iteraciones 2 y 3. La iteración 4 la completa.

## 1. Propósito

Mostrar los elementos que existen en ejecución y cómo se comunican. Sirve para razonar sobre performance,
disponibilidad, seguridad y escalabilidad. Muestra **una región**; todas las regiones tienen la misma estructura
(ver [vista de despliegue](deployment-view.md)). La entrada global que elige la región no aparece acá: está en la
vista de despliegue.

## 2. Presentación primaria

```mermaid
flowchart LR
    subgraph Clientes
        W["Aplicación web<br/>(una sola página)"]
        M["App móvil nativa<br/>(GPS)"]
    end

    subgraph Trotamundos["Trotamundos (una región)"]
        G["Puerta de entrada<br/>(API Gateway)"]
        N["Núcleo<br/>(monolito modular, sin estado)"]
        NT["Notificador<br/>(SSE y push)"]
        DB[("Base operativa<br/>particiones por usuario<br/>con panel_por_usuario")]
        MB["Monitor de base<br/>(ping/echo y conmutación,<br/>3 instancias)"]
        B{{"RabbitMQ regional<br/>novedades · dominio · panel · asistencia"}}
        I["Ingesta<br/>(adaptador por proveedor)"]
        A["Analítica"]
    end

    EC["Proveedores de correo"]
    ET["Sistemas de terceros<br/>(aerolíneas, hoteles, rentadoras)"]

    AG["Agencia preferida"]
    EC -- "avisos vía entrada global" --> G
    ET -- "avisos vía entrada global" --> G
    N -- "asistencia saliente asíncrona" --> AG
    G -- "deriva notificaciones" --> I
    W -- "HTTPS / REST" --> G
    M -- "HTTPS / REST" --> G
    G -- "REST" --> N
    N -- "lectura y escritura" --> DB
    I -- "sondeo / API" --> EC
    I -- "API estándar" --> ET
    I -- "publica novedades" --> B
    B -- "entrega novedades" --> N
    N -- "publica eventos de dominio y panel.changed" --> B
    B -- "entrega eventos de dominio" --> A
    B -- "panel.changed (cola por instancia y cola de push)" --> NT
    W -. "SSE /panel/events" .-> G
    M -. "SSE /panel/events" .-> G
    G -. "SSE" .-> NT
    NT -- "push" --> PS["Push del sistema operativo<br/>(APNs / FCM)"]
    MB -- "ping/echo y promoción de réplicas" --> DB
```

Leyenda: rectángulo = proceso; cilindro = almacenamiento; hexágono = intermediario de mensajes; flecha = conector
en la dirección de la solicitud o del mensaje.

## 3. Catálogo de elementos

| Elemento | Responsabilidad | Iteración que lo refina |
|---|---|---|
| Aplicación web | Panel de viajes y carga manual de reservas | 3 |
| App móvil | Panel de viajes y GPS (CON-4) | 3 |
| Puerta de entrada | Único punto de entrada a la región; valida identidad, balancea y limita tráfico; deriva las notificaciones de terceros a la ingesta | 2, 3, 4 |
| Núcleo | Único dueño del estado de viajes y reservas; aplica novedades; publica eventos de dominio; archiva viajes completados | 3 |
| Base operativa | Datos del núcleo de los usuarios de la región en particiones por usuario; incluye `panel_por_usuario` (ADR-0040, ADR-0042) | 3 |
| Intermediario de mensajes | Conserva mensajes de novedades, dominio y asistencia | 2 |
| Ingesta | Sondea correos, recibe notificaciones y consulta a terceros, traduce al modelo canónico y publica novedades | 2 |
| Analítica | Consume eventos de dominio sin compartir recursos con la consulta | 4 |
| Notificador | Consume `panel.changed.v1`; avisa a las apps abiertas por SSE y a las cerradas por push; no lleva datos de reservas (ADR-0046) | 3 |
| Monitor de base | Tres instancias (zonas A, B y C); detecta primarias caídas en 30 s y promueve la réplica con acuerdo de dos de tres (ADR-0042) | 3 |

## 4. Conectores

| De | A | Estilo | Contrato en `specs/` |
|---|---|---|---|
| Clientes | Puerta de entrada | Síncrono, HTTPS/REST | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| Puerta de entrada | Núcleo | Síncrono, REST | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| Clientes | Puerta de entrada → Notificador | SSE (`/panel/events`), solo versión del panel | [itinerary-api.v1.yaml](../../specs/openapi/itinerary-api.v1.yaml) |
| Intermediario (`panel.changed.v1`) | Notificador | Asíncrono: una cola exclusiva por instancia (todos los avisos) y una cola compartida `notifier.push` | [panel-changed.v1.yaml](../../specs/asyncapi/panel-changed.v1.yaml) |
| Notificador | Servicios de push del sistema operativo | Asíncrono, externo | Externo |
| Ingesta | Intermediario (tema novedades) | Asíncrono, publicación | `asyncapi/booking-change-detected.v1.yaml` |
| Intermediario (tema novedades) | Núcleo | Asíncrono, suscripción | `asyncapi/booking-change-detected.v1.yaml` |
| Núcleo | Intermediario (exchange `travel.domain`) | Asíncrono, publicación desde la outbox | [booking-confirmed.v1.yaml](../../specs/asyncapi/booking-confirmed.v1.yaml), [trip-changed.v1.yaml](../../specs/asyncapi/trip-changed.v1.yaml), [panel-changed.v1.yaml](../../specs/asyncapi/panel-changed.v1.yaml) |
| Intermediario (eventos de dominio) | Analítica | Asíncrono, suscripción | [booking-confirmed.v1.yaml](../../specs/asyncapi/booking-confirmed.v1.yaml), [trip-changed.v1.yaml](../../specs/asyncapi/trip-changed.v1.yaml) |
| Ingesta | Proveedores de correo y terceros | Síncrono, API del proveedor (sondeo y consulta) | Externo (CON-1, CON-2) |
| Terceros | Puerta de entrada → Ingesta | Síncrono, notificaciones por API estándar | Externo; se detalla en la iteración 2 |

## 5. Elementos compartidos entre iteraciones

Núcleo, intermediario de mensajes y sus exchanges (novedades, dominio, asistencia), modelo canónico de reserva, base operativa y su clave de
partición. Cualquier cambio sobre ellos se anota en [impact-log.md](../01-add/impact-log.md).

## 6. Rationale

| Decisión | ADR |
|---|---|
| Clientes ricos y puerta de entrada única | [0004](../03-adr/0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) |
| Núcleo modular; ingesta y analítica como procesos separados | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| Comunicación asincrónica por publicación y suscripción | [0002](../03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) |
| Modelo de lectura del panel | [0040](../03-adr/0040-modelo-de-lectura-del-panel.md) |
| Caché local del panel | [0041](../03-adr/0041-cache-local-del-panel.md) |
| Notificador, evento `panel.changed.v1` y cola por instancia | [0046](../03-adr/0046-notificador-de-cambios-del-panel.md) |
| Particiones por usuario y monitor de base | [0042](../03-adr/0042-particion-de-la-base-por-usuario.md) |
| Límites y prioridades en la puerta de entrada | [0047](../03-adr/0047-priorizacion-y-degradacion-ante-sobrecarga.md) |

## 7. Drivers que sustenta

| Driver | Cómo lo sustenta |
|---|---|
| QA-1 | La ingesta escala por separado y el broker amortigua las ráfagas de los proveedores; el notificador lleva el cambio a la pantalla |
| QA-2 | El panel es una lectura por clave en la partición del usuario |
| QA-3 | La app muestra su caché local sin esperar la red |
| QA-4 | Si la ingesta o la analítica fallan, la consulta (clientes → puerta → núcleo → base) sigue funcionando |
| QA-5 | Núcleo sin estado detrás de la puerta de entrada; cada proceso escala por su cuenta |
| QA-9 | Productores y consumidores no se conocen; los adaptadores aíslan a cada proveedor |

## 8. Vistas relacionadas

[Módulos](module-view.md) · [Despliegue](deployment-view.md) · [Secuencias](sequence-views.md)

## Detalle de ingesta alineado

Ver [ingestion-view.md](ingestion-view.md). Se conserva la vista general de la primera iteración: avisos por entrada global y Gateway, núcleo único dueño de reservas y dos flujos de mensajes.

## Asistencia saliente y correo por avisos

El núcleo contiene el módulo saliente de asistencia (ADR-0026), con trabajo persistente, adaptador y recursos
acotados. No es una función de ingesta. Los avisos de correo y terceros pasan por entrada global y Gateway;
el sondeo de reconciliación permanece como respaldo. Ver [operación](../../specs/ingestion-operations.md).
