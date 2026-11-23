"""Reservas propuestas (iteración 5, ADR-0084): alternativas aceptadas desde una sugerencia, todavía no reservadas.

* Se crean al consumir `suggestion.accepted.v1`, en el viaje de la reserva cancelada, con estado `proposed`, origen
  `suggestion` y el enlace a la oferta. Trotamundos no compra ni emite reservas.
* No generan `booking.facts.v1` ni mueven las fechas del viaje (`UnidadDeCambio`).
* Cuando llega la reserva real por la ingesta con el mismo tipo, el mismo proveedor y fechas que se superponen (un
  día de tolerancia, suposición) en el mismo viaje, la reserva real reemplaza a la propuesta. Si hay más de una
  propuesta posible, no se elige ninguna.
* La tarea diaria elimina las propuestas cuya fecha de inicio ya pasó (`vencer`).
"""
from __future__ import annotations

from datetime import date, timedelta

from comun.infraestructura.db import Transaccion
from nucleo.datos.ruteo import RuteoParticiones
from nucleo.panel.unidad import UnidadDeCambio

TOLERANCIA = timedelta(days=1)


def _dia(texto: str | None) -> date | None:
    return date.fromisoformat(texto[:10]) if texto else None


def aplicar_aceptacion(tx: Transaccion, unidad: UnidadDeCambio, ruteo: RuteoParticiones, evento: dict) -> str:
    """Crea la reserva propuesta; el control de entrada por `suggestionId` evita aplicarla dos veces."""
    if tx.uno("SELECT 1 AS x FROM sugerencias_aplicadas WHERE suggestion_id = ?", (evento["suggestionId"],)):
        return "duplicada"
    viaje = tx.uno("SELECT * FROM viajes WHERE trip_id = ? AND user_id = ?", (evento["tripId"], evento["userId"]))
    if viaje is None:
        resultado = "descartada:viaje_inexistente"
    else:
        oferta = evento["offer"]
        precio = oferta.get("price") or {}
        booking_id = ruteo.nuevo_id(evento["userId"])
        tx.ejecutar(
            "INSERT INTO reservas (booking_id, user_id, trip_id, tipo, estado, origen, proveedor, inicio, fin, zona, "
            "zona_llegada, lugar, lugar_llegada, precio_monto, precio_moneda, campos_editados, version, creado, "
            "url_oferta, suggestion_id) "
            "VALUES (?, ?, ?, ?, 'proposed', 'suggestion', ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', 1, ?, ?, ?)",
            (booking_id, evento["userId"], viaje["trip_id"], oferta["type"], oferta["provider"],
             oferta.get("startsAt"), oferta.get("endsAt"), oferta.get("timeZone"), oferta.get("arrivalTimeZone"),
             oferta.get("location"), oferta.get("arrivalLocation"), precio.get("amount"), precio.get("currency"),
             unidad.ahora, oferta["offerUrl"], evento["suggestionId"]))
        unidad.viaje(viaje["trip_id"])
        unidad.motivo("booking_added")
        unidad.reserva(tx.uno("SELECT * FROM reservas WHERE booking_id = ?", (booking_id,)), "created")
        resultado = "aplicada:propuesta"
    tx.ejecutar("INSERT INTO sugerencias_aplicadas (suggestion_id, user_id, resultado, procesado) VALUES (?, ?, ?, ?)",
                (evento["suggestionId"], evento["userId"], resultado, unidad.ahora))
    return resultado


def conciliar(tx: Transaccion, unidad: UnidadDeCambio, real: dict) -> str | None:
    """Si la reserva real coincide con una sola propuesta del mismo viaje, la propuesta se elimina."""
    if not real.get("trip_id") or not real.get("inicio"):
        return None
    inicio, fin = _dia(real["inicio"]), _dia(real.get("fin") or real["inicio"])
    candidatas = [p for p in tx.todos("SELECT * FROM reservas WHERE trip_id = ? AND estado = 'proposed' "
                                      "AND tipo = ? AND proveedor = ?",
                                      (real["trip_id"], real["tipo"], real.get("proveedor")))
                  if p["inicio"] and inicio - TOLERANCIA <= _dia(p["inicio"]) <= fin + TOLERANCIA]
    if len(candidatas) != 1:
        return None  # sin coincidencia, o ambigua: el viajero borra la que no corresponda
    tx.ejecutar("DELETE FROM reservas WHERE booking_id = ?", (candidatas[0]["booking_id"],))
    unidad.motivo("booking_updated")
    return candidatas[0]["booking_id"]


def vencer(tx: Transaccion, unidad: UnidadDeCambio, user_id: str, hoy: date) -> int:
    """Elimina las propuestas del usuario cuya fecha de inicio ya pasó sin confirmarse."""
    vencidas = tx.todos("SELECT booking_id, trip_id FROM reservas WHERE user_id = ? AND estado = 'proposed' "
                        "AND inicio IS NOT NULL AND substr(inicio, 1, 10) < ?", (user_id, hoy.isoformat()))
    for fila in vencidas:
        tx.ejecutar("DELETE FROM reservas WHERE booking_id = ?", (fila["booking_id"],))
        unidad.viaje(fila["trip_id"])
        unidad.motivo("booking_removed")
    return len(vencidas)
