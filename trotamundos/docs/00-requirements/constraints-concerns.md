# Restricciones y preocupaciones arquitectónicas

**Qué es:** restricciones (no negociables) y concerns (decisiones de diseño que ningún requerimiento pide explícitamente).
**Mantiene:** ambos. **Estado:** BORRADOR.

## Restricciones

| ID | Restricción | Tipo | Origen |
|---|---|---|---|
| CON-1 | El diseño se hace con ADD, con 4 iteraciones como mínimo | Proceso | Enunciado |
| CON-2 | Decisiones documentadas con ADRs en formato MADR | Documentación | Enunciado |
| CON-3 | Vistas arquitectónicas adecuadas (módulos, C&C, despliegue, secuencia) | Documentación | Enunciado |
| CON-4 | Documentación en formato Wiki con actualizaciones periódicas | Entrega | Enunciado |
| CON-5 | Prototipo trazable, consistente con la arquitectura y que respeta las especificaciones (spec-driven) | Implementación | Enunciado |
| CON-6 | Equipo de 2 personas y 10 días para la primera entrega | Recursos | Acordado en el grupo |
| CON-7 | Integración con terceros solo mediante APIs estándar | Técnica | Enunciado |
| CON-8 | Tecnología y nube del prototipo: **a definir** | Técnica | Pendiente (registrar en ADR) |

## Preocupaciones (concerns)

| ID | Concern | Iteración donde se trata |
|---|---|---|
| CRN-1 | Estructura inicial del sistema | 1 |
| CRN-2 | Registro de eventos y monitoreo | 4 |
| CRN-3 | Manejo de errores de ingesta y reintentos | 2 |
| CRN-4 | Despliegue y entornos del prototipo | 3 |
| CRN-5 | Trazabilidad entre drivers, ADRs, specs y código | Todas |

## Supuestos

- No existen restricciones de tecnología impuestas por los docentes más allá de lo anterior. Confirmar.
