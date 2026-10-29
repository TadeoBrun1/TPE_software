"""Gestión manual de reservas (RF-04, ADR-0044 y ADR-0048).

Los campos que edita el usuario quedan marcados; las novedades posteriores pueden cambiar los del proveedor (con
aviso) y nunca los del usuario. Borrar una reserva que vino de un proveedor deja una marca de borrado para que las
novedades no la recreen. `If-Match` con la versión evita pisar un cambio concurrente.
"""
from __future__ import annotations

import json

from comun.infraestructura.db import Transaccion
from nucleo.datos.ruteo import RuteoParticiones
from nucleo.esquemas.registro import RegistroEsquemas
from nucleo.panel.unidad import UnidadDeCambio
from nucleo.reservas.modelo import CAMPOS_HORARIO, COLUMNAS
from nucleo.viajes import asignacion
from nucleo.viajes.ciclo_vida import reactivar


class ErrorDominio(Exception):
    def __init__(self, estado: int, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.estado = estado
        self.codigo = codigo
        self.mensaje = mensaje


def _viaje_propio(tx: Transaccion, user_id: str, trip_id: str) -> dict:
    viaje = tx.uno("SELECT * FROM viajes WHERE trip_id = ? AND user_id = ?", (trip_id, user_id))
    if viaje is None:
        raise ErrorDominio(400, "trip_not_owned", "tripId no es un viaje del usuario")
    return viaje


def crear(tx: Transaccion, unidad: UnidadDeCambio, ruteo: RuteoParticiones, esquemas: RegistroEsquemas,
          user_id: str, datos: dict) -> str:
    esquemas.validar(datos["type"], datos.get("details"))
    booking_id = ruteo.nuevo_id(user_id)
    precio = datos.get("price") or {}
    tx.ejecutar(
        "INSERT INTO reservas (booking_id, user_id, trip_id, tipo, estado, origen, proveedor, referencia_proveedor, "
        "inicio, fin, zona, zona_llegada, lugar, lugar_llegada, nombre_visible, precio_monto, precio_moneda, "
        "detalles, notas, campos_editados, version, creado) "
        "VALUES (?, ?, NULL, ?, 'confirmed', 'manual', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
        (booking_id, user_id, datos["type"], datos.get("provider"), datos.get("providerReference"),
         datos.get("startsAt"), datos.get("endsAt"), datos.get("timeZone"), datos.get("arrivalTimeZone"),
         datos.get("location"), datos.get("arrivalLocation"), datos.get("displayName"), precio.get("amount"),
         precio.get("currency"), json.dumps(datos["details"]) if datos.get("details") else None,
         datos.get("notes"), json.dumps(["tripId"] if datos.get("tripId") else []), unidad.ahora))
    if datos.get("provider") and datos.get("providerReference"):
        # La marca de borrado se quita si el usuario vuelve a agregar esa reserva a mano (ADR-0044).
        tx.ejecutar("DELETE FROM marcas_borrado WHERE user_id = ? AND provider_id = ? AND external_reservation_id = ?",
                    (user_id, datos["provider"], datos["providerReference"]))
    if datos.get("tripId"):
        viaje = _viaje_propio(tx, user_id, datos["tripId"])
        tx.ejecutar("UPDATE reservas SET trip_id = ? WHERE booking_id = ?", (viaje["trip_id"], booking_id))
        unidad.viaje(viaje["trip_id"])
        if viaje["estado"] == "archivado" and datos.get("startsAt", "")[:10] >= unidad.reloj.hoy().isoformat():
            reactivar(tx, unidad, viaje, unidad.reloj.hoy(), a_mano=True)  # reserva futura en un viaje archivado
    else:
        asignacion.asignar(tx, unidad, ruteo, booking_id)
    unidad.motivo("booking_added")
    unidad.reserva(tx.uno("SELECT * FROM reservas WHERE booking_id = ?", (booking_id,)), "created")
    return booking_id


def _reserva_propia(tx: Transaccion, user_id: str, booking_id: str, version_esperada: str | None) -> dict:
    reserva = tx.uno("SELECT * FROM reservas WHERE booking_id = ? AND user_id = ?", (booking_id, user_id))
    if reserva is None:
        raise ErrorDominio(404, "not_found", "No existe o no pertenece al usuario")
    if version_esperada is None:
        raise ErrorDominio(400, "if_match_required", "Falta If-Match con la versión de la reserva")
    if version_esperada.strip('"') != str(reserva["version"]):
        raise ErrorDominio(412, "version_mismatch", "La reserva cambió desde la versión indicada")
    return reserva


def editar(tx: Transaccion, unidad: UnidadDeCambio, ruteo: RuteoParticiones, esquemas: RegistroEsquemas,
           user_id: str, booking_id: str, version: str | None, cambios: dict):
    reserva = _reserva_propia(tx, user_id, booking_id, version)
    editados = set(json.loads(reserva["campos_editados"]))
    asignaciones, valores = [], []
    for campo, valor in cambios.items():
        if campo == "price":
            asignaciones += ["precio_monto = ?", "precio_moneda = ?"]
            valores += [valor.get("amount"), valor.get("currency")]
        elif campo == "details":
            esquemas.validar(reserva["tipo"], valor)
            asignaciones.append("detalles = ?")
            valores.append(json.dumps(valor))
        elif campo == "tripId":
            continue
        else:
            asignaciones.append(f"{COLUMNAS[campo]} = ?")
            valores.append(valor)
        editados.add(campo)
    if asignaciones:
        tx.ejecutar(f"UPDATE reservas SET {', '.join(asignaciones)} WHERE booking_id = ?", (*valores, booking_id))
    if "tripId" in cambios:
        viaje = _viaje_propio(tx, user_id, cambios["tripId"])
        tx.ejecutar("UPDATE reservas SET trip_id = ? WHERE booking_id = ?", (viaje["trip_id"], booking_id))
        unidad.viaje(viaje["trip_id"])
        asignacion.quitar_viaje_vacio(tx, unidad, reserva["trip_id"])
        editados.add("tripId")  # desde ahora el viaje asignado es un campo del usuario (ADR-0048, regla 5)
    elif "tripId" not in editados and any(c in cambios for c in CAMPOS_HORARIO):
        asignacion.asignar(tx, unidad, ruteo, booking_id)
    else:
        unidad.viaje(reserva["trip_id"])
    tx.ejecutar("UPDATE reservas SET campos_editados = ?, version = version + 1 WHERE booking_id = ?",
                (json.dumps(sorted(editados)), booking_id))
    unidad.motivo("booking_updated")
    unidad.reserva(tx.uno("SELECT * FROM reservas WHERE booking_id = ?", (booking_id,)), "updated")


def borrar(tx: Transaccion, unidad: UnidadDeCambio, user_id: str, booking_id: str, version: str | None):
    reserva = _reserva_propia(tx, user_id, booking_id, version)
    if reserva["origen"] != "manual" and reserva["external_reservation_id"]:
        tx.ejecutar("INSERT INTO marcas_borrado (connection_id, provider_id, external_reservation_id, user_id, "
                    "trip_id, creado) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                    (reserva["connection_id"], reserva["provider_id"], reserva["external_reservation_id"], user_id,
                     reserva["trip_id"], unidad.ahora))
    tx.ejecutar("DELETE FROM reservas WHERE booking_id = ?", (booking_id,))
    asignacion.quitar_viaje_vacio(tx, unidad, reserva["trip_id"])
    unidad.motivo("booking_removed")
    unidad.reserva(reserva, "deleted")
