# Vistas arquitectónicas

Cada vista es un archivo. Todas siguen [view-template.md](view-template.md) y se actualizan en cada iteración.

## Índice

| Vista | Tipo de estructura | Sirve para razonar sobre | Archivo | Se actualiza en |
|---|---|---|---|---|
| Modelo de dominio | Soporte | Vocabulario común | [domain-model.md](domain-model.md) | Prep., 1, 2, 3 |
| Módulos | Módulos (estática) | Modificabilidad, reparto del trabajo | [module-view.md](module-view.md) | 1, 2, 3, 4 |
| Componentes y conectores | C&C (en ejecución) | Performance, disponibilidad, seguridad | [cc-view.md](cc-view.md) | 1, 2, 3, 4 |
| Despliegue | Asignación | Escalabilidad, disponibilidad, multirregión | [deployment-view.md](deployment-view.md) | 1, 3, 4 |
| Secuencia | C&C (comportamiento) | Escenarios de calidad y casos de uso | [sequence-views.md](sequence-views.md) | 2, 3, 4 |
| Interfaces | Contratos | Integración y spec-driven | [interfaces.md](interfaces.md) | 1 a 4 |

Las secuencias de la iteración 3 (SEQ-3, SEQ-4 y SEQ-6) están en [sequence-views.md](sequence-views.md).

Los tipos de estructura no se mezclan dentro de una misma vista (módulos, C&C y asignación van por separado).
Los diagramas son Mermaid.

## Cómo agregar una vista nueva

1. Copiar [view-template.md](view-template.md).
2. Completar propósito, diagrama, catálogo y rationale.
3. Agregar la fila al índice de arriba y a [../architecture.md](../architecture.md).

## Refinamiento propuesto de ingesta (iteración 2)

* [Componentes y conectores de ingesta](ingestion-view.md).
* [Secuencias de correo, avisos, recuperación y revocación](ingestion-sequences.md).

Estos detalles complementan las vistas generales; deben integrarse con la actualización de la iteración 1.
