"""Base del proceso de recomendación de una región (ADR-0081): perfiles, sugerencias, feedback, búsquedas
pendientes, versiones del modelo y outbox. No guarda códigos de reserva, nombres, notas ni textos del viajero."""
from __future__ import annotations

from comun.infraestructura.outbox import DDL_OUTBOX

DDL_RECOMENDACION = [
    # Recepción idempotente de booking.facts.v1 (Idempotent Receiver).
    """CREATE TABLE IF NOT EXISTS hechos_recibidos (
        event_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, recibido TEXT NOT NULL)""",
    # Perfil resumido: activación (opt-out), preferencias explícitas, métricas resumidas y ajuste del modelo.
    """CREATE TABLE IF NOT EXISTS perfiles (
        user_id TEXT PRIMARY KEY, home_region TEXT NOT NULL, activada INTEGER NOT NULL, preferencias TEXT NOT NULL,
        metricas TEXT NOT NULL, ajuste TEXT NOT NULL, actualizado TEXT NOT NULL)""",
    # Búsqueda pendiente por cada reserva cancelada; se agrupan por clave al buscar (ADR-0082).
    """CREATE TABLE IF NOT EXISTS busquedas (
        busqueda_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, home_region TEXT NOT NULL, trip_id TEXT NOT NULL,
        cancelled_booking_id TEXT NOT NULL, clave TEXT NOT NULL, consulta TEXT NOT NULL, cancelada TEXT NOT NULL,
        correlation_id TEXT, estado TEXT NOT NULL, intentos INTEGER NOT NULL DEFAULT 0, reintentar_desde TEXT,
        parcial INTEGER NOT NULL DEFAULT 0, creada TEXT NOT NULL, terminada TEXT)""",
    "CREATE INDEX IF NOT EXISTS busquedas_estado ON busquedas (estado, reintentar_desde)",
    # Sugerencias: las 3 mostradas (available) y el resto de los candidatos ordenados (candidate, uso interno).
    """CREATE TABLE IF NOT EXISTS sugerencias (
        suggestion_id TEXT PRIMARY KEY, busqueda_id TEXT NOT NULL, user_id TEXT NOT NULL, trip_id TEXT NOT NULL,
        cancelled_booking_id TEXT NOT NULL, posicion INTEGER NOT NULL, oferta TEXT NOT NULL,
        caracteristicas TEXT NOT NULL, version_modelo TEXT NOT NULL, exploracion INTEGER NOT NULL,
        motivos TEXT NOT NULL, estado TEXT NOT NULL, mostrada INTEGER NOT NULL DEFAULT 0, creada TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS sugerencias_viaje ON sugerencias (user_id, trip_id)",
    # Feedback: la señal del human-in-the-loop (ADR-0083).
    """CREATE TABLE IF NOT EXISTS feedback (
        feedback_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, suggestion_id TEXT NOT NULL, accion TEXT NOT NULL,
        motivo TEXT, caracteristicas TEXT NOT NULL, version_modelo TEXT NOT NULL, posicion INTEGER NOT NULL,
        creado TEXT NOT NULL)""",
    # Registro de versiones del modelo regional (canario, activa, retirada).
    """CREATE TABLE IF NOT EXISTS versiones_modelo (
        version_id TEXT PRIMARY KEY, pesos TEXT NOT NULL, estado TEXT NOT NULL, ejemplos INTEGER NOT NULL,
        evaluacion TEXT NOT NULL, creada TEXT NOT NULL, cambio_estado TEXT NOT NULL)""",
    *DDL_OUTBOX,
]
