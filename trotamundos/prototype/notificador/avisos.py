"""Módulo `consumidor-avisos` del notificador (ADR-0046): lee `panel.changed.v1` de la cola exclusiva de la
instancia. Cada instancia recibe todos los avisos; solo la que tiene la conexión del usuario lo envía."""
from __future__ import annotations

from comun.infraestructura.broker import Mensaje
from comun.observabilidad import contexto_traza, continuar_traza, metricas
from contratos.esquemas import ContratoInvalido, validar_evento


class ConsumidorAvisos:
    def __init__(self, conexiones, logger):
        self.conexiones = conexiones
        self.logger = logger

    def procesar(self, mensaje: Mensaje):
        contexto_traza.set(continuar_traza(mensaje.encabezados.get("traceparent")))
        aviso = mensaje.cuerpo
        try:
            validar_evento("panel.changed.v1", aviso)
        except ContratoInvalido as error:
            self.logger.alerta("aviso_invalido", errores=error.errores)
            return
        evento = {"panelVersion": aviso["panelVersion"]}
        if aviso.get("correlationIds"):
            evento["correlationIds"] = aviso["correlationIds"]
        if self.conexiones.avisar(f"{aviso['homeRegion']}:{aviso['userId']}", evento):
            metricas.incrementar("sse_aviso_enviado")
