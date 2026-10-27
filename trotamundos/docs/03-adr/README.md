# Architecture Decision Records (ADR)

Registramos las decisiones de arquitectura en formato **MADR** (Markdown Architectural Decision Records).
Plantilla: [adr-template.md](adr-template.md).

## Reglas

1. **Una decisión por archivo**, con nombre `NNNN-titulo-con-guiones.md`.
2. Numeración por **bloque de iteración** para evitar choques entre ramas paralelas:

   | Iteración | Rango |
   |---|---|
   | 1 | 0001 – 0019 |
   | 2 | 0020 – 0039 |
   | 3 | 0040 – 0059 |
   | 4 | 0060 – 0079 |
   | Extra | 0080 en adelante |

3. Una ADR **no se borra**. Si cambia la decisión, la vieja pasa a `superseded by ADR-XXXX` y se crea otra.
4. Toda ADR indica el driver que la motiva y las **alternativas descartadas** (al menos 2 opciones consideradas).
5. Toda ADR se enlaza desde la iteración que la creó y desde las vistas que afecta.
6. Es una decisión arquitectónica si: afecta a varios componentes o iteraciones, cambia un QA, responde a una
   restricción, es costosa de revertir o cambia cómo se construye o despliega el sistema.

## Índice

| ADR | Título | Estado | Iteración | Drivers |
|---|---|---|---|---|
| [0000](0000-usar-madr.md) | Usar MADR para registrar decisiones | accepted | Previa | Requisito del enunciado |
| [0001](0001-nucleo-modular-con-procesos-separados.md) | Núcleo como monolito modular, con ingesta y analítica como procesos separados | proposed | 1 | CRN-1, QA-5, QA-4, QA-1, QA-9, RF-05 |
| [0002](0002-mensajeria-persistente-con-publicacion-suscripcion.md) | Comunicación asincrónica con intermediario de publicación y suscripción | proposed | 1 | QA-4, QA-1, QA-9, CON-2 |
| [0003](0003-despliegue-por-regiones-con-region-de-origen.md) | Despliegue multirregión con región de origen por usuario | proposed | 1 | QA-10 (multirregión), QA-4, CON-3 (suposición) |
| [0004](0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) | Arquitectura de referencia: clientes ricos y puerta de entrada única | proposed | 1 | CRN-1, CON-4, QA-4, QA-5 |

Mantener esta tabla actualizada al crear una ADR nueva o cambiar su estado.

## Iteración 2 — decisiones propuestas

| ADR | Decisión | Estado | Drivers |
|---|---|---|---|
| [0020](0020-obtener-novedades.md) | Sondeo configurable y avisos disponibles | proposed | RF-01/03, QA-1/6 |
| [0021](0021-autorizacion-correo.md) | Autorización delegada y mínimo privilegio | proposed | QA-8, CRN-4 |
| [0022](0022-tuberia-ingesta.md) | Etapas internas de procesamiento | proposed | RF-01/02/03, QA-6/8 |
| [0023](0023-adaptadores-proveedores.md) | Puertos y adaptadores por fuente | proposed | QA-6/9, CON-1/2 |
| [0024](0024-avance-y-publicacion-durable.md) | Avance/outbox coordinados y reintentos controlados | proposed | QA-1/6, CRN-3/4 |

Estado propuesto sin aprobación cruzada registrada. La base ya incluye la primera iteración publicada en main como propuesta.

## Alineación de ingesta con la primera revisada

| ADR | Decisión | Estado |
|---|---|---|
| [0025](0025-enrutamiento-de-avisos.md) | Enrutamiento regional de avisos por Gateway | proposed |
| [0026](0026-integracion-agencia.md) | Integración de asistencia con agencia | proposed |
| [0027](0027-publicacion-del-nucleo.md) | Outbox transaccional de cambios confirmados | proposed |

0020–0024 se refinan: versión externa opcional, configuración autoritativa en núcleo y receptor interno.
