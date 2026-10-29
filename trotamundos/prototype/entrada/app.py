"""Entrada global (ADR-0003, ADR-0060): elige la región de cada solicitud. Módulo `entrada/enrutamiento`.

* Login: la app envía el email; la entrada global calcula `HMAC(clave_directorio, email)` con una clave propia y lo
  busca en el directorio global mínimo (`HMAC(email) → región`). Responde igual exista o no la cuenta: si no
  existe, deriva a la región del país indicado, donde se puede crear. Tiene límite de tasa.
* Resto de las solicitudes: elige la región por `homeRegion` del token (sin validar la firma, solo para elegir) o,
  sin token, por el prefijo de región del recurso (ticket SSE, tarjeta, viaje, invitación). La validación la hace
  la puerta de entrada de esa región.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re

import jwt
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from comun.infraestructura import db as db_mod
from comun.infraestructura import http as http_mod
from comun.infraestructura.db import BaseDatos
from comun.infraestructura.http import Destino, DestinoNoDisponible
from comun.infraestructura.limites import LimitePorCliente

_PREFIJO = re.compile(r"^([a-z]+-[a-z]+):")
_DEVUELTOS = ("content-type", "etag", "cache-control", "retry-after")
REGION_POR_PAIS = {"AR": "sa-east", "BR": "sa-east", "CL": "sa-east", "UY": "sa-east",
                   "ES": "eu-west", "FR": "eu-west", "DE": "eu-west", "IT": "eu-west"}


class EntradaGlobal:
    def __init__(self, base: BaseDatos, clave_directorio: bytes, clave_interna: str, regiones: dict[str, Destino],
                 proveedores_identidad: dict[str, str], destinos_identidad: dict[str, Destino] | None = None):
        self.base = base
        self.destinos_identidad = destinos_identidad or {}  # proxy /id/<región>/... hacia el proveedor de identidad
        self.clave_directorio = clave_directorio
        self.clave_interna = clave_interna
        self.regiones = regiones
        self.proveedores_identidad = proveedores_identidad
        self.limite = LimitePorCliente(capacidad=10, por_segundo=1)
        base.crear_esquema(["CREATE TABLE IF NOT EXISTS directorio (email_hmac TEXT PRIMARY KEY, region TEXT NOT NULL)"])
        self.app = Starlette(routes=[Route("/login/region", self.region_login, methods=["POST"]),
                                     Route("/internal/directory", self.registrar, methods=["POST"]),
                                     Route("/id/{region}/{camino:path}", self.identidad, methods=["GET", "POST"]),
                                     Route("/{camino:path}", self.enrutar, methods=["GET", "POST", "PATCH", "DELETE"])])

    def _hmac(self, email: str) -> str:
        return hmac.new(self.clave_directorio, email.strip().lower().encode(), hashlib.sha256).hexdigest()

    def registrar_email(self, email: str, region: str):
        with self.base.transaccion() as tx:
            tx.ejecutar("INSERT INTO directorio (email_hmac, region) VALUES (?, ?) "
                        "ON CONFLICT (email_hmac) DO UPDATE SET region = excluded.region", (self._hmac(email), region))

    async def registrar(self, request: Request):
        if not hmac.compare_digest(request.headers.get("x-internal-key", ""), self.clave_interna):
            return JSONResponse({"code": "unauthorized", "message": "No autorizado"}, status_code=401)
        datos = await request.json()
        self.registrar_email(datos["email"], datos["region"])
        return Response(status_code=204)

    async def region_login(self, request: Request):
        cliente = request.client.host if request.client else "desconocido"
        if not self.limite.permitir(cliente):
            return JSONResponse({"code": "rate_limited", "message": "Demasiadas solicitudes"}, status_code=429,
                                headers={"Retry-After": "1"})
        datos = await request.json()
        with self.base.transaccion() as tx:
            fila = tx.uno("SELECT region FROM directorio WHERE email_hmac = ?", (self._hmac(datos.get("email", "")),))
        region = fila["region"] if fila else REGION_POR_PAIS.get(datos.get("country", "").upper(), "sa-east")
        return JSONResponse({"region": region, "identityProvider": self.proveedores_identidad.get(region)})

    async def identidad(self, request: Request):
        destino = self.destinos_identidad.get(request.path_params["region"])
        if destino is None:
            return JSONResponse({"code": "not_found", "message": "Proveedor desconocido"}, status_code=404)
        respuesta = await destino.enviar(request.method, "/" + request.path_params["camino"],
                                         {"content-type": "application/json"}, await request.body())
        return Response(respuesta.cuerpo, status_code=respuesta.estado,
                        headers={"content-type": respuesta.encabezado("content-type") or "application/json"})

    def _region(self, request: Request) -> str | None:
        autorizacion = request.headers.get("authorization", "")
        if autorizacion.lower().startswith("bearer "):
            try:
                return jwt.decode(autorizacion[7:], options={"verify_signature": False}).get("homeRegion")
            except jwt.PyJWTError:
                return None
        candidatos = [request.query_params.get("ticket", "")] + request.url.path.split("/")
        for candidato in candidatos:
            coincidencia = _PREFIJO.match(candidato)
            if coincidencia:
                return coincidencia.group(1)
        return None

    async def enrutar(self, request: Request):
        region = self._region(request)
        if region not in self.regiones:
            return JSONResponse({"code": "unknown_region", "message": "No se pudo elegir la región"}, status_code=400)
        encabezados = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
        ruta = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        try:
            if (request.method, request.url.path) == ("GET", "/panel/events"):
                return await self._flujo(region, ruta, encabezados)  # SSE: se reenvía a medida que llega
            respuesta = await self.regiones[region].enviar(request.method, ruta, encabezados, await request.body())
        except DestinoNoDisponible:
            return JSONResponse({"code": "unavailable", "message": "Región no disponible"}, status_code=503)
        devueltos = {k: v for k, v in respuesta.encabezados if k.lower() in _DEVUELTOS}
        return Response(respuesta.cuerpo, status_code=respuesta.estado, headers=devueltos)

    async def _flujo(self, region: str, ruta: str, encabezados: dict):
        flujo = await self.regiones[region].abrir_flujo("GET", ruta, encabezados)

        async def partes():
            try:
                async for parte in flujo.partes:
                    yield parte
            finally:
                await flujo.cerrar()

        devueltos = {k: v for k, v in flujo.encabezados if k.lower() in _DEVUELTOS}
        return StreamingResponse(partes(), status_code=flujo.estado, headers=devueltos)


def desde_entorno() -> EntradaGlobal:  # pragma: no cover - docker compose
    def pares(variable: str) -> dict[str, str]:  # "sa-east=http://...;eu-west=http://..."
        return dict(par.split("=", 1) for par in filter(None, os.environ.get(variable, "").split(";")))

    regiones = {region: http_mod.abrir(url) for region, url in pares("REGIONES").items()}
    identidad = {region: http_mod.abrir(url) for region, url in pares("IDENTIDAD").items()}
    return EntradaGlobal(db_mod.abrir(os.environ["BASE_DIRECTORIO"], "directorio"),
                         os.environ["CLAVE_DIRECTORIO"].encode(), os.environ["CLAVE_INTERNA_DIRECTORIO"], regiones,
                         {region: f"/id/{region}" for region in identidad}, identidad)
