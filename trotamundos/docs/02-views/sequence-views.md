# Vistas de secuencia

**Tipo:** Comportamiento
**Mantiene:** quien documenta cada escenario
**Estado:** PENDIENTE

Un diagrama por escenario clave. Debajo de cada uno, una descripción de qué representa y qué driver demuestra.

## Índice de secuencias

| ID | Escenario | Driver | Iteración | Estado |
|---|---|---|---|---|
| SEQ-1 | Llega un correo de reserva y se agrega al itinerario | RF-01, QA-1 | 2 | Propuesta documentada; evaluación pendiente |
| SEQ-2 | Un tercero informa una cancelación | RF-03, QA-6 | 2 | Propuesta documentada; evaluación pendiente |
| SEQ-3 | El viajero consulta su panel de viajes | QA-2, QA-3 | 3 | Pendiente |
| SEQ-4 | Falla una instancia y el tráfico se redirige | QA-4 | 3 | Pendiente |
| SEQ-5 | Se comparte un itinerario con otra persona | QA-7 | 4 | Pendiente |

## Refinamiento de SEQ-1 y SEQ-2

Los recorridos de ingesta están en [ingestion-sequences.md](ingestion-sequences.md): son diseño propuesto, no
pruebas. Incluyen sondeo autorizado del correo, avisos de terceros y consulta de detalles, recuperación de
publicación y revocación. Reemplazan el ejemplo anterior que dibujaba un correo como aviso iniciado por el proveedor
y confundía novedad detectada con cambio aplicado. SEQ-3/4/5 se mantienen pendientes para sus responsables.
