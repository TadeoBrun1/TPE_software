# Escenarios de atributos de calidad (SEI, 6 partes)

**Qué es:** QAs del enunciado refinados como escenarios de 6 partes.
**Mantiene:** ambos. **Estado:** BORRADOR. Auditar cada escenario con `/test-qas` antes de usarlo como driver.

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
| Artefacto | Aplicación móvil y su API de consulta |
| Ambiente | Operación normal, conexión móvil estándar |
| Respuesta | La aplicación muestra el primer contenido útil del itinerario |
| Medida de respuesta | El primer despliegue de contenido ocurre en menos de 1,4 s en el 95 % de las aperturas |

## QA-4 Disponibilidad

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Falla de infraestructura (nodo, zona o región) |
| Estímulo | Una instancia o zona del servicio de consulta deja de responder |
| Artefacto | Servicio de consulta de itinerarios y su almacenamiento |
| Ambiente | Operación normal, con tráfico global |
| Respuesta | El sistema detecta la falla, redirige el tráfico a réplicas sanas y sigue atendiendo |
| Medida de respuesta | Máximo 5 minutos de inactividad no planificada por mes (aproximadamente 99,988 %) |

## QA-5 Escalabilidad

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Viajeros afectados por una disrupción masiva (por ejemplo, clima) |
| Estímulo | El tráfico se multiplica respecto del promedio |
| Artefacto | Plataforma completa: consulta e ingesta |
| Ambiente | Operación con pico de carga |
| Respuesta | El sistema agrega capacidad automáticamente y sigue procesando consultas y actualizaciones |
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
| Respuesta | El equipo incorpora el proveedor sin modificar el código de los medios existentes |
| Medida de respuesta | Se completa en 10 días-persona o menos y la suite de pruebas existente sigue en verde |

## QA-10 Usabilidad e internacionalización

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Viajero ubicado en otro país |
| Estímulo | Usa la aplicación desde una región distinta con su idioma y formato locales |
| Artefacto | Aplicación y backend multirregión |
| Ambiente | Operación normal |
| Respuesta | El sistema muestra el contenido en el idioma y formato del usuario y lo sirve desde la región más cercana |
| Medida de respuesta | Se agrega un nuevo idioma sin cambios de código y se mantienen las medidas de QA-2 y QA-3 |

## Suposiciones a validar

| Valor asumido | Escenario | Criterio |
|---|---|---|
| Percentil 99 de las actualizaciones | QA-1 | El enunciado da 5 minutos pero no el porcentaje de cumplimiento |
| Percentil 95 | QA-2, QA-3 | Es el estándar habitual para SLAs de latencia |
| 99,988 % | QA-4 | Cálculo directo: 5 minutos sobre 43.200 minutos de un mes de 30 días |
| Pico de 5 veces el promedio | QA-5 | Estimación por analogía con plataformas de viajes en disrupciones; el enunciado solo dice "dramáticos" |
| 99,9 % sin pérdida ni duplicación | QA-6 | Analogía con SLAs de integraciones entre sistemas |
| 100 % de rechazos | QA-7, QA-8 | Control de seguridad: el objetivo razonable es sin excepciones |
| 10 días-persona | QA-9 | Estimación por analogía con una integración nueva de complejidad media |

## Pendientes

- [ ] Auditar cada escenario con `/test-qas`.
- [ ] Decidir si QA-3 se mantiene aparte de QA-2 o se fusionan.
- [ ] Agregar un escenario de privacidad (borrado de datos del usuario) si el equipo lo considera driver.
- [ ] Revisar si la opción avanzada elegida (A o B) agrega QAs propios.
