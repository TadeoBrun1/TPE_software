# Cierre documental de primera entrega — Trotamundos

**Fecha:** 2026-10-28. **Base revisada:** main, commit `00f21b9`.
**Preparación:** revisión analítica de ambos integrantes, con asistencia de IA (ver [uso de IA](../../ai/prompts.md)).
La revisión de este cierre por el equipo se registra mediante el PR que lo integra. No se afirma una reunión grupal de
Risk Storming.

## Alcance y evidencia de integración

Se revisaron la consigna, requisitos, cuatro iteraciones ADD, ADRs, vistas, contratos y navegación de la Wiki.
El cierre corresponde a documentación de diseño. El PDF general exige un prototipo, pero no desglosa todo el
alcance por fecha: el equipo debe respetar el criterio de la cátedra. La opción avanzada A o B está indicada
expresamente para la segunda entrega. No se presenta el repositorio como un sistema implementado.

| Iteración | ADRs | Evidencia de integración en main |
|---|---|---|
| 1, estructura | 0001 a 0004 | [PR #3](https://github.com/TadeoBrun1/TPE_software/pull/3), merge 05a8fd7 |
| 2, ingesta | 0020 a 0028 | [PR #4](https://github.com/TadeoBrun1/TPE_software/pull/4), merge 0801315 |
| 3, consulta y escala | 0040 a 0048 | [PR #6](https://github.com/TadeoBrun1/TPE_software/pull/6), merge 54122ee |
| 4, seguridad y evolución | 0060 a 0067 | [PR #7](https://github.com/TadeoBrun1/TPE_software/pull/7), merge 00f21b9 |

`accepted` registra la adopción documental de decisiones integradas, no implementación correcta ni satisfacción
medida de sus atributos. ADR-0000 ya registraba aceptación del formato MADR. La incorporación del diseño no
elimina los riesgos ni valida automáticamente las suposiciones de requisitos.

## Verificaciones realizadas en la revisión técnica

| Comprobación | Resultado y límite |
|---|---|
| Cuatro iteraciones ADD | Todas contienen los pasos 2 a 7 |
| ADRs | 31 registros con contexto, drivers, alternativas, decisión y consecuencias |
| Mermaid | Sintaxis de 18 diagramas aceptada por el parser; no equivale a prueba de comportamiento ni a garantía de legibilidad en toda pantalla |
| OpenAPI y JSON Schema | Validación estructural correcta; referencias internas YAML existentes |
| Navegación | Sin enlaces Markdown locales rotos; tablas con separadores y diff sin errores de formato |
| Correcciones de iteración 4 | Las correcciones de la auditoría y de la revisión cruzada están incorporadas en `main` mediante PR #7 |
| Wiki | Las páginas `Home` y `_Sidebar` se mantienen en la carpeta `wiki/` del repositorio y se copian a la Wiki de GitHub; sus links apuntan a archivos existentes en `main` |
| Autoría | Historial Git y TEAM-LOG muestran aportes de ambos integrantes; este cierre no agrega aprobaciones ni pruebas ficticias |

Las verificaciones son sobre artefactos, no pruebas del prototipo.

## Recorrido transversal de escenarios

| Driver o requisito | Recorrido y decisiones | Resultado documental | Evidencia o riesgo pendiente |
|---|---|---|---|
| RF-01, RF-02 y RF-03 | Avisos y reconciliación; autorización; filtros; adaptadores; procesador; outbox; núcleo | Responsabilidades y contratos definidos | Proveedores reales, cuotas, extracción y casos incompletos |
| RF-04 | Gestión manual con control de versión, dueño por campo y marca de borrado, ADR-0044 | Diseño definido | Concurrencia y conciliación entre fuentes |
| RF-05 | Asignación a viajes, archivado, reactivación y eliminación, ADR-0045/0048 | Diseño definido | Validar márgenes de fechas y comportamiento de reservas pendientes |
| RF-06 | Solicitud autorizada, módulo saliente de asistencia y resultado recuperable, ADR-0026 | Diseño definido | API de agencia, idempotencia externa y respuesta incierta |
| RF-07 | Outbox, booking.facts, recepción idempotente y almacén regional, ADR-0064 | Diseño definido con límites | Consultas útiles, hechos tardíos sin clave, retención y reidentificación |
| RF-08 y QA-7 | Principal regional, invitación atada al email, permiso por lectura, auditoría y proyección sin details | Diseño definido | Probar actor ajeno por todas las rutas, revocación y fallo de auditoría; se mantiene riesgo residual de auditoría y logs simultáneamente caídos |
| QA-1 | Fuente, detección, publicación, cola, aplicación y cliente; presupuesto total 300 s | Parcial; no demostrado | Avisos perdidos y reconciliación lenta; cuotas a escala. Medición incompleta no se imputa como éxito |
| QA-2 | Lectura del panel precalculado, versión, límites de contenido y priorización | Condicionado a carga y tamaño | Pruebas bajo pico, latencia de red y tiempo de escalado |
| QA-3 | Caché local, revalidación y caso sin caché | Parcial | Medir también aperturas sin caché dentro del 95 %; sesión iniciada no garantiza caché |
| QA-4 | Zonas, monitor, fencing, conmutación y sondas temporales | Diseñado; no medido | Medir detección, recuperación y 300 s/mes; pérdida de región no recuperada; ventana de una sola copia |
| QA-5 | Particiones por usuario, broker, ocho shards y escalado reactivo | Parcial | Carga y skew reales; un escalón puede superar capacidad durante el arranque. CON-5 es una suposición, no una medición de capacidad |
| QA-6 | Identidad de mensaje y reserva separadas, deduplicación y transacciones | Diseñado; no medido | Reentregas, desorden, cancelación anterior al alta y conflictos sin versión |
| QA-8 | Autorización delegada, mínimo privilegio y barrera de revocación | Diseño definido | Carreras, conservación y validación del proveedor real |
| QA-9 | Campos comunes, tipo abierto y detalles registrados, ADR-0023/0066 | Diseño definido | Agregar ferry y registrar esfuerzo frente a 10 días-persona, sin editar medios existentes |
| QA-10 | Catálogos, formatos, zonas IANA, identidad y datos regionales | Parcial | Dos idiomas y zonas; latencia de conexión nueva desde lejos y cobertura sin caché |
| Interoperabilidad con redes | Tarjeta pública separada del itinerario, ADR-0063 | Interpretación documentada | Confirmar con la cátedra que el resumen satisface la interacción pedida |
| CRN-1 a CRN-4 | Estructura, observabilidad, errores y secretos en sus iteraciones | Responsabilidades asignadas | Implementar configuración, instrumentación y operación |

## Riesgos cruzados sobre componentes y despliegue

Esta es una revisión analítica de riesgos, no una sesión grupal registrada ni nuevas decisiones de arquitectura.

| Riesgo | Consecuencia | Tratamiento existente | Responsable de seguimiento |
|---|---|---|---|
| Cuotas o avisos perdidos | Actualizaciones fuera de 300 s | Reconciliación, modelo de solicitudes y medición de cobertura; refinamiento candidato para iteración 5 | Responsable de ingesta, coordinado con consulta |
| Escalón brusco y sobrecarga | Panel lento o novedades demoradas | Escalado, prioridades y contrapresión; no afirmar capacidad garantizada por un umbral del 60 % | Responsable de consulta y equipo |
| Caída de zona y una sola copia | Ventana de durabilidad reducida | Política explícita de ADR-0042, reconstrucción y alarmas | Equipo de despliegue |
| Auditoría indisponible | Se rechaza lectura compartida | Fallo cerrado, registro alternativo y alarma; riesgo residual documentado | Ambos, seguridad |
| Error de identidad o proyección | Acceso ajeno o exposición de contenido | Perfil JWT, principal regional, permisos y SharedBooking sin details | Ambos, seguridad |
| Respuesta compartida entre regiones | Transferencia aunque no se persista réplica | mTLS, no-store y criterio de CON-3 todavía por validar | Ambos |
| Rotación de claves y reprocesamiento | Hechos tardíos pendientes o análisis incompleto | Período committedAt, deduplicación previa y resolución durable | Ambos, analítica |
| Reportes faltantes o relojes distintos | Percentiles sesgados | Cobertura, incertidumbre y reintentos; desconocido no cuenta como éxito | Ambos, observabilidad |

## Pendientes que el cierre no borra

* Las cifras de percentiles, pico 5x y otros valores identificados como supuestos requieren validación.
* QA-1 a escala, QA-3 sin caché, QA-5 durante arranque y QA-10 internacional conservan su estado parcial.
* CON-3 no tiene normativa concreta validada; no se afirma cumplimiento legal ni anonimato demostrado.
* El prototipo y sus pruebas todavía no existen; el plan está en prototype/README.md y sus documentos enlazados.
* No se registra una sesión de Risk Storming del equipo si no ocurrió. Si la realizan, agregar participantes,
  fecha, escenarios revisados y acuerdos reales.
* Confirmar alcance por fecha con lo indicado por la cátedra y seleccionar la opción avanzada de la segunda entrega.

## Publicación del cierre

El cierre es visible para el docente en `main` y en la Wiki de GitHub, que se actualiza copiando `wiki/Home.md` y
`wiki/_Sidebar.md`. Antes de enviar el enlace, abrir desde la Wiki publicada la portada, las cuatro iteraciones y este
documento, y comprobar que el menú lateral se muestra.
