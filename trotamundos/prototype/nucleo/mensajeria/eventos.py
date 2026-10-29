"""Eventos que el núcleo escribe en su outbox, en la misma transacción que el cambio (ADR-0027).

Cada evento se valida contra su contrato AsyncAPI antes de guardarse: un evento que no cumple el contrato aborta
la transacción en lugar de publicarse.

`booking.changed.v1` no se escribe: según `ingestion-operations.md` no tiene consumidores en la primera entrega, y
con `mandatory` un mensaje sin ruta es un fallo que dejaría la outbox trabada (hallazgo del prototipo, ver README).
"""
from __future__ import annotations

import uuid

from comun.infraestructura import outbox
from comun.infraestructura.db import Transaccion
from comun.observabilidad import continuar_traza, contexto_correlacion, contexto_traza
from contratos.esquemas import validar_evento
from contratos.topologia import EXCHANGE_DOMINIO, RK_HECHOS, RK_PANEL, RK_VIAJE


def _encabezados() -> dict:
    return {"traceparent": continuar_traza(contexto_traza.get())}


def _guardar(tx: Transaccion, nombre: str, routing_key: str, cuerpo: dict, ahora: str):
    validar_evento(nombre, cuerpo)
    outbox.agregar(tx, EXCHANGE_DOMINIO, routing_key, cuerpo, _encabezados(), ahora)


def panel_cambiado(tx, region, user_id, version, motivo, relevancia, correlation_ids, ahora):
    cuerpo = {
        "eventId": str(uuid.uuid4()), "schemaVersion": "1", "homeRegion": region, "userId": user_id,
        "panelVersion": version, "reason": motivo, "relevance": relevancia, "committedAt": ahora,
    }
    if correlation_ids:
        cuerpo["correlationIds"] = list(dict.fromkeys(correlation_ids))[:50]
    _guardar(tx, "panel.changed.v1", RK_PANEL, cuerpo, ahora)


def viaje_cambiado(tx, region, user_id, trip_id, tipo, version_panel, ahora):
    cuerpo = {
        "eventId": str(uuid.uuid4()), "schemaVersion": "1", "homeRegion": region, "userId": user_id,
        "tripId": trip_id, "changeType": tipo, "panelVersion": version_panel, "committedAt": ahora,
        "correlationId": contexto_correlacion.get() or str(uuid.uuid4()),
    }
    _guardar(tx, "trip.changed.v1", RK_VIAJE, cuerpo, ahora)


def hechos_reserva(tx, region, fila: dict, tipo_cambio: str, ahora: str):
    """`booking.facts.v1`: solo los campos permitidos para la analítica (ADR-0064)."""
    cuerpo = {
        "eventId": str(uuid.uuid4()), "schemaVersion": "1",
        "correlationId": contexto_correlacion.get() or str(uuid.uuid4()),
        "homeRegion": region, "userId": fila["user_id"], "tripId": fila.get("trip_id") or "unassigned",
        "bookingId": fila["booking_id"], "changeType": tipo_cambio, "type": fila["tipo"], "status": fila["estado"],
        "source": fila["origen"], "committedAt": ahora, "createdDate": fila["creado"][:10],
    }
    opcionales = {"provider": fila.get("proveedor"), "startDate": (fila.get("inicio") or "")[:10] or None,
                  "endDate": (fila.get("fin") or "")[:10] or None, "locationCity": fila.get("lugar"),
                  "arrivalCity": fila.get("lugar_llegada")}
    cuerpo.update({k: v for k, v in opcionales.items() if v})
    _guardar(tx, "booking.facts.v1", RK_HECHOS, cuerpo, ahora)
