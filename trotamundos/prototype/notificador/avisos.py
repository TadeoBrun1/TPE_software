"""Módulo `consumidor-avisos` del notificador (ADR-0046): lee la cola exclusiva de la instancia. Cada instancia
recibe todos los avisos; solo la que tiene la conexión del usuario lo envía.

* `panel.changed.v1` → evento SSE `panel-changed` (versión del panel y `correlationIds`).
* `suggestions.available.v1` (iteración 5, ADR-0084) → evento SSE `suggestions-available` (viaje y cantidad).
* `account.deleted.v1` (iteración 5, ADR-0085) → evento SSE `account-deleted` y cierre de las conexiones del usuario.
"""
from __future__ import annotations

from comun.infraestructura.broker import Mensaje
from comun.observabilidad import contexto_traza, continuar_traza, metricas
from contratos.esquemas import ContratoInvalido, validar_evento
from contratos.topologia import RK_CUENTA, RK_SUGERENCIAS


class ConsumidorAvisos:
    def __init__(self, conexiones, logger):
        self.conexiones = conexiones
        self.logger = logger

    def procesar(self, mensaje: Mensaje):
        contexto_traza.set(continuar_traza(mensaje.encabezados.get("traceparent")))
        aviso = mensaje.cuerpo
        nombre = mensaje.routing_key if mensaje.routing_key in (RK_SUGERENCIAS, RK_CUENTA) else "panel.changed.v1"
        try:
            validar_evento(nombre, aviso)
        except ContratoInvalido as error:
            self.logger.alerta("aviso_invalido", errores=error.errores)
            return
        if nombre == RK_CUENTA:
            evento = {"_evento": "account-deleted"}
        elif nombre == RK_SUGERENCIAS:
            evento = {"_evento": "suggestions-available", "tripId": aviso["tripId"],
                      "cancelledBookingId": aviso["cancelledBookingId"], "suggestionCount": aviso["suggestionCount"]}
        else:
            evento = {"panelVersion": aviso["panelVersion"]}
            if aviso.get("correlationIds"):
                evento["correlationIds"] = aviso["correlationIds"]
        if self.conexiones.avisar(f"{aviso['homeRegion']}:{aviso['userId']}", evento):
            metricas.incrementar("sse_aviso_enviado")
