# Escenarios de atributos de calidad (SEI, 6 partes)

**Qué es:** los atributos de calidad del enunciado refinados como escenarios de 6 partes.
**Mantiene:** ambos. **Estado:** COMPLETADO (revisado con la skill `/test-qas`). Cambios solo por PR de ambos: son
drivers inmutables durante ADD.

Regla de este documento: los valores que vienen **del enunciado** se usan tal cual. Los que se inventaron para poder
medir están marcados como **Suposición** y se explican abajo. Una suposición es un punto de partida (straw man).

Datos del enunciado: 2 millones de usuarios activos por semana, 15 millones de cuentas, picos domingo-lunes y
jueves-viernes y ante disrupciones; actualización visible en 5 minutos; respuesta web de 800 ms; primer contenido
en móvil en menos de 1,4 s; máximo 5 minutos por mes de inactividad no planificada.

## QA-1 Performance: frescura de las actualizaciones

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Sistema de una aerolínea, hotel o rentadora, o proveedor de correo |
| Estímulo | Se genera una actualización o llega un correo de reserva de un viajero |
| Artefacto | Flujo de ingesta y actualización de itinerarios |
| Ambiente | Operación normal |
| Respuesta | El sistema detecta el cambio, lo normaliza y actualiza el itinerario del viajero |
| Medida de respuesta | El 99 % de las actualizaciones se ve en la aplicación dentro de los 5 minutos de generada |

## QA-2 Performance: latencia web

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Viajero desde un navegador |
| Estímulo | Solicita su panel de viajes |
| Artefacto | Servicio de consulta de itinerarios |
| Ambiente | Operación normal, con carga habitual de usuarios activos |
| Respuesta | El sistema devuelve los viajes con sus reservas agrupadas |
| Medida de respuesta | El 95 % de las solicitudes se responde en 800 ms o menos |

## QA-3 Performance: primer despliegue en móvil

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Viajero desde la aplicación móvil |
| Estímulo | Abre la aplicación para ver su próximo viaje |
| Artefacto | Cliente móvil |
| Ambiente | Operación normal, con red 4G y sesión ya iniciada |
| Respuesta | La aplicación muestra el primer contenido útil del itinerario |
| Medida de respuesta | El primer despliegue de contenido ocurre en menos de 1,4 s en el 95 % de las aperturas |

## QA-4 Disponibilidad

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Infraestructura de ejecución (instancia o zona de falla) |
| Estímulo | Una instancia o zona del servicio de consulta deja de responder |
| Artefacto | Servicio de consulta de itinerarios y su almacenamiento |
| Ambiente | Operación normal, con tráfico global |
| Respuesta | El sistema detecta la falla, redirige el tráfico a réplicas sanas y sigue atendiendo |
| Medida de respuesta | La falla se detecta en 30 s o menos y el tráfico se redirige a réplicas sanas en 60 s o menos, sin superar 5 minutos de inactividad no planificada por mes |

## QA-5 Escalabilidad

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Viajeros usuarios de la aplicación |
| Estímulo | Consultan sus itinerarios y se reciben actualizaciones de reservas |
| Artefacto | Servicios de consulta e ingesta de itinerarios |
| Ambiente | Operación con pico de carga |
| Respuesta | El sistema procesa las consultas y actualizaciones, y agrega capacidad automáticamente a medida que crece la carga |
| Medida de respuesta | Soporta 2 millones de usuarios activos semanales sobre 15 millones de cuentas y un pico de **5 veces** el promedio, cumpliendo QA-1 y QA-2 |

## QA-6 Interoperabilidad con terceros

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Sistema de una aerolínea u hotel |
| Estímulo | Informa una cancelación o cambio de una reserva a través de su API estándar |
| Artefacto | Módulo de integración con terceros |
| Ambiente | Operación normal |
| Respuesta | El sistema recibe el mensaje, lo traduce al modelo interno y actualiza la reserva |
| Medida de respuesta | El 99,9 % de los mensajes válidos se procesa sin pérdida ni duplicación |

## QA-7 Seguridad: itinerarios compartidos

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Persona que no fue designada por el viajero |
| Estímulo | Intenta ver un itinerario compartido con otra persona |
| Artefacto | Módulo de autorización de itinerarios |
| Ambiente | Operación normal |
| Respuesta | El sistema rechaza el acceso y registra el intento |
| Medida de respuesta | El 100 % de los accesos de personas no designadas se rechaza y queda registrado |

## QA-8 Seguridad: acceso a correos

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Procesador de correo de Trotamundos |
| Estímulo | Sondea el buzón de un viajero |
| Artefacto | Módulo de acceso a correos |
| Ambiente | Operación normal |
| Respuesta | El sistema accede con la autorización otorgada por el usuario y procesa solo mensajes de remitentes permitidos y relacionados con viajes |
| Medida de respuesta | El 100 % de los accesos usa credenciales autorizadas y 0 mensajes ajenos a viajes se almacenan |

## QA-9 Evolucionabilidad

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Equipo de desarrollo |
| Estímulo | Debe agregar un nuevo medio de transporte (por ejemplo, trenes) |
| Artefacto | Modelo de reservas y módulo de integraciones |
| Ambiente | Etapa de desarrollo, sistema en producción |
| Respuesta | El equipo agrega el nuevo tipo de reserva y su conector, y lo despliega con el sistema en producción |
| Medida de respuesta | Se completa en 10 días-persona o menos, sin modificar el código de los medios existentes |

## QA-10 Usabilidad e internacionalización

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Viajero usuario de la aplicación |
| Estímulo | Usa la aplicación con un idioma y formato regional distintos a los del idioma base, o desde otro país durante un viaje |
| Artefacto | Aplicación y backend multirregión |
| Ambiente | Operación normal |
| Respuesta | El sistema muestra el contenido en el idioma y formato del usuario y atiende la solicitud desde la región de origen del usuario |
| Medida de respuesta | El 100 % de los textos y formatos de los idiomas soportados se muestra según la configuración del usuario, y se siguen cumpliendo QA-2 (800 ms) y QA-3 (1,4 s) aunque el usuario esté fuera de su región |

## Suposiciones a validar

| Valor asumido | Escenario | Criterio |
|---|---|---|
| Percentil 99 de las actualizaciones | QA-1 | El enunciado da 5 minutos pero no el porcentaje de cumplimiento |
| Percentil 95 | QA-2, QA-3 | Es el estándar habitual para SLAs de latencia |
| Pico de 5 veces el promedio | QA-5 | Estimación por analogía con plataformas de viajes en disrupciones; el enunciado solo dice "dramáticos" |
| 99,9 % sin pérdida ni duplicación | QA-6 | Analogía con SLAs de integraciones entre sistemas |
| 10 días-persona | QA-9 | Estimación por analogía con una integración nueva de complejidad media |
| Red 4G y sesión ya iniciada | QA-3 | El enunciado no fija las condiciones de red; 4G es el caso típico de un viajero |
| Detección en 30 s y redirección en 60 s | QA-4 | El presupuesto de 5 min/mes solo admite unas pocas fallas por mes si cada una se resuelve en alrededor de un minuto |


## Escenarios para la 2da entrega (opción A, RF-09)

Generados con `/generador-qas` a partir del texto de la opción A y de las decisiones del equipo, y auditados con
`/test-qas` (QA-12, QA-14 y QA-15 se corrigieron en la auditoría: la respuesta de QA-12 describía la táctica, la
medida de QA-14 mezclaba la residencia de datos y QA-15 tenía valores vagos).

### QA-11 Performance: oportunidad de las sugerencias

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Sistema de una aerolínea u hotel |
| Estímulo | Informa la cancelación de una reserva de un viajero que tiene la recomendación activada |
| Artefacto | Módulo de recomendación |
| Ambiente | Operación normal |
| Respuesta | El sistema busca alternativas del mismo tipo, las ordena según el perfil del viajero, las deja disponibles en la app y le envía un aviso push |
| Medida de respuesta | El 95 % de las sugerencias está disponible y avisada dentro de los 2 minutos de aplicada la cancelación en el panel |

### QA-12 Escalabilidad: disrupción masiva

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Aerolíneas afectadas por una disrupción climática |
| Estímulo | Cancelan 50 vuelos con 15.000 viajeros afectados en 10 minutos |
| Artefacto | Módulo de recomendación y búsqueda de ofertas |
| Ambiente | Operación con pico de carga (5 veces el promedio) |
| Respuesta | El sistema busca alternativas para todos los viajeros afectados, las ordena y les avisa |
| Medida de respuesta | QA-11 se cumple para el 95 % de los afectados, el sistema respeta el 100 % de los límites de consulta de cada proveedor y el panel sigue cumpliendo QA-2 |

### QA-13 Usabilidad: adaptación al usuario (human-in-the-loop)

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Viajero |
| Estímulo | Rechaza una sugerencia o ajusta un parámetro (precio máximo, máximo de escalas, franja horaria) |
| Artefacto | Módulo de recomendación |
| Ambiente | Operación normal |
| Respuesta | El sistema reordena las sugerencias de ese viaje según el ajuste, guarda el feedback y lo incorpora al modelo |
| Medida de respuesta | Las sugerencias reordenadas se muestran en 2 s o menos, el 100 % respeta los límites explícitos del usuario y el feedback entra en el modelo regional dentro de las 24 h |

### QA-14 Seguridad y privacidad: control del perfil

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Viajero |
| Estímulo | Desactiva la recomendación y pide borrar su perfil |
| Artefacto | Almacén de perfiles y feedback del módulo de recomendación |
| Ambiente | Operación normal |
| Respuesta | El sistema deja de generar sugerencias para ese viajero, borra su perfil y su feedback identificable y le confirma el borrado |
| Medida de respuesta | 0 sugerencias nuevas desde la desactivación y el 100 % del perfil y del feedback borrado en 24 h o menos |

### QA-15 Modificabilidad del modelo

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Equipo de desarrollo |
| Estímulo | Reemplaza el modelo de ranking por una versión nueva |
| Artefacto | Módulo de recomendación |
| Ambiente | Sistema en producción |
| Respuesta | El sistema despliega la versión nueva para el 5 % de los usuarios, compara su tasa de aceptación con la de la versión actual y vuelve atrás si cae más de un 10 % relativo |
| Medida de respuesta | El cambio no modifica código del núcleo, la ingesta ni el notificador, y la vuelta atrás a la versión anterior tarda 5 minutos o menos |

### QA-16 Disponibilidad: falla de la recomendación

| Parte | Contenido |
|---|---|
| Fuente del estímulo | API de búsqueda de un proveedor, o el propio módulo de recomendación |
| Estímulo | Deja de responder durante una cancelación |
| Artefacto | Módulo de recomendación |
| Ambiente | Operación normal |
| Respuesta | El sistema muestra la cancelación y su aviso sin sugerencias, guarda la búsqueda pendiente y la reintenta al volver el servicio |
| Medida de respuesta | El panel sigue cumpliendo QA-2 y QA-4, y las sugerencias pendientes se generan dentro de los 10 minutos de recuperado el servicio |

### Suposiciones de la 2da entrega

| Valor asumido | Escenario | Criterio |
|---|---|---|
| 2 minutos desde la cancelación en el panel | QA-11 | Analogía con alertas de reprogramación de aerolíneas; se cuenta desde el panel para no mezclarlo con el presupuesto de QA-1 |
| 50 vuelos y 15.000 viajeros en 10 minutos | QA-12 | Analogía con un cierre de aeropuerto por tormenta (vuelos de unos 300 pasajeros) |
| 2 s para reordenar | QA-13 | Interacción en la app, con la misma referencia que QA-2 |
| 24 h para incorporar el feedback | QA-13 | Reentrenamiento diario por lotes (CON-5) |
| 24 h para borrar el perfil | QA-14 | Plazo operativo; la normativa concreta no está validada (CON-3) |
| 5 % de usuarios, 10 % relativo, 5 minutos | QA-15 | Práctica habitual de despliegue canario con vuelta atrás automatizada |
| 10 minutos tras la recuperación | QA-16 | Reintento con espera creciente, como la ingesta |
