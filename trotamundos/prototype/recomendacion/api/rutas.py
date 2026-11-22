"""API de sugerencias y preferencias del proceso de recomendación (ADR-0084, `itinerary-api.v1.yaml` 0.4.0).

Como el núcleo, solo acepta solicitudes de la puerta de entrada de su región, que valida el token y le pasa el
principal en encabezados internos. Todas las operaciones son del propio viajero (táctica *autorizar actores*): un
viaje ajeno o inexistente responde como un viaje sin sugerencias (`searchStatus` `none`), sin revelar si existe.
"""
from __future__ import annotations

import hmac
import json
from functools import wraps

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from comun.infraestructura.db import ErrorBloqueo
from comun.observabilidad import contexto_correlacion, contexto_traza, continuar_traza, metricas, nuevo_correlation_id
from contratos.esquemas import ContratoInvalido, validar_api
from recomendacion.sugerencias.servicio import EstadoInvalido, NoEncontrada


def _error(estado: int, codigo: str, mensaje: str, encabezados: dict | None = None) -> JSONResponse:
    return JSONResponse({"code": codigo, "message": mensaje}, status_code=estado, headers=encabezados)


def endpoint(funcion):
    @wraps(funcion)
    def envoltura(request: Request):
        app = request.app.state.recomendacion
        contexto_traza.set(continuar_traza(request.headers.get("traceparent")))
        contexto_correlacion.set(request.headers.get("x-correlation-id") or nuevo_correlation_id())
        if not hmac.compare_digest(request.headers.get("x-gateway-key", ""), app.clave_puerta):
            return _error(401, "unauthorized", "No autenticado")
        region, user_id = request.headers.get("x-principal-region"), request.headers.get("x-principal-user")
        if not user_id or region != app.region:
            return _error(401, "unauthorized", "El token no corresponde a esta región")
        with app.base.transaccion() as tx:
            if app.perfiles.eliminada(tx, user_id):  # token vigente de una cuenta eliminada (ADR-0085)
                return _error(401, "account_deleted", "La cuenta fue eliminada")
        try:
            return funcion(request, app, user_id)
        except ContratoInvalido as e:
            return _error(400, "invalid_request", str(e))
        except ErrorBloqueo:
            return _error(503, "unavailable", "Intente de nuevo", {"Retry-After": "1"})
    return envoltura


def _cuerpo(request: Request) -> dict:
    try:
        return json.loads(getattr(request.state, "cuerpo", b"") or b"{}")
    except ValueError as e:
        raise ContratoInvalido("cuerpo", ["JSON inválido"]) from e


def _respuesta(esquema: str, valor: dict, estado: int = 200) -> JSONResponse:
    validar_api(esquema, valor)  # la respuesta también cumple el contrato
    return JSONResponse(valor, status_code=estado, headers={"Cache-Control": "no-store"})


@endpoint
def sugerencias_del_viaje(request: Request, app, user_id: str):
    trip_id = request.path_params["tripId"]
    if not trip_id.startswith(f"{app.region}:"):
        return _error(404, "not_found", "No existe")
    return _respuesta("SuggestionList", app.sugerencias.listar(user_id, trip_id))


@endpoint
def feedback(request: Request, app, user_id: str):
    datos = _cuerpo(request)
    validar_api("SuggestionFeedback", datos)
    if datos["action"] == "adjust" and not datos.get("preferences"):
        return _error(400, "invalid_request", "adjust necesita preferences")
    try:
        estado, valor = app.sugerencias.feedback(user_id, request.path_params["suggestionId"], datos["action"],
                                                 datos.get("reason"), datos.get("preferences"))
    except NoEncontrada:
        return _error(404, "not_found", "No existe")
    except EstadoInvalido as e:
        return _error(409, "conflict", f"La sugerencia ya está {e}")
    return _respuesta("SuggestionAccepted" if estado == 202 else "SuggestionList", valor, estado)


@endpoint
def leer_preferencias(request: Request, app, user_id: str):
    return _respuesta("RecommendationPreferences", app.perfiles.preferencias_api(user_id))


@endpoint
def cambiar_preferencias(request: Request, app, user_id: str):
    datos = _cuerpo(request)
    validar_api("RecommendationPreferences", datos)
    valor = app.perfiles.cambiar_preferencias(user_id, datos)
    app.logger.info("preferencias_cambiadas", activada=valor["enabled"])
    metricas.incrementar("recomendacion_preferencias_cambiadas")
    return _respuesta("RecommendationPreferences", valor)


@endpoint
def borrar_perfil(request: Request, app, user_id: str):
    app.perfiles.borrar(user_id)
    app.logger.info("perfil_borrado")
    metricas.incrementar("recomendacion_perfil_borrado")
    return Response(status_code=204)


def crear_app(recomendacion) -> Starlette:
    async def estado(request: Request):
        return JSONResponse(metricas.resumen())

    def asincrona(funcion):
        async def manejar(request: Request):
            request.state.cuerpo = await request.body()
            return await run_in_threadpool(funcion, request)
        return manejar

    app = Starlette(routes=[
        Route("/trips/{tripId}/suggestions", asincrona(sugerencias_del_viaje), methods=["GET"]),
        Route("/suggestions/{suggestionId}/feedback", asincrona(feedback), methods=["POST"]),
        Route("/recommendations/preferences", asincrona(leer_preferencias), methods=["GET"]),
        Route("/recommendations/preferences", asincrona(cambiar_preferencias), methods=["PUT"]),
        Route("/recommendations/profile", asincrona(borrar_perfil), methods=["DELETE"]),
        Route("/metrics", estado, methods=["GET"]),
    ])
    app.state.recomendacion = recomendacion
    return app
