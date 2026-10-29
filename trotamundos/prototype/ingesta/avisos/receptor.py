"""Receptor de avisos (ADR-0020, ADR-0025): recibe avisos de los proveedores solo a través de la puerta de entrada,
verifica el origen (firma de la suscripción) y persiste trabajo durable antes de confirmar con 202. Un aviso
repetido no origina otra consulta."""
from __future__ import annotations

import hashlib
import hmac
import json

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from comun.infraestructura.reloj import iso
from comun.observabilidad import metricas


def firma_aviso(secreto: str, cuerpo: bytes) -> str:
    return hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()


class Receptor:
    def __init__(self, registro, vinculaciones, planificador, reloj):
        self.registro = registro
        self.vinculaciones = vinculaciones
        self.planificador = planificador
        self.reloj = reloj

    async def recibir(self, request: Request):
        cuerpo = await request.body()
        try:
            aviso = json.loads(cuerpo)
            vinculacion = self.vinculaciones.obtener(aviso["connectionId"])
            aviso_id = aviso["avisoId"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return JSONResponse({"code": "invalid_request", "message": "Aviso inválido"}, status_code=400)
        firma = request.headers.get("x-provider-signature", "")
        if (vinculacion is None or vinculacion["provider_id"] != request.path_params["providerId"]
                or not hmac.compare_digest(firma, firma_aviso(vinculacion["secreto_avisos"] or "", cuerpo))):
            metricas.incrementar("avisos_rechazados")
            return JSONResponse({"code": "unauthorized", "message": "Firma inválida"}, status_code=401)
        with self.registro.base.transaccion() as tx:
            nuevo = tx.ejecutar("INSERT INTO avisos_recibidos (aviso_id, provider_id, connection_id, recibido) "
                                "VALUES (?, ?, ?, ?) ON CONFLICT (aviso_id) DO NOTHING",
                                (aviso_id, vinculacion["provider_id"], vinculacion["connection_id"],
                                 iso(self.reloj.ahora())))
        if nuevo:
            self.planificador.agendar(vinculacion["connection_id"], "aviso")
        metricas.incrementar("avisos_recibidos")
        return Response(status_code=202)
