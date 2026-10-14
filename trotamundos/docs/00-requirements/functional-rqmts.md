# Requerimientos funcionales

**Qué es:** requerimientos extraídos del enunciado y su priorización.
**Mantiene:** ambos. **Estado:** BORRADOR. Pasar por `/generador-casos-de-uso` para obtener los casos de uso (plantilla Cockburn).

Los RF-01 a RF-07 salen del enunciado. La priorización es **suposición a validar**: se hizo según cuánto condiciona
la estructura del sistema.

| ID | Requerimiento | Origen | Prioridad (supuesta) | Primario |
|---|---|---|---|---|
| RF-01 | Sondear y escanear el correo del usuario para detectar correos de viaje y agregar las reservas al itinerario | Procesamiento de correo | Alta | Sí |
| RF-02 | Filtrar y crear listas de remitentes seguros (whitelists) | Filtros y whitelists | Media | No |
| RF-03 | Integrarse con sistemas de terceros por APIs estándar para obtener detalles, actualizaciones y cancelaciones | Integración con terceros | Alta | Sí |
| RF-04 | Agregar, actualizar y eliminar reservas manualmente | Gestión manual | Media | No |
| RF-05 | Agrupar elementos por viaje; archivar o eliminar de la vista principal al completarse | Ciclo de vida del viaje | Alta | Sí |
| RF-06 | Integrarse con la agencia de viajes preferida para resolver problemas | Resolución de problemas | Media | No |
| RF-07 | Recopilar datos analíticos (tendencias, destinos, cancelaciones) y permitir consultas pesadas al equipo de datos | Analítica de datos | Media | No |
| RF-08 | Compartir un itinerario con personas designadas | Atributo Seguridad | Media | No |

### Funcionalidad avanzada (2da entrega, elegir al menos una)

| Opción | Descripción | Estado |
|---|---|---|
| A | Sistema de recomendación con optimización human-in-the-loop | **Decisión pendiente** |
| B | Asistente virtual (chatbot) de primer nivel, derivando casos complejos a la agencia | **Decisión pendiente** |

> Cuando se elija una opción, registrar la decisión en una ADR (bloque de la iteración que la incorpore) y agregar el RF.

## Casos de uso

<!-- Pegar acá el resultado de /generador-casos-de-uso, o enlazar a docs/00-requirements/use-cases.md -->

## Supuestos

- Los RF se pensaron para los tipos de reserva del enunciado: hoteles, autos, vuelos, trenes y autobuses. Trenes y
  autobuses se tratan como integraciones futuras en el atributo de evolucionabilidad.
