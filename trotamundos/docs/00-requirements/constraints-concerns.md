# Restricciones y preocupaciones arquitectónicas

**Qué es:** restricciones (decisiones ya tomadas o impuestas que le quitan libertad al diseño del sistema) y concerns (aspectos de diseño que ningún requerimiento pide de forma explícita, pero que la arquitectura tiene que resolver).
**Mantiene:** ambos. **Estado:** COMPLETADO.

## Restricciones

Criterio: algo es una restricción si elimina opciones de diseño. Si solo pide un resultado o un comportamiento, es un requerimiento o un atributo de calidad.

| ID | Restricción | Libertad que quita | Origen | Estado |
|---|---|---|---|---|
| CON-1 | La integración con aerolíneas, hoteles y rentadoras se hace solo mediante APIs estándar | No se pueden definir interfaces propias con esos proveedores: el diseño se adapta a sus APIs | Enunciado: "a través de APIs estándar" | Confirmada |
| CON-2 | Los proveedores de correo, las redes sociales, la agencia de viajes y los sistemas de terceros son sistemas externos existentes que no podemos modificar | No se puede cambiar cómo se comunican ni pedirles ajustes: hay que tolerar sus latencias, límites y caídas | Inferida del enunciado | Confirmada |
| CON-3 | Los datos personales se tratan según la normativa de protección de datos de las regiones donde opera el sistema | Dónde y cómo se almacenan y procesan los datos queda condicionado por la región del usuario | Suposición: el enunciado dice que el sistema "procesa información personal" y debe operar en varias regiones | **Suposición a validar** (falta fijar qué normativa se toma como criterio) |

El enunciado **no impone** lenguaje, nube, base de datos ni framework. Esas son decisiones de diseño y se toman en las iteraciones con su ADR, no son restricciones.

## Preocupaciones (concerns)

| ID | Concern | Por qué importa | Se trata en la iteración |
|---|---|---|---|
| CRN-1 | Estructura general del sistema y asignación de funcionalidad a elementos | Es el punto de partida; ningún QA lo pide por sí solo | 1 |
| CRN-2 | Registro de eventos (logging), monitoreo y trazas | Hace falta para detectar fallas y medir QA-1 y QA-4; el enunciado no lo pide de forma explícita | 4 |
| CRN-3 | Manejo de errores y reintentos al integrarse con sistemas externos | Las fuentes externas fallan o devuelven datos inválidos (QA-1, QA-6) | 2 |
| CRN-4 | Gestión de configuración y secretos (credenciales de terceros y autorizaciones de correo) | Se manejan credenciales de terceros y autorizaciones de usuarios (QA-8). Es una propuesta | 2 |

Un concern no se mide como un QA: es algo que hay que decidir igual. La columna de iteración es una guía de planificación y debe coincidir con el [plan de iteraciones](../01-add/iteration-plan.md).
