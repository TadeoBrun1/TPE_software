"""Puerta de entrada regional (ADR-0004, ADR-0047, ADR-0060, ADR-0061, ADR-0062).

Único punto de entrada a la región. Valida tokens y tickets SSE, aplica límites y prioridades, enruta por método y
ruta (y por prefijo de región en las operaciones remotas), reenvía a otra región por el canal entre regiones y
registra en la auditoría los rechazos que ocurren antes de llegar al núcleo. No aplica reglas de dominio: el
permiso sobre un viaje lo decide el núcleo de la región del dueño.

El canal entre regiones se representa con la ruta `/__interregion/...` y una clave compartida que en el
despliegue real es la autenticación mutua mTLS entre puertas.
"""
from __future__ import annotations

import hmac
import json
import os

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from comun.infraestructura import db as db_mod
from comun.infraestructura import http as http_mod
from comun.infraestructura.db import BaseDatos
from comun.infraestructura.http import Destino, DestinoNoDisponible
from comun.infraestructura.reloj import Reloj
from comun.observabilidad import Logger, contexto_correlacion, contexto_traza, continuar_traza, metricas, \
    nuevo_correlation_id
from puerta.auditoria import AuditoriaPuerta
from puerta.autenticacion import Emisores, Identidad, Tickets, TokenInvalido
from puerta.enrutamiento import REENVIABLES, clasificar, es_recurso
from puerta.limites import ControlSobrecarga, LimitePorCliente

PREFIJO_CANAL = "/__interregion"
ENCABEZADOS_REENVIADOS = ("content-type", "if-match", "if-none-match", "idempotency-key")
ENCABEZADOS_DEVUELTOS = ("content-type", "etag", "cache-control", "retry-after")
_REGION = __import__("re").compile(r"^([a-z]+-[a-z]+):")


def _error(estado: int, codigo: str, mensaje: str, encabezados: dict | None = None) -> JSONResponse:
    return JSONResponse({"code": codigo, "message": mensaje}, status_code=estado, headers=encabezados)


class Puerta:
    def __init__(self, region: str, nucleo: Destino, notificador: Destino, ingesta: Destino,
                 otras_regiones: dict[str, Destino], emisores: Emisores, base_auditoria: BaseDatos,
                 clave_puerta: str, clave_canal: str, secreto_tickets: str, reloj: Reloj | None = None,
                 logger: Logger | None = None, limite: LimitePorCliente | None = None,
                 sobrecarga: ControlSobrecarga | None = None):
        self.region = region
        self.nucleo = nucleo
        self.notificador = notificador
        self.ingesta = ingesta
        self.otras_regiones = otras_regiones
        self.emisores = emisores
        self.clave_puerta = clave_puerta
        self.clave_canal = clave_canal
        self.reloj = reloj or Reloj()
        self.logger = logger or Logger("puerta", region)
        self.auditoria = AuditoriaPuerta(base_auditoria, self.reloj, self.logger)
        self.tickets = Tickets(region, secreto_tickets)
        self.limite = limite or LimitePorCliente()
        self.sobrecarga = sobrecarga or ControlSobrecarga()
        self.app = Starlette(routes=[Route("/{camino:path}", self.manejar,
                                           methods=["GET", "POST", "PATCH", "DELETE"])])

    # ------------------------------------------------------------------------------------------ utilidades

    def _rechazo(self, recurso: bool, motivo: str, estado: int, mensaje: str, metodo: str, ruta: str,
                 entry_region: str, identidad: Identidad | None, parametros: dict, encabezados=None):
        """Rechazo previo al núcleo: en rutas de recurso se audita antes de responder (QA-7)."""
        metricas.incrementar(f"puerta_rechazo_{motivo}")
        if recurso and not self.auditoria.rechazo(motivo, metodo, ruta, entry_region, identidad, parametros):
            return _error(503, "audit_unavailable", "No se pudo registrar el acceso", {"Retry-After": "5"})
        return _error(estado, motivo, mensaje, encabezados)

    def _identidad(self, request: Request) -> Identidad:
        autorizacion = request.headers.get("authorization", "")
        if not autorizacion.lower().startswith("bearer "):
            raise TokenInvalido("sin token")
        return self.emisores.validar(autorizacion[7:].strip(), self.reloj.ahora())

    @staticmethod
    def _respuesta(estado: int, encabezados: list[tuple[str, str]], cuerpo: bytes, sin_cache: bool = False):
        devueltos = {k: v for k, v in encabezados if k.lower() in ENCABEZADOS_DEVUELTOS}
        if sin_cache:
            devueltos["Cache-Control"] = "no-store"  # la puerta no guarda ni registra respuestas compartidas
        return Response(cuerpo, status_code=estado, headers=devueltos)

    # ------------------------------------------------------------------------------------------ manejo

    async def manejar(self, request: Request):
        metodo, camino = request.method, request.url.path
        contexto_traza.set(continuar_traza(request.headers.get("traceparent")))
        contexto_correlacion.set(request.headers.get("x-correlation-id") or nuevo_correlation_id())
        entry_region, via_canal = self.region, False
        if camino.startswith(PREFIJO_CANAL + "/"):
            if not hmac.compare_digest(request.headers.get("x-inter-region-key", ""), self.clave_canal):
                return _error(401, "unauthorized", "Canal entre regiones no autenticado")
            via_canal, camino = True, camino[len(PREFIJO_CANAL):]
            entry_region = request.headers.get("x-entry-region", "")
        ruta, parametros = clasificar(metodo, camino)
        recurso = ruta.recurso if ruta else es_recurso(camino)
        plantilla = ruta.plantilla if ruta else camino
        if ruta is None or (via_canal and (metodo, ruta.plantilla) not in REENVIABLES):
            return self._rechazo(recurso, "not_found", 404, "Ruta inexistente", metodo, plantilla, entry_region, None,
                                 parametros)
        cuerpo = await request.body()
        if ruta.destino == "ingesta":  # los proveedores se autentican con su firma, que verifica el receptor
            try:
                respuesta = await self.ingesta.enviar(metodo, camino, self._reenviados(request), cuerpo)
            except DestinoNoDisponible:  # el proveedor reintenta el aviso; la reconciliación cubre si no lo hace
                return _error(503, "unavailable", "Ingesta no disponible", {"Retry-After": "30"})
            return self._respuesta(respuesta.estado, respuesta.encabezados, respuesta.cuerpo)
        if ruta.destino == "notificador":
            return await self._eventos(request)

        try:
            identidad = self._identidad(request)
        except TokenInvalido as error:
            self.logger.info("token_rechazado", motivo=str(error), ruta=plantilla)
            return self._rechazo(recurso, "unauthenticated", 401, "No autenticado", metodo, plantilla, entry_region,
                                 None, parametros)
        if (not via_canal and identidad.region != self.region) or (via_canal and identidad.region != entry_region):
            # Un token de otra región solo se acepta por el canal entre regiones (ADR-0060).
            return self._rechazo(recurso, "unauthenticated", 401, "El token no corresponde a esta región", metodo,
                                 plantilla, entry_region, None, parametros)
        if not self.limite.permitir(f"{identidad.region}:{identidad.user_id}"):
            return self._rechazo(recurso, "rate_limited", 429, "Demasiadas solicitudes", metodo, plantilla,
                                 entry_region, identidad, parametros, {"Retry-After": "1"})
        if ruta.destino == "puerta":
            ticket, vence = self.tickets.emitir(identidad, self.reloj.ahora())
            return JSONResponse({"ticket": ticket, "expiresAt": vence}, status_code=201)

        destino = self.region
        if ruta.destino == "prefijo":
            prefijo = _REGION.match(parametros.get(ruta.parametro, ""))
            destino = prefijo.group(1) if prefijo else None
            if destino is None or (destino != self.region and destino not in self.otras_regiones) or \
                    (via_canal and destino != self.region):  # un solo salto entre puertas
                return self._rechazo(recurso, "bad_region", 404, "No existe", metodo, plantilla, entry_region,
                                     identidad, parametros)
        if not self.sobrecarga.admitir(ruta.prioridad):
            metricas.incrementar(f"puerta_descarte_prioridad_{ruta.prioridad}")
            return _error(503, "overloaded", "Sobrecarga temporal", {"Retry-After": "10"})

        sin_cache = (metodo, ruta.plantilla) == ("GET", "/shared/trips/{tripId}")
        if destino != self.region:
            encabezados = {**self._reenviados(request), "Authorization": request.headers["authorization"],
                           "X-Inter-Region-Key": self.clave_canal, "X-Entry-Region": self.region, "X-Hop": "1",
                           "X-Correlation-Id": contexto_correlacion.get(), "traceparent": contexto_traza.get()}
            try:
                respuesta = await self.otras_regiones[destino].enviar(metodo, PREFIJO_CANAL + camino, encabezados,
                                                                      cuerpo)
            except DestinoNoDisponible:
                return self._rechazo(recurso, "owner_region_unavailable", 503, "La región del dueño no responde",
                                     metodo, plantilla, entry_region, identidad, parametros, {"Retry-After": "30"})
            metricas.incrementar("puerta_reenvio_entre_regiones")
            return self._respuesta(respuesta.estado, respuesta.encabezados, respuesta.cuerpo, sin_cache)

        encabezados = {**self._reenviados(request), **self._principal(identidad, entry_region)}
        with self.sobrecarga:
            try:
                respuesta = await self.nucleo.enviar(metodo, camino + (f"?{request.url.query}" if request.url.query
                                                                        else ""), encabezados, cuerpo)
            except DestinoNoDisponible:
                return _error(503, "unavailable", "Núcleo no disponible", {"Retry-After": "5"})
        return self._respuesta(respuesta.estado, respuesta.encabezados, respuesta.cuerpo, sin_cache)

    def _reenviados(self, request: Request) -> dict:
        encabezados = {k: v for k, v in request.headers.items() if k.lower() in ENCABEZADOS_REENVIADOS}
        if "x-provider-signature" in request.headers:
            encabezados["X-Provider-Signature"] = request.headers["x-provider-signature"]
        return encabezados

    def _principal(self, identidad: Identidad, entry_region: str) -> dict:
        encabezados = {"X-Gateway-Key": self.clave_puerta, "X-Principal-Region": identidad.region,
                       "X-Principal-User": identidad.user_id, "X-Principal-Issuer": identidad.issuer,
                       "X-Entry-Region": entry_region, "X-Correlation-Id": contexto_correlacion.get(),
                       "traceparent": contexto_traza.get()}
        if identidad.email_hmac:
            encabezados["X-Principal-Email-Hmac"] = identidad.email_hmac
        return encabezados

    async def _eventos(self, request: Request):
        """GET /panel/events?ticket=...: valida el ticket y abre el flujo SSE con el notificador."""
        try:
            identidad = self.tickets.validar(request.query_params.get("ticket", ""), self.reloj.ahora())
        except TokenInvalido:
            return _error(401, "unauthorized", "Ticket inválido o vencido")
        try:
            flujo = await self.notificador.abrir_flujo("GET", "/panel/events", self._principal(identidad, self.region))
        except DestinoNoDisponible:
            return _error(503, "unavailable", "Notificador no disponible", {"Retry-After": "5"})

        async def partes():
            try:
                async for parte in flujo.partes:
                    yield parte
            finally:
                await flujo.cerrar()

        return StreamingResponse(partes(), status_code=flujo.estado, media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store"})


def desde_entorno() -> Puerta:  # pragma: no cover - docker compose
    import urllib.request

    region = os.environ["REGION"]
    emisores = Emisores()
    for definicion in os.environ["EMISORES"].split(";"):  # iss,region,url_jwks;...
        iss, region_emisor, url = definicion.split(",")
        with urllib.request.urlopen(url, timeout=10) as respuesta:
            emisores.registrar(iss, region_emisor, json.loads(respuesta.read()))
    otras = {par.split("=")[0]: http_mod.abrir(par.split("=")[1])
             for par in filter(None, os.environ.get("OTRAS_REGIONES", "").split(";"))}
    return Puerta(region, http_mod.abrir(os.environ["URL_NUCLEO"]), http_mod.abrir(os.environ["URL_NOTIFICADOR"]),
                  http_mod.abrir(os.environ["URL_INGESTA"]), otras, emisores,
                  db_mod.abrir(os.environ["BASE_AUDITORIA"], f"{region}-auditoria"), os.environ["CLAVE_PUERTA"],
                  os.environ["CLAVE_CANAL"], os.environ["SECRETO_TICKETS"])
