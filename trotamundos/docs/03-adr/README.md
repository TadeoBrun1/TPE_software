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
| [0020](0020-obtener-novedades.md) | Avisos principales y reconciliación adaptable | proposed | 2 | RF-01/03, QA-1/5/6/8 |
| [0021](0021-autorizacion-correo.md) | Autorización delegada y mínimo privilegio | proposed | 2 | QA-8, CRN-4 |
| [0022](0022-tuberia-ingesta.md) | Pipes and Filters internos | proposed | 2 | RF-01/02/03, QA-6/8 |
| [0023](0023-adaptadores-proveedores.md) | Ports and Adapters por fuente | proposed | 2 | QA-6/9, CON-1/2 |
| [0024](0024-avance-y-publicacion-durable.md) | Outbox de ingesta y avance coordinado | proposed | 2 | QA-1/6, CRN-3/4 |
| [0025](0025-enrutamiento-de-avisos.md) | Directorio mínimo y enrutamiento regional | proposed | 2 | RF-03, QA-1/6/8 |
| [0026](0026-integracion-agencia.md) | Asistencia saliente del núcleo | proposed | 2 | RF-06, QA-6/9, CRN-3 |
| [0027](0027-publicacion-del-nucleo.md) | Outbox de cambios confirmados del núcleo | proposed | 2 | QA-6, CRN-3, RF-07 |
| [0028](0028-rabbitmq-y-politicas.md) | RabbitMQ con colas quorum y políticas | proposed | 2 | QA-1/6/8, CRN-3/4 |
| [0040](0040-modelo-de-lectura-del-panel.md) | Modelo de lectura del panel por usuario en la misma transacción | proposed | 3 | QA-2, QA-5 |
| [0041](0041-cache-local-y-notificador.md) | Caché local en la app y notificador separado | proposed | 3 | QA-3, QA-1, QA-5 |
| [0042](0042-particion-de-la-base-por-usuario.md) | Partición de la base por usuario con réplica sincrónica | proposed | 3 | QA-5, QA-4 |
| [0043](0043-escalado-reactivo-y-degradacion.md) | Escalado reactivo, priorización y degradación | proposed | 3 | QA-5, QA-2, QA-4 |
| [0044](0044-aplicacion-de-novedades-en-el-nucleo.md) | Aplicación de novedades: dueño por campo y asignación por fechas | proposed | 3 | RF-04, RF-05, QA-6 |
| [0045](0045-ciclo-de-vida-y-archivado-de-viajes.md) | Archivado diario y eliminación al año | proposed | 3 | RF-05, QA-2, CON-3 |

Mantener esta tabla actualizada al crear una ADR o cambiar su estado. La revisión cruzada y las pruebas se registran por separado.
