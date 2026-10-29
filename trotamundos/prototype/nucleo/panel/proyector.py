"""Proyector del panel (ADR-0040): único escritor de `panel_por_usuario`.

Los demás módulos le piden la actualización dentro de su transacción. Cada transacción que cambia algo de un
usuario toma primero el bloqueo de la fila del panel de ese usuario (`bloquear`), y la versión pasa a anterior + 1.
"""
from __future__ import annotations

import json
from datetime import timedelta

from comun.infraestructura.db import Transaccion
from comun.infraestructura.reloj import Reloj, iso
from nucleo.mensajeria import eventos
from nucleo.reservas.modelo import viaje_a_api, reserva_a_api

VIAJES_COMPLETOS = 15   # el resto va en resumen (ADR-0040)
DIAS_AVISOS = 7         # los avisos quedan 7 días en el panel (ADR-0044, suposición)

PRIORIDAD_MOTIVOS = ["provider_overrode_user_edit", "booking_cancelled", "schedule_changed", "trip_deleted",
                     "trip_reactivated", "trip_archived", "trip_created", "booking_removed", "booking_added",
                     "booking_updated"]
RELEVANCIA_IMPORTANTE = {"provider_overrode_user_edit", "booking_cancelled", "schedule_changed"}


def bloquear(tx: Transaccion, user_id: str, ahora: str) -> int:
    """Bloquea la fila del panel del usuario (la crea si no existe) y devuelve su versión actual."""
    tx.ejecutar("INSERT INTO panel_por_usuario (user_id, version, documento, actualizado) VALUES (?, 0, ?, ?) "
                "ON CONFLICT (user_id) DO NOTHING",
                (user_id, json.dumps({"panelVersion": 0, "trips": [], "unassignedBookings": [], "notices": []}),
                 ahora))
    return tx.bloqueo_fila("SELECT version FROM panel_por_usuario WHERE user_id = ?", (user_id,))["version"]


def construir(tx: Transaccion, user_id: str, version: int, reloj: Reloj) -> dict:
    """Arma el documento desde las tablas normalizadas (fuente de verdad); sirve también para reconstruirlo."""
    viajes = tx.todos("SELECT * FROM viajes WHERE user_id = ? AND estado = 'activo' "
                      "ORDER BY fecha_inicio, trip_id", (user_id,))
    reservas = tx.todos("SELECT * FROM reservas WHERE user_id = ? ORDER BY inicio, booking_id", (user_id,))
    por_viaje: dict[str, list[dict]] = {}
    sin_asignar = []
    for reserva in reservas:
        if reserva["trip_id"] is None:
            sin_asignar.append(reserva)
        else:
            por_viaje.setdefault(reserva["trip_id"], []).append(reserva)
    desde = iso(reloj.ahora() - timedelta(days=DIAS_AVISOS))
    avisos = tx.todos("SELECT * FROM avisos WHERE user_id = ? AND creado >= ? ORDER BY creado", (user_id, desde))
    return {
        "panelVersion": version,
        "trips": [viaje_a_api(v, por_viaje.get(v["trip_id"], []), resumen=i >= VIAJES_COMPLETOS)
                  for i, v in enumerate(viajes)],
        "unassignedBookings": [reserva_a_api(r) for r in sin_asignar],
        "notices": [{k: v for k, v in {"id": a["notice_id"], "type": a["tipo"], "bookingId": a["booking_id"],
                                        "field": a["campo"], "createdAt": a["creado"]}.items() if v is not None}
                    for a in avisos],
    }


def actualizar(tx: Transaccion, region: str, user_id: str, motivos: list[str], correlation_ids: list[str],
               reloj: Reloj) -> int:
    """Escribe el panel con versión anterior + 1 y deja `panel.changed.v1` en la outbox, en la misma transacción."""
    ahora = iso(reloj.ahora())
    anterior = bloquear(tx, user_id, ahora)
    version = anterior + 1
    documento = construir(tx, user_id, version, reloj)
    tx.ejecutar("UPDATE panel_por_usuario SET version = ?, documento = ?, actualizado = ? WHERE user_id = ?",
                (version, json.dumps(documento), ahora, user_id))
    motivo = min(motivos, key=PRIORIDAD_MOTIVOS.index) if motivos else "booking_updated"
    relevancia = "important" if any(m in RELEVANCIA_IMPORTANTE for m in motivos) else "normal"
    eventos.panel_cambiado(tx, region, user_id, version, motivo, relevancia, correlation_ids, ahora)
    return version


def leer(tx: Transaccion, user_id: str) -> dict | None:
    """Lectura por clave (QA-2): una sola fila, sin uniones."""
    fila = tx.uno("SELECT documento FROM panel_por_usuario WHERE user_id = ?", (user_id,))
    return json.loads(fila["documento"]) if fila else None

