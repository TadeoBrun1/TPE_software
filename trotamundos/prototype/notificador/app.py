"""Notificador de cambios del panel (ADR-0046): proceso separado del núcleo, una o más instancias por región.

Módulos: `sse` (conexiones-sse), `avisos` (consumidor-avisos, cola por instancia) y `push` (envio-push, cola
compartida). No accede a la base del núcleo ni importa su código: solo `contratos` (vista de módulos).
"""
from __future__ import annotations

import hmac
import os
import uuid

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from comun.infraestructura import broker as broker_mod
from comun.infraestructura import db as db_mod
from comun.infraestructura.broker import Broker
from comun.infraestructura.db import BaseDatos
from comun.infraestructura.reloj import Reloj
from comun.observabilidad import Logger, metricas
from contratos.topologia import COLA_PUSH, cola_instancia_notificador, topologia_region
from notificador.avisos import ConsumidorAvisos
from notificador.push import EnvioPush
from notificador.sse import ConexionesSSE, flujo_eventos


class Notificador:
    def __init__(self, region: str, broker: Broker, base_push: BaseDatos, clave_puerta: str,
                 reloj: Reloj | None = None, logger: Logger | None = None, instancia: str | None = None):
        self.region = region
        self.broker = broker
        self.clave_puerta = clave_puerta
        self.reloj = reloj or Reloj()
        self.logger = logger or Logger("notificador", region)
        self.instancia = instancia or uuid.uuid4().hex[:8]
        self.conexiones = ConexionesSSE()
        self.avisos = ConsumidorAvisos(self.conexiones, self.logger)
        self.push = EnvioPush(base_push, self.reloj, self.logger)
        self.app = Starlette(routes=[Route("/panel/events", self.eventos, methods=["GET"]),
                                     Route("/metrics", self.estado, methods=["GET"])])

    def preparar_mensajeria(self):
        cola = cola_instancia_notificador(self.instancia)
        self.broker.declarar_cola(cola)
        self.broker.consumir(cola.nombre, self.avisos.procesar)
        self.broker.consumir(COLA_PUSH, self.push.procesar, prefetch=5)

    async def eventos(self, request: Request):
        """Solo la puerta de entrada abre conexiones (validó el ticket SSE)."""
        if not hmac.compare_digest(request.headers.get("x-gateway-key", ""), self.clave_puerta):
            return JSONResponse({"code": "unauthorized", "message": "No autenticado"}, status_code=401)
        usuario = f"{request.headers['x-principal-region']}:{request.headers['x-principal-user']}"
        return StreamingResponse(flujo_eventos(self.conexiones, usuario), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    async def estado(self, request: Request):
        return JSONResponse(metricas.resumen())


def desde_entorno() -> Notificador:  # pragma: no cover - docker compose
    region = os.environ["REGION"]
    notificador = Notificador(region, broker_mod.abrir(os.environ.get("BROKER", "memoria")),
                              db_mod.abrir(os.environ["BASE_PUSH"], f"{region}-push"), os.environ["CLAVE_PUERTA"])
    notificador.broker.declarar(topologia_region())  # idempotente: no depende de que el núcleo arranque antes
    notificador.preparar_mensajeria()
    notificador.broker.iniciar()
    return notificador
