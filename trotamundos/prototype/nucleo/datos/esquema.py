"""Tablas de cada nodo de la base operativa y del registro de auditoría.

Las tablas normalizadas son la fuente de verdad; `panel_por_usuario` es la copia para leer (ADR-0040). Cada nodo
guarda las particiones que le tocan (ADR-0042). El registro de auditoría es una base aparte (ADR-0061).
"""
from comun.infraestructura.outbox import DDL_OUTBOX

DDL_NODO = [
    """CREATE TABLE IF NOT EXISTS usuarios (
        user_id TEXT PRIMARY KEY, home_region TEXT NOT NULL, idioma TEXT, pais TEXT, creado TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS vinculaciones (
        connection_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, home_region TEXT NOT NULL, provider_id TEXT NOT NULL,
        estado TEXT NOT NULL, revision INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS viajes (
        trip_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, particion INTEGER NOT NULL, nombre TEXT NOT NULL,
        estado TEXT NOT NULL, fecha_inicio TEXT, fecha_fin TEXT, archivado_en TEXT, reactivado_hasta TEXT,
        creado TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS viajes_usuario ON viajes (user_id, estado)",
    "CREATE INDEX IF NOT EXISTS viajes_particion ON viajes (particion, estado)",
    """CREATE TABLE IF NOT EXISTS reservas (
        booking_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, trip_id TEXT, tipo TEXT NOT NULL, estado TEXT NOT NULL,
        origen TEXT NOT NULL, proveedor TEXT, referencia_proveedor TEXT, connection_id TEXT, provider_id TEXT,
        external_reservation_id TEXT, source_version TEXT, inicio TEXT, fin TEXT, zona TEXT, zona_llegada TEXT,
        lugar TEXT, lugar_llegada TEXT, nombre_visible TEXT, precio_monto REAL, precio_moneda TEXT, detalles TEXT,
        notas TEXT, campos_editados TEXT NOT NULL, version INTEGER NOT NULL, creado TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS reservas_usuario ON reservas (user_id, trip_id)",
    "CREATE INDEX IF NOT EXISTS reservas_externas ON reservas (connection_id, provider_id, external_reservation_id)",
    """CREATE TABLE IF NOT EXISTS marcas_borrado (
        connection_id TEXT NOT NULL, provider_id TEXT NOT NULL, external_reservation_id TEXT NOT NULL,
        user_id TEXT NOT NULL, trip_id TEXT, creado TEXT NOT NULL,
        PRIMARY KEY (connection_id, provider_id, external_reservation_id))""",
    """CREATE TABLE IF NOT EXISTS avisos (
        notice_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, tipo TEXT NOT NULL, booking_id TEXT, campo TEXT,
        creado TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS panel_por_usuario (
        user_id TEXT PRIMARY KEY, version INTEGER NOT NULL, documento TEXT NOT NULL, actualizado TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS novedades_procesadas (
        event_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, resultado TEXT NOT NULL, procesado TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS casos_pendientes (
        caso_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, event_id TEXT NOT NULL, motivo TEXT NOT NULL,
        resumen TEXT NOT NULL, reservation_key TEXT, source_version TEXT, resuelto TEXT, creado TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS idempotencia (
        user_id TEXT NOT NULL, clave TEXT NOT NULL, operacion TEXT NOT NULL, estado INTEGER NOT NULL,
        respuesta TEXT NOT NULL, creado TEXT NOT NULL, PRIMARY KEY (user_id, clave))""",
    """CREATE TABLE IF NOT EXISTS comparticiones (
        share_id TEXT PRIMARY KEY, trip_id TEXT NOT NULL, owner_user_id TEXT NOT NULL, email TEXT,
        email_hmac TEXT NOT NULL, secreto_hash TEXT NOT NULL, estado TEXT NOT NULL, creado TEXT NOT NULL,
        vence TEXT NOT NULL, aceptada_region TEXT, aceptada_usuario TEXT, aceptada_en TEXT)""",
    "CREATE INDEX IF NOT EXISTS comparticiones_viaje ON comparticiones (trip_id)",
    """CREATE TABLE IF NOT EXISTS referencias_compartidas (
        user_id TEXT NOT NULL, trip_id TEXT NOT NULL, aceptada_en TEXT NOT NULL, PRIMARY KEY (user_id, trip_id))""",
    """CREATE TABLE IF NOT EXISTS telemetria_panel (
        principal TEXT NOT NULL, panel_version INTEGER NOT NULL, mostrado TEXT NOT NULL, correlation_ids TEXT,
        recibido TEXT NOT NULL, PRIMARY KEY (principal, panel_version))""",
    *DDL_OUTBOX,
]

DDL_AUDITORIA = [
    """CREATE TABLE IF NOT EXISTS auditoria (
        record_id TEXT PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL, result TEXT NOT NULL, reason TEXT,
        actor_user_id TEXT, actor_region TEXT, actor_issuer TEXT, method TEXT, route TEXT, booking_id TEXT,
        entry_region TEXT NOT NULL, trip_id TEXT, share_id TEXT, correlation_id TEXT)""",
]
