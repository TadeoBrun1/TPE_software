# Medición de frescura y disponibilidad

**Estado:** propuesta de iteración 4, ADR-0067. Parámetros iniciales son hipótesis operativas; no son mediciones.

## QA-4: tiempo de indisponibilidad

Mantener dos indicadores separados: proporción de solicitudes exitosas, útil para operación, y duración de
indisponibilidad no planificada, necesaria para el límite de 300 s por mes. No convertir el primero directamente
en minutos ni contar 401 o 404 legítimos como fallas de servicio.

Sondas sintéticas independientes de los procesos vigilados consultan cada 5 s el recorrido entrada global,
puerta de entrada, autenticación y lectura del núcleo. Cada región y partición dispone de una cuenta sintética
sin datos personales reales; incluir pruebas de disponibilidad de auditoría para el recorrido compartido.
El monitor de base sigue midiendo detección y conmutación de ADR-0042; no sustituye al sondeo externo.

Registrar inicio y fin del fallo con precisión de segundos. Como límite conservador, un intervalo comienza en
la última sonda exitosa previa al primer fallo y termina al recuperar respuestas válidas; el primer fallo ya se
registra aunque la alerta espere tres fallos consecutivos. Declarar la incertidumbre del intervalo de sondeo.
Consolidar intervalos superpuestos sin sumarlos dos veces. Informar por región, partición y recorrido; una caída
parcial no desaparece al promediar con regiones sanas. Comparar cada ámbito acordado con los 300 s del mes y
mantener aparte la indisponibilidad planificada. Si la sonda también falla, marcar el intervalo como desconocido,
no como disponible. La falta de tráfico de usuarios no detiene las sondas.

## QA-1: población, cobertura y cola de latencia

Definir la cohorte de actualizaciones a medir, registrar expectedAt, occurredAt cuando sea confiable, detectedAt,
commit, versión visible y recepción del reporte. La cadena técnica nace en ingesta: no hace observable una fecha
externa desconocida. Informar por separado latencia desde detección y desde generación externa.

El notificador conserva para la cohorte la relación de novedades con versiones enviadas a clientes activos.
Si el cliente recibe varias versiones juntas, solo declara una novedad visible cuando la versión mostrada
contiene ese cambio. Una reconexión o un GET sin correlationIds debe enlazarse por principal y versión cuando
exista esa relación; si no puede reconstruirse, la muestra queda sin cierre, no con latencia cero.

El cliente guarda reportes técnicos pendientes en una cola local limitada (hipótesis: hasta 1.000 reportes,
1 MiB y 24 h). No guarda cuerpos de reserva ni tokens. Solo retira un reporte tras 202; reintenta ante pérdida de
respuesta, 429 y 503 con espera creciente y variación, respetando Retry-After. Una caída o límite puede perder
reportes: contabilizar vencimientos, pérdidas y cobertura. 202 significa recepción durable regional; ante
sobrecarga se puede rechazar con 503, pero no confirmar y descartar silenciosamente.

Servidor deduplica por principal canónico y panelVersion, conservando el primer cierre válido de la cohorte;
reportes repetidos no multiplican observaciones. Registra además receivedAt del servidor. El reloj del dispositivo
no se supone confiable: validar shownAt, documentar desfase y usar un intervalo de incertidumbre o marcar el
reporte como no comparable. Un dato horario imposible no cierra una muestra exitosa.

Publicar contadores de esperadas, cerradas, conocidas >300 s y desconocidas o perdidas, junto con cobertura por
región, proveedor y carga. No estimar cumplimiento del 99 % usando solo los reportes que sobrevivieron a una
sobrecarga. Las muestras desconocidas no se imputan como éxitos; si impiden concluir el resultado, QA-1 queda
indeterminado para esa cohorte. Pueden presentarse límites conservadores con las desconocidas como incumplimientos,
distinguiéndolos de fallos observados. El riesgo de detección a escala de iteración 2 no se elimina por medir mejor.

## Muestreo de trazas

Si se pretende conservar todas las trazas lentas o con error y 10 % de las normales, decidir después de observar
la traza (tail sampling) y dimensionar memoria y ventana de espera. Un muestreo previo que ya descartó spans no
puede recuperarlos luego. Contar trazas incompletas; las métricas de cobertura y disponibilidad no se muestrean.

## Pruebas futuras

* Caída de lectura sin tráfico real: las sondas registran el intervalo de indisponibilidad.
* Fallos solapados de componentes: la duración del recorrido no se suma dos veces.
* Rechazos legítimos de autenticación: no producen caída artificial del servicio.
* Sobrecarga de telemetría: 503, reintento, deduplicación y cobertura de muestras faltantes.
* Reloj de cliente adelantado o atrasado y ocurrido externo ausente: resultado incierto, no éxito inventado.
