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
| [0000](0000-usar-madr.md) | Usar MADR para registrar decisiones | accepted | Previa | CON-2 |
| 0001 | `<estilo arquitectónico>` | proposed | 1 | CRN-1, QA-5 |
| 0002 | `<comunicación entre servicios>` | proposed | 1 | QA-5, QA-9 |
| 0003 | `<separación de la carga analítica>` | proposed | 1 | QA-2, RF-07 |
| 0004 | `<estrategia de despliegue multirregión>` | proposed | 1 | QA-4, QA-10 |

Mantener esta tabla actualizada al crear una ADR nueva o cambiar su estado.
