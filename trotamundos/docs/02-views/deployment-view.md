# Vista de despliegue

**Tipo:** Asignación (software a infraestructura)
**Actualizada en la iteración:** 1
**Mantiene:** Ambos
**Estado:** Versión inicial (iteración 1). La iteración 3 la refina (escalado, tiempos de conmutación).

## 1. Propósito

Mostrar dónde corre cada elemento. Sirve para razonar sobre escalabilidad, disponibilidad y multirregión.

## 2. Presentación primaria

```mermaid
flowchart TB
    U["Clientes web y móvil<br/>y notificaciones de terceros"] --> E["Entrada global redundante<br/>(enruta a la región de origen)"]

    subgraph R1["Región 1 (celda completa)"]
        direction TB
        subgraph Z1["Zona de falla A"]
            G1["Puerta de entrada"]
            N1["Núcleo × n"]
            I1["Ingesta × n"]
            B1["Broker (nodo)"]
            D1[("Base primaria")]
        end
        subgraph Z2["Zona de falla B"]
            G2["Puerta de entrada"]
            N2["Núcleo × n"]
            I2["Ingesta × n"]
            B2["Broker (nodo)"]
            D2[("Réplica sincrónica")]
        end
        subgraph Z3["Zona de falla C (broker)"]
            B3["Broker (tercer miembro quorum)"]
        end
        A1["Analítica"]
        D1 -. "replicación sincrónica" .- D2
        B1 -. "replicación quorum" .- B2
        B2 -. "replicación quorum" .- B3
    end

    subgraph R2["Región 2 (celda completa)"]
        X2["Misma estructura que la Región 1"]
    end

    E --> G1
    E --> G2
    E --> X2
```

## 3. Catálogo de elementos

| Nodo o recurso | Qué corre | Réplicas | Observaciones |
|---|---|---|---|
| Entrada global | Enrutamiento por región de origen | Redundante | Resuelve la región a partir de la identidad del usuario; para notificaciones de terceros, se resuelve en la iteración 2 |
| Región (celda) | Todos los procesos y datos de los usuarios con esa región de origen | Una por mercado | Sumar una región es desplegar una celda más |
| Zona de falla | Puerta de entrada, núcleo, ingesta, broker y base | Al menos 2 por región | Redundancia activa de los procesos: todas las zonas atienden tráfico; la base es primaria en una zona y réplica en la otra (redundancia pasiva) |
| Base operativa | Datos de la región, particionados por usuario | Primaria + réplica sincrónica en otra zona | Conmutación automática |
| Analítica | Proceso analítico | Por región | Dónde se agregan los datos de todas las regiones: iteración 4 |

## 4. Rationale

| Decisión | ADR |
|---|---|
| Multirregión con región de origen; zonas de falla | [0003](../03-adr/0003-despliegue-por-regiones-con-region-de-origen.md) |
| Puerta de entrada por región, redundante, como único acceso | [0004](../03-adr/0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) |

## 5. Drivers que sustenta

| Driver | Cómo lo sustenta |
|---|---|
| QA-4 Disponibilidad | La falla de una instancia o zona se absorbe con las otras zonas (redundancia activa) |
| QA-5 Escalabilidad | Cada proceso tiene `n` instancias por zona y escala por separado |
| QA-10 Multirregión | Cada región es una celda independiente que atiende a sus usuarios |
| CON-3 (suposición) | Los datos de un usuario quedan en su región de origen |

## 6. Prototipo

El prototipo corre una sola región en una máquina con `docker compose` (núcleo, ingesta y broker). La multirregión y
las zonas se documentan acá, pero no se simulan.

## 7. Vistas relacionadas

[Componentes y conectores](cc-view.md) · [Módulos](module-view.md)

## Refinamiento de broker de la iteración 2

ADR-0028 elige RabbitMQ con tres miembros quorum en tres zonas distintas por región. La tercera zona del dibujo
aloja el tercer miembro; el mínimo inicial de dos zonas para procesos generales no se interpreta como quorum
suficiente en un cluster de dos nodos. Perder una zona conserva dos de tres miembros. Si la infraestructura no
ofrece esas tres zonas, registrar limitación y no afirmar tolerancia a la caída de cualquiera de ellas.
[Políticas](../../specs/ingestion-operations.md). El prototipo funcional de un nodo no valida disponibilidad zonal.
