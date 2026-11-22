"""Recepción de `booking.facts.v1` en la cola `recommendation.facts` (ADR-0081).

En una sola transacción, antes del ACK: control de entrada por `eventId` (Idempotent Receiver), actualización del
perfil y, si el hecho es una cancelación de alojamiento o transporte informada por un proveedor o por correo de un
viajero con la recomendación activada, una búsqueda pendiente. Una cancelación o un borrado del propio viajero
(`source` manual) no dispara sugerencias.
"""
from __future__ import annotations

import json
import uuid
from datetime import date

from comun.infraestructura.broker import Mensaje
from comun.infraestructura.db import con_reintentos
from comun.infraestructura.reloj import iso
from comun.observabilidad import contexto_traza, continuar_traza, metricas
from contratos.esquemas import ContratoInvalido, validar_evento
from recomendacion.busqueda.adaptadores import TIPOS_TRANSPORTE, Consulta

TIPOS_ALOJAMIENTO = ("hotel",)


def consulta_para(hecho: dict) -> Consulta | None:
    """Consulta normalizada (`specs/offer-search.md`) para buscar alternativas del mismo tipo."""
    if not hecho.get("startDate") or not hecho.get("locationCity"):
        return None
    if hecho["type"] in TIPOS_ALOJAMIENTO:
        noches = 1
        if hecho.get("endDate"):
            noches = max((date.fromisoformat(hecho["endDate"]) - date.fromisoformat(hecho["startDate"])).days, 1)
        return Consulta("hotel", hecho["locationCity"], hecho["startDate"], nights=noches)
    if hecho["type"] in TIPOS_TRANSPORTE and hecho.get("arrivalCity"):
        return Consulta(hecho["type"], hecho["locationCity"], hecho["startDate"], arrivalLocation=hecho["arrivalCity"])
    return None


def dispara(hecho: dict) -> bool:
    return (hecho["changeType"] == "cancelled" and hecho["source"] in ("provider", "email")
            and hecho["type"] in TIPOS_ALOJAMIENTO + TIPOS_TRANSPORTE)


class ConsumidorHechos:
    def __init__(self, app):
        self.app = app

    def procesar(self, mensaje: Mensaje):
        app = self.app
        contexto_traza.set(continuar_traza(mensaje.encabezados.get("traceparent")))
        hecho = mensaje.cuerpo
        try:
            validar_evento("booking.facts.v1", hecho)
        except ContratoInvalido as error:
            app.logger.alerta("hecho_invalido_apartado", eventId=hecho.get("eventId"), errores=error.errores)
            return
        if hecho["homeRegion"] != app.region:
            app.logger.alerta("hecho_de_otra_region", eventId=hecho["eventId"])
            return

        def transaccion() -> str:
            with app.base.transaccion() as tx:
                if tx.uno("SELECT 1 AS x FROM hechos_recibidos WHERE event_id = ?", (hecho["eventId"],)):
                    return "duplicado"
                ahora = iso(app.reloj.ahora())
                tx.ejecutar("INSERT INTO hechos_recibidos (event_id, user_id, recibido) VALUES (?, ?, ?)",
                            (hecho["eventId"], hecho["userId"], ahora))
                perfil = app.perfiles.obtener(tx, hecho["userId"])
                app.perfiles.registrar_hecho(perfil, hecho)
                app.perfiles.guardar(tx, perfil)
                if not dispara(hecho):
                    return "perfil"
                if not perfil["activada"]:
                    return "desactivada"  # opt-out: no se generan sugerencias (QA-14)
                if hecho["tripId"] == "unassigned":
                    return "sin_viaje"  # la reserva propuesta necesita el viaje de la cancelada (ADR-0084)
                consulta = consulta_para(hecho)
                if consulta is None:
                    return "sin_datos_para_buscar"
                cancelada = {k: hecho.get(c) for k, c in (("type", "type"), ("provider", "provider"),
                                                          ("startsAt", "startsAt"), ("endsAt", "endsAt"),
                                                          ("location", "locationCity"),
                                                          ("arrivalLocation", "arrivalCity"))}
                if not cancelada["startsAt"]:
                    cancelada["startsAt"] = f"{hecho['startDate']}T12:00:00+00:00"
                tx.ejecutar("INSERT INTO busquedas (busqueda_id, user_id, home_region, trip_id, cancelled_booking_id, "
                            "clave, consulta, cancelada, correlation_id, estado, creada) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)",
                            (str(uuid.uuid4()), hecho["userId"], hecho["homeRegion"], hecho["tripId"],
                             hecho["bookingId"], consulta.clave, json.dumps(consulta.__dict__), json.dumps(cancelada),
                             hecho.get("correlationId"), ahora))
                return "busqueda_pendiente"

        resultado = con_reintentos(transaccion)
        metricas.incrementar(f"recomendacion_hecho_{resultado}")
        app.logger.info("hecho_recibido", eventId=hecho["eventId"], resultado=resultado)
