# Requerimientos funcionales

**Qué es:** requerimientos extraídos del enunciado y su priorización.
**Mantiene:** ambos. **Estado:** COMPLETADO (lista de requerimientos revisada contra el enunciado).

Los RF-01 a RF-07 salen de la sección "Requerimientos Funcionales Principales" del enunciado. RF-08 se deriva del atributo de Seguridad (uso compartido de itinerarios con personas designadas) y de Interoperabilidad (redes sociales). La priorización es **suposición a validar**: se hizo según cuánto condiciona
la estructura del sistema.

| ID | Requerimiento | Origen | Prioridad (supuesta) | Primario |
|---|---|---|---|---|
| RF-01 | Sondear y escanear el correo del usuario para detectar correos de viaje y agregar las reservas al itinerario | Procesamiento de correo | Alta | Sí |
| RF-02 | Filtrar y crear listas de remitentes seguros (whitelists) | Filtros y whitelists | Media | No |
| RF-03 | Integrarse con sistemas de viajes y agencias de terceros por APIs estándar para obtener detalles, actualizaciones y cancelaciones | Integración con terceros | Alta | Sí |
| RF-04 | Agregar, actualizar y eliminar reservas manualmente | Gestión manual | Media | No |
| RF-05 | Agrupar elementos por viaje; archivar o eliminar automáticamente de la vista principal al completarse el viaje | Ciclo de vida del viaje | Alta | Sí |
| RF-06 | Integrarse con la agencia de viajes preferida para resolver problemas | Resolución de problemas | Media | No |
| RF-07 | Recopilar datos analíticos (tendencias, destinos, cancelaciones) y permitir consultas pesadas al equipo de datos | Analítica de datos | Media | No |
| RF-08 | Compartir un itinerario con personas designadas | Atributo Seguridad | Media | No |

### Funcionalidad avanzada (2da entrega, elegir al menos una)

| Opción | Descripción | Estado |
|---|---|---|
| A | Sistema de recomendación con optimización human-in-the-loop | **Elegida** (2026-11-22, [ADR-0080](../03-adr/0080-eleccion-del-modulo-avanzado.md)) → RF-09 |
| B | Asistente virtual (chatbot) de primer nivel, derivando casos complejos a la agencia | Descartada; la comparación queda en ADR-0080 |

| ID | Requerimiento | Origen | Prioridad (supuesta) | Primario |
|---|---|---|---|---|
| RF-09 | Sugerir proactivamente alternativas de alojamiento y transporte cuando una reserva del viajero se cancela, a partir de su historial y preferencias, y refinar las sugerencias con su interacción (human-in-the-loop) | Requerimientos avanzados, opción A | Alta | Sí (2da entrega) |

Alcance de RF-09 acordado por el equipo (las rutas de varios tramos quedan fuera):

| ID | Detalle |
|---|---|
| RF-09.1 | Ante la cancelación de una reserva de alojamiento o transporte (por el proveedor o por una disrupción), el sistema busca alternativas del mismo tipo, las ordena según el perfil del viajero y le avisa |
| RF-09.2 | El viajero acepta una sugerencia: queda en el viaje como **reserva propuesta** (no confirmada) con el enlace a la oferta del proveedor. Trotamundos no compra ni emite reservas; si el viajero reserva, la reserva real llega por la ingesta y reemplaza a la propuesta |
| RF-09.3 | El viajero rechaza una sugerencia o ajusta parámetros (precio máximo, máximo de escalas, franja horaria, cadena o aerolínea preferida); las sugerencias se reordenan y el feedback refina el modelo |
| RF-09.4 | La recomendación está activada por defecto; el viajero puede desactivarla y borrar su perfil de preferencias |
