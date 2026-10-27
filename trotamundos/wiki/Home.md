# Wiki TPE Ingeniería de software: Trotamundos

El fin de este proyecto es diseñar la arquitectura del sistema 'Trotamundos' mediante iteraciones ADD, documentando todas las decisiones elegidas con sus respectivas ventajas y desventajas, con sus distintos tipos de vistas (vista estática, dinámica, hexagonal, etc.), y mediante la elaboración de un prototipo.

### ¿Qué es el sistema 'Trotamundos'?

El sistema Trotamundos es un panel de gestión de viajes en línea para permitir a los viajeros ver todas sus reservas existentes organizadas por viaje, ya sea a través de la web o desde su dispositivo móvil. El objetivo es ofrecer un único punto de verdad para todos los arreglos de viaje (hoteles, autos, vuelos, trenes, autobuses) en una interfaz simple centrada en el viaje, mitigando la frustración de rastrear múltiples aplicaciones y bandejas de correo.

---

### Requerimientos iniciales

| Página | Qué contiene |
|---|---|
| [Diagrama de contexto](https://github.com/TadeoBrun1/TPE_software/blob/main/trotamundos/docs/00-requirements/context-diagram.md) | Límites del sistema y actores externos |
| [Requerimientos funcionales](https://github.com/TadeoBrun1/TPE_software/blob/main/trotamundos/docs/00-requirements/functional-rqmts.md) | Qué hace el sistema |
| [Atributos de calidad](https://github.com/TadeoBrun1/TPE_software/blob/main/trotamundos/docs/00-requirements/quality-attribute-scenarios.md) | Escenarios SEI de 6 partes |
| [Árbol de utilidad](https://github.com/TadeoBrun1/TPE_software/blob/main/trotamundos/docs/00-requirements/utility-tree.md) | Escenarios priorizados (importancia, dificultad) |
| [Restricciones y concerns](https://github.com/TadeoBrun1/TPE_software/blob/main/trotamundos/docs/00-requirements/constraints-concerns.md) | Lo que quita libertad al diseño y las preocupaciones de diseño |
| [Drivers arquitectónicos](https://github.com/TadeoBrun1/TPE_software/blob/main/trotamundos/docs/00-requirements/architectural-drivers.md) | Resumen priorizado que guía el diseño |

### Iteraciones ADD

La explicación del método y el documento de cada iteración están en una misma carpeta.

- [Proceso ADD e iteraciones](https://github.com/TadeoBrun1/TPE_software/tree/main/trotamundos/docs/01-add)

### Documentación derivada de las iteraciones

| Página | Qué contiene |
|---|---|
| [Arquitectura de Trotamundos](https://github.com/TadeoBrun1/TPE_software/blob/main/trotamundos/docs/architecture.md) | Documento central: resumen de todo y trazabilidad entre drivers, decisiones y vistas |
| [ADRs](https://github.com/TadeoBrun1/TPE_software/tree/main/trotamundos/docs/03-adr) | Decisiones de diseño con sus alternativas, ventajas y desventajas |
| [Vistas](https://github.com/TadeoBrun1/TPE_software/tree/main/trotamundos/docs/02-views) | Modelo de dominio, vista estática (módulos), componentes y conectores, despliegue, secuencias e interfaces |

### Código y seguimiento

- [Contratos (specs)](https://github.com/TadeoBrun1/TPE_software/tree/main/trotamundos/specs): OpenAPI y AsyncAPI
- [Prototipo](https://github.com/TadeoBrun1/TPE_software/tree/main/trotamundos/prototype)
- [Registro de trabajo del equipo](https://github.com/TadeoBrun1/TPE_software/blob/main/trotamundos/TEAM-LOG.md)
