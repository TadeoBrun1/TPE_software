"""Eventos que la recomendación escribe en su outbox, en la misma transacción que el cambio (ADR-0084).

Cada evento se valida contra su contrato AsyncAPI antes de guardarse.
"""
from __future__ import annotations

import uuid

from comun.infraestructura import outbox
from comun.infraestructura.db import Transaccion
from comun.observabilidad import continuar_traza, contexto_traza
from contratos.esquemas import validar_evento
from contratos.topologia import EXCHANGE_DOMINIO, RK_ACEPTADA, RK_SUGERENCIAS


def _guardar(tx: Transaccion, nombre: str, routing_key: str, cuerpo: dict, ahora: str):
    validar_evento(nombre, cuerpo)
    outbox.agregar(tx, EXCHANGE_DOMINIO, routing_key, cuerpo, {"traceparent": continuar_traza(contexto_traza.get())},
                   ahora)


def sugerencias_disponibles(tx, busqueda: dict, cantidad: int, parcial: bool, ahora: str):
    cuerpo = {"eventId": str(uuid.uuid4()), "schemaVersion": "1", "homeRegion": busqueda["home_region"],
              "userId": busqueda["user_id"], "tripId": busqueda["trip_id"],
              "cancelledBookingId": busqueda["cancelled_booking_id"], "suggestionCount": cantidad,
              "partial": parcial, "collapseKey": f"booking-cancel:{busqueda['cancelled_booking_id']}",
              "committedAt": ahora}
    if busqueda.get("correlation_id"):
        cuerpo["correlationId"] = busqueda["correlation_id"]
    if busqueda.get("cancelacion_confirmada"):
        cuerpo["cancellationCommittedAt"] = busqueda["cancelacion_confirmada"]  # para medir QA-11 en el notificador
    tipo = (busqueda.get("cancelada") or {}).get("type")
    if tipo:
        cuerpo["bookingType"] = tipo
    _guardar(tx, "suggestions.available.v1", RK_SUGERENCIAS, cuerpo, ahora)


def sugerencia_aceptada(tx, region: str, fila: dict, oferta: dict, correlation_id: str | None, ahora: str):
    campos = ("type", "provider", "startsAt", "endsAt", "timeZone", "arrivalTimeZone", "location", "arrivalLocation",
              "stops", "price", "offerUrl")
    cuerpo = {"eventId": str(uuid.uuid4()), "schemaVersion": "1", "homeRegion": region, "userId": fila["user_id"],
              "tripId": fila["trip_id"], "suggestionId": fila["suggestion_id"],
              "cancelledBookingId": fila["cancelled_booking_id"],
              "offer": {k: oferta[k] for k in campos if oferta.get(k) is not None}, "acceptedAt": ahora}
    if correlation_id:
        cuerpo["correlationId"] = correlation_id
    _guardar(tx, "suggestion.accepted.v1", RK_ACEPTADA, cuerpo, ahora)
