"""Asignación automática de reservas a viajes por fechas (ADR-0048), dentro de la transacción del cambio."""
from __future__ import annotations

from datetime import date, timedelta

from comun.infraestructura.db import Transaccion
from nucleo.datos.ruteo import RuteoParticiones
from nucleo.panel.unidad import UnidadDeCambio

MARGEN = timedelta(days=2)


def _dia(texto: str) -> date:
    return date.fromisoformat(texto[:10])


def candidato(tx: Transaccion, user_id: str, inicio: date, fin: date) -> str | None:
    """Viaje activo que cubre las fechas, o a menos de 2 días de su inicio o fin; el más cercano en fechas."""
    mejor: tuple[int, str, str] | None = None
    for viaje in tx.todos("SELECT trip_id, fecha_inicio, fecha_fin FROM viajes "
                          "WHERE user_id = ? AND estado = 'activo' AND fecha_inicio IS NOT NULL", (user_id,)):
        v_inicio, v_fin = _dia(viaje["fecha_inicio"]), _dia(viaje["fecha_fin"])
        if inicio <= v_fin + MARGEN and fin >= v_inicio - MARGEN:
            distancia = max(0, (v_inicio - fin).days, (inicio - v_fin).days)
            clave = (distancia, viaje["fecha_inicio"], viaje["trip_id"])
            if mejor is None or clave < mejor:
                mejor = clave
    return mejor[2] if mejor else None


def crear_viaje(tx: Transaccion, unidad: UnidadDeCambio, ruteo: RuteoParticiones, user_id: str, nombre: str) -> str:
    trip_id = ruteo.nuevo_id_con_region(user_id)
    tx.ejecutar("INSERT INTO viajes (trip_id, user_id, particion, nombre, estado, creado) "
                "VALUES (?, ?, ?, ?, 'activo', ?)",
                (trip_id, user_id, ruteo.particion(user_id), nombre, unidad.ahora))
    unidad.viaje(trip_id, "created")
    unidad.motivo("trip_created")
    return trip_id


def asignar(tx: Transaccion, unidad: UnidadDeCambio, ruteo: RuteoParticiones, booking_id: str) -> str | None:
    """Asigna una reserva cuyo viaje no fijó el usuario. Sin fechas, queda pendiente en "sin asignar"."""
    reserva = tx.uno("SELECT * FROM reservas WHERE booking_id = ?", (booking_id,))
    anterior = reserva["trip_id"]
    if not reserva["inicio"]:
        destino = None
        if reserva["estado"] != "cancelled":
            tx.ejecutar("UPDATE reservas SET estado = 'pending' WHERE booking_id = ?", (booking_id,))
    else:
        inicio = _dia(reserva["inicio"])
        fin = _dia(reserva["fin"] or reserva["inicio"])
        destino = candidato(tx, reserva["user_id"], inicio, fin)
        if destino is None:
            lugar = reserva["lugar_llegada"] or reserva["lugar"] or "Viaje"
            destino = crear_viaje(tx, unidad, ruteo, reserva["user_id"], f"{lugar} {inicio:%Y-%m}")
    if destino != anterior:
        tx.ejecutar("UPDATE reservas SET trip_id = ? WHERE booking_id = ?", (destino, booking_id))
        unidad.viaje(destino)
        quitar_viaje_vacio(tx, unidad, anterior)
    return destino


def quitar_viaje_vacio(tx: Transaccion, unidad: UnidadDeCambio, trip_id: str | None):
    """Un viaje sin reservas deja de existir (con sus invitaciones)."""
    if not trip_id:
        return
    if tx.uno("SELECT COUNT(*) AS n FROM reservas WHERE trip_id = ?", (trip_id,))["n"] == 0:
        tx.ejecutar("DELETE FROM comparticiones WHERE trip_id = ?", (trip_id,))
        tx.ejecutar("DELETE FROM viajes WHERE trip_id = ?", (trip_id,))
        unidad.viaje(trip_id, "deleted")
        unidad.motivo("trip_deleted")
    else:
        unidad.viaje(trip_id)
