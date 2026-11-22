"""Módulo `envio-push` del notificador (ADR-0046): lee la cola compartida `notifier.push`. Solo los avisos
`important` generan push; cada push tiene identidad estable (eventId + dispositivo), se registra 24 h para descartar
repetidos y lleva una clave de colapso. El emisor de push del sistema operativo está simulado.

Iteración 5 (ADR-0084): `suggestions.available.v1` también genera push (motivo `alternatives_available`). La
cancelación y sus alternativas comparten `collapseKey` (`booking-cancel:<bookingId>`), así que en el teléfono el
segundo push reemplaza al primero. Sin `collapseKey`, la clave de colapso sale de la identidad del push."""
from __future__ import annotations

from datetime import timedelta

from comun.infraestructura.broker import Mensaje
from comun.infraestructura.db import BaseDatos
from comun.infraestructura.reloj import Reloj, iso
from comun.observabilidad import Logger, metricas
from contratos.esquemas import validar_evento
from contratos.topologia import RK_SUGERENCIAS

VIGENCIA_REGISTRO_PUSH = timedelta(hours=24)


class EnvioPush:
    """Puerto de push del sistema operativo (APNs/FCM). En el prototipo, un emisor simulado que registra los envíos."""

    def __init__(self, base: BaseDatos, reloj: Reloj, logger: Logger):
        self.base = base
        self.reloj = reloj
        self.logger = logger
        self.enviados: list[dict] = []
        base.crear_esquema(["CREATE TABLE IF NOT EXISTS push_enviados (clave TEXT PRIMARY KEY, vence TEXT NOT NULL)"])

    def dispositivos(self, home_region: str, user_id: str) -> list[str]:
        return [f"disp-{home_region}-{user_id}"]  # registro de dispositivos simulado

    def procesar(self, mensaje: Mensaje):
        aviso = mensaje.cuerpo
        if mensaje.routing_key == RK_SUGERENCIAS:
            validar_evento(RK_SUGERENCIAS, aviso)
            motivo = "alternatives_available"
        else:
            validar_evento("panel.changed.v1", aviso)
            if aviso["relevance"] != "important":
                return
            motivo = aviso["reason"]
        ahora = self.reloj.ahora()
        for dispositivo in self.dispositivos(aviso["homeRegion"], aviso["userId"]):
            clave = f"{aviso['eventId']}:{dispositivo}"
            with self.base.transaccion() as tx:
                tx.ejecutar("DELETE FROM push_enviados WHERE vence < ?", (iso(ahora),))
                if tx.uno("SELECT 1 AS x FROM push_enviados WHERE clave = ?", (clave,)):
                    metricas.incrementar("push_duplicado_descartado")
                    continue
                tx.ejecutar("INSERT INTO push_enviados (clave, vence) VALUES (?, ?)",
                            (clave, iso(ahora + VIGENCIA_REGISTRO_PUSH)))
            colapso = (aviso.get("collapseKey") or clave)[:64]  # apns-collapse-id / collapse_key
            enviado = {"dispositivo": dispositivo, "reason": motivo, "collapseKey": colapso}
            if "panelVersion" in aviso:
                enviado["panelVersion"] = aviso["panelVersion"]
            else:
                enviado.update(tripId=aviso["tripId"], suggestionCount=aviso["suggestionCount"])
            self.enviados.append(enviado)
            metricas.incrementar("push_enviado")
            self.logger.info("push_enviado", reason=motivo)
