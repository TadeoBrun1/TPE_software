"""Procesador de novedades: tubería de etapas internas (ADR-0022, Pipes and Filters).

selección → extracción → normalización → validación. Cada elemento termina en un evento publicable, un descarte
justificado o un caso pendiente; nunca se fabrican horas ni identificadores desconocidos.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from comun.infraestructura.reloj import iso
from contratos.esquemas import ContratoInvalido, validar_evento


@dataclass
class Resultado:
    tipo: str            # evento | descarte | pendiente
    motivo: str | None
    evento: dict | None = None
    business_change_key: str | None = None


# ------------------------------------------------------------------------------------------ extracción

_CAMPO = re.compile(r"^\s*([A-Za-zÁÉÍÓÚáéíóúñ ]+):\s*(.+?)\s*$")


def extraer_correo(crudo: dict) -> dict:
    """Confirmación de reserva en texto (formato sintético de un emisor hotelero)."""
    campos = {}
    for linea in crudo["body"].splitlines():
        coincidencia = _CAMPO.match(linea)
        if coincidencia:
            campos[coincidencia.group(1).strip().lower()] = coincidencia.group(2)
    return {
        "tipo": "hotel" if "hotel" in campos else None,
        "referencia": campos.get("localizador"),
        "estado": {"confirmada": "confirmed", "cancelada": "cancelled", "pendiente": "pending"}.get(
            campos.get("estado", "confirmada").lower(), "unknown"),
        "inicio": campos.get("entrada"), "fin": campos.get("salida"),
        "lugar": campos.get("ciudad"), "zona": campos.get("zona"),
        "version": None,  # los correos no traen versión externa
    }


def extraer_hotel(crudo: dict) -> dict:
    return {
        "tipo": "hotel", "referencia": crudo["reservationId"],
        "estado": {"CONFIRMED": "confirmed", "ON_HOLD": "pending", "CANCELLED": "cancelled"}.get(crudo["status"],
                                                                                              "unknown"),
        "inicio": f"{crudo['checkIn']} {crudo.get('checkInTime', '15:00')}" if crudo.get("checkIn") else None,
        "fin": f"{crudo['checkOut']} {crudo.get('checkOutTime', '11:00')}" if crudo.get("checkOut") else None,
        "lugar": crudo.get("city"), "zona": crudo.get("timeZone"), "version": str(crudo["version"]),
        "ocurrido": crudo.get("updatedAt"),
    }


def extraer_aerolinea(crudo: dict) -> dict:
    origen, destino = crudo.get("from", {}), crudo.get("to", {})
    return {
        "tipo": "flight", "referencia": crudo["pnr"],
        "estado": {"HK": "confirmed", "UN": "unknown", "XX": "cancelled"}.get(crudo["state"], "unknown"),
        "inicio": origen.get("time"), "fin": destino.get("time"), "zona": origen.get("tz"),
        "zona_llegada": destino.get("tz"), "lugar": origen.get("airport"), "lugar_llegada": destino.get("airport"),
        "version": str(crudo["rev"]),
        "detalles": {"schema": "flight.v1", "flightNumber": crudo["flightNumber"]} if crudo.get("flightNumber") else None,
    }


EXTRACTORES = {"correo:texto": extraer_correo, "api:hotel": extraer_hotel, "api:aerolinea": extraer_aerolinea}

# ------------------------------------------------------------------------------------------ normalización


def _con_zona(texto: str | None, zona: str | None) -> str | None:
    """Fecha y hora local + zona IANA → ISO 8601 con desfase. Sin zona no se inventa un desfase."""
    if not texto:
        return None
    if not zona:
        raise ValueError("fecha sin zona horaria")
    try:
        local = datetime.fromisoformat(texto.replace(" ", "T"))
        return local.replace(tzinfo=ZoneInfo(zona)).isoformat(timespec="seconds") if local.tzinfo is None \
            else local.isoformat(timespec="seconds")
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError(str(error)) from error


def _clave(*partes) -> str:
    return hashlib.sha256(json.dumps(partes, separators=(",", ":")).encode()).hexdigest()[:40]


class Tuberia:
    def __init__(self, reloj):
        self.reloj = reloj

    def procesar(self, vinculacion: dict, fuente: str, elemento, correlation_id: str) -> Resultado:
        # 1. Selección: correo con remitentes permitidos; APIs con origen validado por el adaptador.
        if fuente == "email":
            permitidos = json.loads(vinculacion["remitentes"] or "[]")
            if elemento.crudo.get("from") not in permitidos:
                return Resultado("descarte", "remitente_no_permitido")
        # 2. Extracción según el formato del emisor.
        extraido = EXTRACTORES[elemento.formato](elemento.crudo)
        if extraido["tipo"] is None:
            return Resultado("descarte", "no_es_una_reserva")
        # 3. Normalización al modelo canónico.
        try:
            reserva = {"type": extraido["tipo"], "status": extraido["estado"]}
            opcionales = {
                "startAt": _con_zona(extraido.get("inicio"), extraido.get("zona")),
                "endAt": _con_zona(extraido.get("fin"), extraido.get("zona_llegada") or extraido.get("zona")),
                "location": extraido.get("lugar"), "arrivalLocation": extraido.get("lugar_llegada"),
                "timeZone": extraido.get("zona"), "arrivalTimeZone": extraido.get("zona_llegada"),
                "details": extraido.get("detalles"),
            }
        except ValueError as error:
            return Resultado("pendiente", f"dato_invalido: {error}")
        reserva.update({k: v for k, v in opcionales.items() if v})
        referencia = extraido.get("referencia")
        evento = {
            "eventId": str(uuid.uuid4()), "schemaVersion": "1", "correlationId": correlation_id,
            "userId": vinculacion["user_id"], "connectionId": vinculacion["connection_id"],
            "providerId": vinculacion["provider_id"], "source": fuente, "detectedAt": iso(self.reloj.ahora()),
            "changeType": "cancel" if reserva["status"] == "cancelled" else "upsert",
            # Sin referencia estable de la reserva no se aplica automáticamente (ingestion-contract.md).
            "requiresResolution": referencia is None,
            "reservation": reserva, "homeRegion": vinculacion["home_region"],
        }
        if fuente == "email":
            evento["sourceMessageId"] = elemento.item_id
        if referencia:
            evento["externalReservationId"] = referencia
        if extraido.get("version"):
            evento["sourceVersion"] = extraido["version"]
        if extraido.get("ocurrido"):
            evento["occurredAt"] = extraido["ocurrido"]  # nunca se reemplaza por detectedAt
        evento["reservationKey"] = _clave(vinculacion["connection_id"], vinculacion["provider_id"],
                                          referencia or elemento.item_id)
        if fuente == "email":
            clave_negocio = _clave(elemento.item_id, referencia)
        elif extraido.get("version"):
            clave_negocio = _clave(vinculacion["provider_id"], referencia, extraido["version"])
        else:  # huella canónica de los campos normalizados, sin horas de detección
            clave_negocio = _clave(vinculacion["provider_id"], referencia, reserva)
        evento["businessChangeKey"] = clave_negocio
        # 4. Validación contra el contrato publicado.
        try:
            validar_evento("booking.change.detected.v1", evento)
        except ContratoInvalido as error:
            return Resultado("pendiente", f"contrato: {error}")
        return Resultado("evento", None, evento, clave_negocio)
