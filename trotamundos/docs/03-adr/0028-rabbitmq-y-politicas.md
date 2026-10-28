---
status: "proposed"
date: 2026-10-27
decision-makers: "Tomas Lateana; revisión cruzada en PR #4 pendiente"
consulted: "ChatGPT/Codex y documentación primaria enlazada"
---

# RabbitMQ con colas quorum para los flujos de ingesta

## Context and Problem Statement

ADR-0002 fija publicación/suscripción persistente, pero no producto ni políticas. Ingesta debe conservar trabajo,
controlar entrega y alimentar al núcleo sin exponer su base. No existe requerimiento de replay ilimitado del log.
Hay que elegir broker y concretar las hipótesis operativas, no mantener esta decisión indefinidamente abierta.

## Decision Drivers

* QA-1: frescura de extremo a extremo.
* QA-6: 99,9 % de mensajes válidos sin pérdida ni duplicación.
* QA-8: acceso restringido.
* CRN-3 y CRN-4: recuperación, configuración y secretos.
* ADR-0001, ADR-0002 y ADR-0003: límites de procesos y despliegue.

## Considered Options

* RabbitMQ con topic exchanges y colas quorum.
* Apache Kafka con temas particionados y grupos de consumidores.
* Cola transaccional implementada sobre una base relacional.

## Decision Outcome

Se elige **RabbitMQ** para el diseño, con AMQP 0-9-1, TLS, colas quorum, publisher confirms, retorno de no enrutados
y ACK manual posterior al resultado durable. [Políticas](../../specs/ingestion-operations.md) define topología,
presupuesto, carga inicial, reintentos, retención, contrapresión y métricas. No se cambia la propiedad del núcleo.

Kafka es válido si el requisito dominante pasa a ser retener/reproducir un log a gran escala; no se descarta por
ser incapaz de satisfacer estos flujos. Aquí se priorizan enrutamiento a colas y confirmación individual de trabajo.
Una cola en base requeriría diseñar reparto pub/sub, entrega, seguridad y operación del intermediario, en vez de
utilizar un broker que ya ofrece esas piezas. No se elige RabbitMQ por el tamaño/plazo del grupo del TPE.

### Patrones y tácticas

* Patrón o mecanismo: Dead Letter Channel mediante casos aparcados y avisos mínimos; cola replicada.
* Tácticas: Retry y Exception handling; redundancia de estado con líder y seguidores, sin equiparar quorum a ejecución activa de negocio en todas las réplicas.

### Consequences

* A favor: enrutamiento a colas independientes por consumidor y confirmación explícita de recepción/procesamiento.
* A favor: cola replicada para el trabajo pendiente, con contrapresión y control de consumo.
* En contra: operar mayoría y capacidad; tres miembros en tres zonas para tolerar pérdida de cualquiera de ellas.
* En contra: no es historial de negocio/replay; reentregas e idempotencia y orden real siguen en aplicación.
* En contra: confirmar recepción no demuestra actualización visible ni capacidad para todos los usuarios.

### Confirmation

El paso 7 analiza escenarios y registra riesgos. El prototipo debe comprobar publicación, confirmación del broker y ACK del consumidor, reentrega,
reinicio y mensajes no enrutados; se declara pendiente de ejecución. Seleccionar release y digest al implementar,
verificar compatibilidad y no usar una etiqueta móvil `latest`. Los ADR permanecen proposed hasta revisión cruzada;
la elección y el análisis ya están documentados, no falta elegir el producto.

## Pros and Cons of the Options

### RabbitMQ

Enrutamiento y trabajo confirmado por consumidor son adecuados para estos flujos. Requiere quorum, administración
y capacidad de colas; no elimina outbox, duplicados ni estados externos desordenados.

### Apache Kafka

Log retenido, replay y grupos particionados permiten varios consumidores y buen orden por partición. Requiere
especificar offsets/retención/particiones y traducir confirmación de trabajo y reintentos a ese modelo. No se
necesita aún replay de toda la historia para el recorrido operativo; puede reconsiderarse con otros drivers.

### Cola sobre base relacional

Transacciones locales ayudan a conservar pendientes. Debe construirse el intermediario para reparto independiente,
reintentos, flujo de consumidores y permisos; además puede competir con los datos del dominio si comparte recursos.

## More Information

[Iteración 2](../01-add/iteration-2-ingestion.md), [C&C ingesta](../02-views/ingestion-view.md),
[operación y fuentes](../../specs/ingestion-operations.md), [eventos](../../specs/asyncapi/booking-change-detected.v1.yaml).
La política de tres zonas del broker refina el mínimo zonal de ADR-0003; no agrega recuperación entre regiones.
