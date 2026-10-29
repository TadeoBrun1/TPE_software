"""Representación de reservas y viajes en la API (`Booking`, `Trip`, `SharedTrip` de la OpenAPI).

El backend devuelve datos neutros (ADR-0065): fechas ISO 8601 con desfase, zona IANA, montos con moneda ISO 4217 y
códigos en lugar de textos. La vista compartida es una proyección explícita de campos comunes: no incluye notas,
códigos de reserva ni `details` (ADR-0061, ADR-0066).
"""
from __future__ import annotations

import json

# Dueño por campo (ADR-0044). Proveedor: lo que informa la novedad. Usuario: lo que solo cambia el viajero.
CAMPOS_PROVEEDOR = ("startsAt", "endsAt", "timeZone", "arrivalTimeZone", "location", "arrivalLocation", "status",
                    "provider", "providerReference", "type", "details", "price")
CAMPOS_USUARIO = ("displayName", "notes", "tripId")

COLUMNAS = {
    "startsAt": "inicio", "endsAt": "fin", "timeZone": "zona", "arrivalTimeZone": "zona_llegada",
    "location": "lugar", "arrivalLocation": "lugar_llegada", "status": "estado", "provider": "proveedor",
    "providerReference": "referencia_proveedor", "type": "tipo", "displayName": "nombre_visible", "notes": "notas",
    "tripId": "trip_id",
}

CAMPOS_HORARIO = ("startsAt", "endsAt")


def _sin_nulos(valor: dict) -> dict:
    return {k: v for k, v in valor.items() if v is not None}


def reserva_a_api(fila: dict) -> dict:
    precio = None
    if fila.get("precio_monto") is not None and fila.get("precio_moneda"):
        precio = {"amount": fila["precio_monto"], "currency": fila["precio_moneda"]}
    return _sin_nulos({
        "id": fila["booking_id"],
        "tripId": fila.get("trip_id"),
        "type": fila["tipo"],
        "status": fila["estado"],
        "origin": fila["origen"],
        "provider": fila.get("proveedor"),
        "providerReference": fila.get("referencia_proveedor"),
        "startsAt": fila.get("inicio"),
        "endsAt": fila.get("fin"),
        "timeZone": fila.get("zona"),
        "arrivalTimeZone": fila.get("zona_llegada"),
        "location": fila.get("lugar"),
        "arrivalLocation": fila.get("lugar_llegada"),
        "displayName": fila.get("nombre_visible"),
        "price": precio,
        "details": json.loads(fila["detalles"]) if fila.get("detalles") else None,
        "notes": fila.get("notas"),
        "userEditedFields": json.loads(fila.get("campos_editados") or "[]"),
        "version": fila["version"],
    })


def reserva_compartida(fila: dict) -> dict:
    """Lista explícita de campos permitidos (no se serializa la reserva completa con exclusiones)."""
    return _sin_nulos({
        "id": fila["booking_id"],
        "type": fila["tipo"],
        "status": fila["estado"],
        "startsAt": fila.get("inicio"),
        "endsAt": fila.get("fin"),
        "timeZone": fila.get("zona"),
        "arrivalTimeZone": fila.get("zona_llegada"),
        "location": fila.get("lugar"),
        "arrivalLocation": fila.get("lugar_llegada"),
        "displayName": fila.get("nombre_visible"),
    })


def viaje_a_api(viaje: dict, reservas: list[dict] | None, resumen: bool = False) -> dict:
    datos = _sin_nulos({
        "id": viaje["trip_id"],
        "name": viaje["nombre"],
        "status": "archived" if viaje["estado"] == "archivado" else "active",
        "startDate": viaje.get("fecha_inicio"),
        "endDate": viaje.get("fecha_fin"),
        "reactivatedUntil": viaje.get("reactivado_hasta"),
    })
    if resumen:
        datos["summaryOnly"] = True
        datos["bookingCount"] = len(reservas or [])
    else:
        datos["bookings"] = [reserva_a_api(r) for r in reservas or []]
    return datos


def viaje_compartido(viaje: dict, reservas: list[dict]) -> dict:
    return _sin_nulos({
        "id": viaje["trip_id"],
        "name": viaje["nombre"],
        "status": "archived" if viaje["estado"] == "archivado" else "active",
        "startDate": viaje.get("fecha_inicio"),
        "endDate": viaje.get("fecha_fin"),
        "bookings": [reserva_compartida(r) for r in reservas],
    })


def fecha(texto: str | None) -> str | None:
    """Día local del lugar de la reserva (la parte de fecha de un ISO 8601 con desfase)."""
    return texto[:10] if texto else None
