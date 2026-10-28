# Validación futura del prototipo de ingesta

**Estado:** plan ejecutable por escenarios, sin resultados de ejecución. El diseño del paso 7 ya fue analizado.
[Políticas y valores](../specs/ingestion-operations.md), [autorización](../specs/ingestion-authorization.md).

| ID | Preparación / acción | Resultado exigido y evidencia |
|---|---|---|
| V01 | Correo con localizador y fechas suficientes, sin sourceVersion | Reserva nueva visible; marca externa y timestamps de cada etapa; sin quedar pendiente solo por falta de versión |
| V02 | Dos respuestas de proveedores con campos/estados diferentes | Payload normalizado válido y reserva coherente; contrato y referencias correctos |
| V03 | Reentregar el mismo evento y reconsultar mismo correo | Una reserva/efecto, IDs procesados durables y ACK tras commit |
| V04 | Cancelación antes del alta y confirmación anterior atrasada | Pendiente conciliada sin reactivar una cancelación con información vieja |
| V05 | Matar ingesta antes/después de guardar cursor/outbox | No salta novedades; avanza solo con resultados durables |
| V06 | Cortar conexión después de confirm del broker y antes de marcar enviada | Republicación con igual eventId sin duplicar efecto |
| V07 | Quitar binding deliberadamente y publicar mandatory | Retorno detectado; outbox no enviada; alerta; al restaurar ruta se entrega |
| V08 | Caída de núcleo antes/después de commit y antes de ACK | Transacción/control/outbox consistentes; reentrega segura; cambios manuales también producen evento confirmado |
| V09 | Desvincular mientras se inicia consulta o renovación | Barrera coordinada; no nuevo inicio tras confirmación; estados pendientes honestos si falla servicio |
| V10 | Agencia recibe solicitud pero se pierde respuesta | No duplicar ciegamente; consulta de estado/resolución y seguimiento por requestId |
| V11 | Formato inválido, fallo de base y cuota Retry-After | Clasificación distinta; aparcado durable para datos, pausa para infraestructura y respeto de espera externa |
| V12 | Nodo local reinicia con datos persistentes | Conserva trabajo; no equivale a prueba de fallo de zona |
| V13 | Perfil adicional con tres miembros, perder uno | Se conserva mayoría y se mide elección/consumo; no afirmar independencia física con una sola máquina |
| V14 | 50 eventos/s 10 min y 250/s 15 min por región simulada, promedio4KiB/máximo16KiB | Medir capacidad, edad cola/outbox, p99 y total≤300s; paralelamente verificar web con escenario de 3 |
| V16 | Perder aviso, vencer suscripción y usar cursor inválido | Recuperación trazable; medir consultas y renovaciones; registrar incumplimiento si supera presupuesto, incluidas cuentas inactivas |
| V17 | Agregar trenes contra puerto de proveedores | Contrato válido, regresión de medios existentes sin editar su código y registro de esfuerzo frente a 10 días-persona |
| V15 | Forzar presión de espacio y fallo de destino de errores | No drop-head ni borrado silencioso; productor conserva trabajo y no avanza indebidamente |

Guardar por corrida versión/digest, configuración, máquina, número de consumidores, cuotas simuladas, datos
sintéticos, timestamps correlacionados y resultado observado. No sustituir occurredAt por detectedAt si se desconoce
el origen. Si falla un umbral, registrar causa y reabrir el riesgo; no ajustar números solo para que pase.
No usar correos ni tokens reales. Las pruebas de contrato/formato no demuestran seguridad, latencia o recuperación.
