"""Módulo `envio-push` del notificador (ADR-0046): lee la cola compartida `notifier.push`. Solo los avisos
`important` generan push; cada push tiene identidad estable (eventId + dispositivo), se registra 24 h para descartar
repetidos y lleva una clave de colapso. El emisor de push del sistema operativo está simulado."""
from __future__ import annotations

from datetime import timedelta

from comun.infraestructura.broker import Mensaje
from comun.infraestructura.db import BaseDatos
from comun.infraestructura.reloj import Reloj, iso
from comun.observabilidad import Logger, metricas
from contratos.esquemas import validar_evento

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
        validar_evento("panel.changed.v1", aviso)
        if aviso["relevance"] != "important":
            return
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
            colapso = clave[:64]  # apns-collapse-id / collapse_key
            self.enviados.append({"dispositivo": dispositivo, "reason": aviso["reason"], "collapseKey": colapso,
                                  "panelVersion": aviso["panelVersion"]})
            metricas.incrementar("push_enviado")
            self.logger.info("push_enviado", reason=aviso["reason"], panelVersion=aviso["panelVersion"])
