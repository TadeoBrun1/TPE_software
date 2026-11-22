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
   | 5 (2da entrega, módulo avanzado) | 0080 – 0099 |
   | Extra | 0100 en adelante |

3. Una ADR **no se borra**. Si cambia la decisión, la vieja pasa a `superseded by ADR-XXXX` y se crea otra.
4. Toda ADR indica el driver que la motiva y las **alternativas descartadas** (al menos 2 opciones consideradas).
5. Toda ADR se enlaza desde la iteración que la creó y desde las vistas que afecta.
6. Es una decisión arquitectónica si: afecta a varios componentes o iteraciones, cambia un QA, responde a una
   restricción, es costosa de revertir o cambia cómo se construye o despliega el sistema.

## Índice

| ADR | Título | Estado | Iteración | Drivers |
|---|---|---|---|---|
| [0000](0000-usar-madr.md) | Usar MADR para registrar decisiones | accepted | Previa | Requisito del enunciado |
| [0001](0001-nucleo-modular-con-procesos-separados.md) | Núcleo como monolito modular, con ingesta y analítica como procesos separados | accepted | 1 | CRN-1, QA-5, QA-4, QA-1, QA-9, RF-05 |
| [0002](0002-mensajeria-persistente-con-publicacion-suscripcion.md) | Comunicación asincrónica con intermediario de publicación y suscripción | accepted | 1 | QA-4, QA-1, QA-9, CON-2 |
| [0003](0003-despliegue-por-regiones-con-region-de-origen.md) | Despliegue multirregión con región de origen por usuario | accepted | 1 | QA-10 (multirregión), QA-4, CON-3 (suposición) |
| [0004](0004-arquitectura-de-referencia-clientes-ricos-y-puerta-de-entrada.md) | Arquitectura de referencia: clientes ricos y puerta de entrada única | accepted | 1 | CRN-1, CON-4, QA-4, QA-5 |
| [0020](0020-obtener-novedades.md) | Avisos principales y reconciliación adaptable | accepted | 2 | RF-01/03, QA-1/5/6/8 |
| [0021](0021-autorizacion-correo.md) | Autorización delegada y mínimo privilegio | accepted | 2 | QA-8, CRN-4 |
| [0022](0022-tuberia-ingesta.md) | Pipes and Filters internos | accepted | 2 | RF-01/02/03, QA-6/8 |
| [0023](0023-adaptadores-proveedores.md) | Ports and Adapters por fuente | accepted | 2 | QA-6/9, CON-1/2 |
| [0024](0024-avance-y-publicacion-durable.md) | Outbox de ingesta y avance coordinado | accepted | 2 | QA-1/6, CRN-3/4 |
| [0025](0025-enrutamiento-de-avisos.md) | Directorio mínimo y enrutamiento regional | accepted | 2 | RF-03, QA-1/6/8 |
| [0026](0026-integracion-agencia.md) | Asistencia saliente del núcleo | accepted | 2 | RF-06, QA-6/9, CRN-3 |
| [0027](0027-publicacion-del-nucleo.md) | Outbox de cambios confirmados del núcleo | accepted | 2 | QA-6, CRN-3, RF-07 |
| [0028](0028-rabbitmq-y-politicas.md) | RabbitMQ con colas quorum y políticas | accepted | 2 | QA-1/6/8, CRN-3/4 |
| [0040](0040-modelo-de-lectura-del-panel.md) | Modelo de lectura del panel por usuario en la misma transacción | accepted | 3 | QA-2, QA-5, RF-04 |
| [0041](0041-cache-local-del-panel.md) | Caché local del panel en la app, revalidada por versión | accepted | 3 | QA-3, QA-5, CON-4 |
| [0042](0042-particion-de-la-base-por-usuario.md) | Partición de la base por usuario en varios nodos con réplica sincrónica | accepted | 3 | QA-4, QA-5, CON-3 |
| [0043](0043-escalado-solo-reactivo.md) | Escalado automático solo reactivo | accepted | 3 | QA-5, QA-2, CON-5 |
| [0044](0044-novedades-y-cambios-manuales.md) | Novedades y cambios manuales: dueño por campo y marca de borrado | accepted | 3 | RF-04, QA-6 |
| [0045](0045-ciclo-de-vida-y-archivado-de-viajes.md) | Archivado diario, reactivación y eliminación al año | accepted | 3 | RF-05, QA-2, QA-5, CON-3 |
| [0046](0046-notificador-de-cambios-del-panel.md) | Notificador separado con evento propio y cola por instancia | accepted | 3 | QA-1, QA-5, QA-4, RF-04 |
| [0047](0047-priorizacion-y-degradacion-ante-sobrecarga.md) | Priorización y degradación ante sobrecarga | accepted | 3 | QA-2, QA-4, QA-5 |
| [0048](0048-asignacion-de-reservas-a-viajes.md) | Asignación automática de reservas a viajes por fechas | accepted | 3 | RF-05, RF-04 |
| [0060](0060-identidad-por-region-con-tokens.md) | Autenticación con un proveedor de identidad por región y tokens de vida corta | accepted | 4 | QA-7, QA-5, QA-4, CON-3 |
| [0061](0061-comparticion-con-cuenta-y-auditoria.md) | Compartición con personas designadas con cuenta, control en el núcleo y auditoría | accepted | 4 | QA-7, RF-08 |
| [0062](0062-lectura-de-viajes-compartidos-entre-regiones.md) | Lectura remota de viajes compartidos en la región del dueño | accepted | 4 | CON-3, QA-7, QA-2 |
| [0063](0063-tarjeta-de-resumen-para-redes-sociales.md) | Tarjeta de resumen pública para compartir en redes sociales | accepted | 4 | QA-7, interoperabilidad, CON-2 |
| [0064](0064-analitica-regional-seudonimizada.md) | Almacenes analíticos regionales con seudonimización al entrar | accepted | 4 | RF-07, QA-4, QA-5, CON-3 |
| [0065](0065-internacionalizacion-en-el-cliente.md) | Internacionalización: catálogos remotos, datos neutros y formato en el cliente | accepted | 4 | QA-10, QA-2, QA-3 |
| [0066](0066-detalles-de-reserva-extensibles-por-tipo.md) | Reserva con campos comunes y detalles con esquema propio por tipo | accepted | 4 | QA-9, RF-05 |
| [0067](0067-observabilidad-con-trazas-y-metricas.md) | Observabilidad con trazas, métricas por etapa y logs estructurados | accepted | 4 | CRN-2, QA-1, QA-4, CON-3 |
| [0080](0080-eleccion-del-modulo-avanzado.md) | Módulo avanzado de la segunda entrega: sistema de recomendación (opción A) | accepted | 5 | Enunciado (2da entrega), RF-09 |
| [0081](0081-proceso-de-recomendacion-con-perfiles-regionales.md) | Proceso de recomendación por región, alimentado por eventos y con su propio almacén de perfiles | accepted | 5 | RF-09, QA-11, QA-14, QA-16, CON-3, CON-5 |
| [0082](0082-busqueda-de-alternativas-con-cache-corta.md) | Búsqueda de alternativas en las APIs de los proveedores, con caché corta y búsquedas agrupadas | accepted | 5 | QA-11, QA-12, QA-17, CON-1, CON-2 |
| [0083](0083-ranking-aprendido-del-feedback.md) | Ranking de ofertas por características, aprendido del feedback, con un modelo regional versionado | accepted | 5 | RF-09.3, QA-11, QA-13, QA-15, CON-3, CON-5 |
| [0084](0084-entrega-y-aceptacion-de-sugerencias.md) | Sugerencias por una API propia con aviso del notificador, y aceptación como reserva propuesta en el núcleo | accepted | 5 | RF-09.1, RF-09.2, QA-2, QA-7, QA-11, QA-13 |
| [0085](0085-eliminacion-de-la-cuenta.md) | Eliminación de la cuenta: borrado inmediato en el núcleo y aviso por evento al resto de los procesos | accepted | 5 | QA-14, QA-7, CON-3 (pendiente de 0081 y 0064) |

Las ADRs 0080 a 0085 están `accepted` por decisión de los dos integrantes; su integración en `main` depende de la
revisión del PR #12.

Mantener esta tabla actualizada al crear una ADR o cambiar su estado. La revisión cruzada y las pruebas se registran por separado.
