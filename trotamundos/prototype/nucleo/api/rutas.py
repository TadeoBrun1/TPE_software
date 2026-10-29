"""API de itinerarios del núcleo (`specs/openapi/itinerary-api.v1.yaml`).

El núcleo solo acepta solicitudes de la puerta de entrada de su región (táctica *limitar el acceso*): la puerta
valida el token y le pasa el principal verificado en encabezados internos. Los endpoints con acceso a la base son
funciones sincrónicas; Starlette las ejecuta en un pool de hilos.
"""
from __future__ import annotations

import base64
import hmac
import json
from functools import wraps

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from comun.infraestructura.db import ErrorBloqueo, con_reintentos
from comun.infraestructura.reloj import iso
from comun.observabilidad import contexto_correlacion, contexto_traza, continuar_traza, metricas, nuevo_correlation_id
from contratos.esquemas import ContratoInvalido, validar_api
from nucleo.auditoria.registro import AuditoriaNoDisponible
from nucleo.comparticion.servicio import Principal
from nucleo.datos.ruteo import IdentificadorInvalido
from nucleo.esquemas.registro import DetallesInvalidos
from nucleo.panel import proyector
from nucleo.panel.unidad import UnidadDeCambio
from nucleo.reservas import manuales
from nucleo.reservas.manuales import ErrorDominio
from nucleo.reservas.modelo import reserva_a_api, viaje_a_api
from nucleo.usuarios import perfil
from nucleo.viajes import ciclo_vida

ENCABEZADOS_COMPARTIDOS = {"Cache-Control": "no-store"}


def error(estado: int, codigo: str, mensaje: str, encabezados: dict | None = None) -> JSONResponse:
    return JSONResponse({"code": codigo, "message": mensaje}, status_code=estado, headers=encabezados)


def principal_de(request: Request, nucleo) -> Principal | None:
    clave = request.headers.get("x-gateway-key", "")
    if not hmac.compare_digest(clave, nucleo.clave_puerta):
        return None
    region, user_id = request.headers.get("x-principal-region"), request.headers.get("x-principal-user")
    if not region or not user_id:
        return None
    return Principal(region=region, user_id=user_id, issuer=request.headers.get("x-principal-issuer"),
                     email_hmac=request.headers.get("x-principal-email-hmac"),
                     entry_region=request.headers.get("x-entry-region", nucleo.region))


def endpoint(ruta: str, local: bool = True):
    """Envuelve un handler: verifica la puerta, fija la correlación y traduce errores a respuestas del contrato.

    `local=True` exige que el principal sea de esta región (operaciones del usuario sobre lo propio).
    """
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(request: Request):
            nucleo = request.app.state.nucleo
            contexto_traza.set(continuar_traza(request.headers.get("traceparent")))
            contexto_correlacion.set(request.headers.get("x-correlation-id") or nuevo_correlation_id())
            principal = principal_de(request, nucleo)
            if principal is None:
                return error(401, "unauthorized", "No autenticado")
            if local and principal.region != nucleo.region:
                return error(401, "unauthorized", "El token no corresponde a esta región")
            try:
                with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
                    if principal.region == nucleo.region:
                        perfil.asegurar(tx, principal.user_id, nucleo.region, iso(nucleo.reloj.ahora()))
                return funcion(request, nucleo, principal, ruta)
            except ErrorDominio as e:
                return error(e.estado, e.codigo, e.mensaje)
            except (ContratoInvalido, DetallesInvalidos) as e:
                return error(400, "invalid_request", str(e))
            except AuditoriaNoDisponible:
                return error(503, "audit_unavailable", "No se pudo registrar el acceso", {"Retry-After": "5"})
            except ErrorBloqueo:
                return error(503, "busy", "Cambios concurrentes del mismo usuario; reintentar", {"Retry-After": "1"})
            except ConnectionError:
                return error(503, "unavailable", "Nodo de la base no disponible", {"Retry-After": "30"})
        return envoltura
    return decorador


def _json(request_body: bytes, esquema: str) -> dict:
    try:
        datos = json.loads(request_body or b"null")
    except json.JSONDecodeError as e:
        raise ErrorDominio(400, "invalid_json", str(e))
    validar_api(esquema, datos)
    return datos


def _cuerpo(request: Request) -> bytes:
    return request.state.cuerpo if hasattr(request.state, "cuerpo") else b""


def _cambiar(nucleo, principal: Principal, operacion):
    """Transacción local del usuario con bloqueo por usuario, reintentos y panel coherente."""
    def transaccion():
        with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
            unidad = UnidadDeCambio(tx, nucleo.region, principal.user_id, nucleo.reloj)
            resultado = operacion(tx, unidad)
            unidad.confirmar()
            return resultado
    return con_reintentos(transaccion)


# ------------------------------------------------------------------------------------------ panel

@endpoint("/panel")
def obtener_panel(request, nucleo, principal, ruta):
    with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
        documento = proyector.leer(tx, principal.user_id) or \
            {"panelVersion": 0, "trips": [], "unassignedBookings": [], "notices": []}
    etag = f'"{documento["panelVersion"]}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return JSONResponse(documento, headers={"ETag": etag})


@endpoint("/telemetry/panel-shown")
def informar_panel_mostrado(request, nucleo, principal, ruta):
    datos = json.loads(_cuerpo(request) or b"{}")
    if not isinstance(datos.get("panelVersion"), int) or not datos.get("shownAt"):
        raise ErrorDominio(400, "invalid_request", "panelVersion y shownAt son obligatorios")
    with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
        tx.ejecutar("INSERT INTO telemetria_panel (principal, panel_version, mostrado, correlation_ids, recibido) "
                    "VALUES (?, ?, ?, ?, ?) ON CONFLICT (principal, panel_version) DO NOTHING",
                    (f"{principal.region}:{principal.user_id}", datos["panelVersion"], datos["shownAt"],
                     json.dumps(datos.get("correlationIds", [])), iso(nucleo.reloj.ahora())))
    metricas.incrementar("telemetria_panel_mostrado")
    return Response(status_code=202)


# ------------------------------------------------------------------------------------------ viajes

@endpoint("/trips/archived")
def listar_archivados(request, nucleo, principal, ruta):
    limite = max(1, min(50, int(request.query_params.get("limit", 20))))
    desde = int(base64.urlsafe_b64decode(request.query_params["cursor"]).decode()) if "cursor" in request.query_params else 0
    with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
        viajes = tx.todos("SELECT * FROM viajes WHERE user_id = ? AND estado = 'archivado' "
                          "ORDER BY archivado_en DESC, trip_id LIMIT ? OFFSET ?", (principal.user_id, limite + 1, desde))
        datos = [viaje_a_api(v, tx.todos("SELECT * FROM reservas WHERE trip_id = ? ORDER BY inicio", (v["trip_id"],)))
                 for v in viajes[:limite]]
    respuesta = {"trips": datos}
    if len(viajes) > limite:
        respuesta["nextCursor"] = base64.urlsafe_b64encode(str(desde + limite).encode()).decode()
    return JSONResponse(respuesta)


@endpoint("/trips/{tripId}", local=False)
def obtener_viaje(request, nucleo, principal, ruta):
    trip_id = request.path_params["tripId"]
    nucleo.comparticion.viaje_del_dueno(principal, trip_id, "GET", ruta)
    with nucleo.ruteo.nodo_de_id(trip_id).transaccion() as tx:
        viaje = tx.uno("SELECT * FROM viajes WHERE trip_id = ?", (trip_id,))
        reservas = tx.todos("SELECT * FROM reservas WHERE trip_id = ? ORDER BY inicio", (trip_id,))
    return JSONResponse(viaje_a_api(viaje, reservas))


def _cambiar_estado_viaje(request, nucleo, principal, ruta, accion):
    trip_id = request.path_params["tripId"]
    nucleo.comparticion.viaje_del_dueno(principal, trip_id, "POST", ruta)

    def operacion(tx, unidad):
        viaje = tx.uno("SELECT * FROM viajes WHERE trip_id = ?", (trip_id,))
        hoy = nucleo.reloj.hoy()
        if accion == "archivar":
            if viaje["estado"] == "archivado":
                raise ErrorDominio(409, "already_archived", "El viaje ya está archivado")
            ciclo_vida.archivar(tx, unidad, viaje, hoy)
        else:
            if viaje["estado"] != "archivado":
                raise ErrorDominio(409, "not_archived", "El viaje no está archivado")
            ciclo_vida.reactivar(tx, unidad, viaje, hoy, a_mano=True)
        return trip_id

    _cambiar(nucleo, principal, operacion)
    with nucleo.ruteo.nodo_de_id(trip_id).transaccion() as tx:
        viaje = tx.uno("SELECT * FROM viajes WHERE trip_id = ?", (trip_id,))
        reservas = tx.todos("SELECT * FROM reservas WHERE trip_id = ? ORDER BY inicio", (trip_id,))
    return JSONResponse(viaje_a_api(viaje, reservas))


@endpoint("/trips/{tripId}/archive", local=False)
def archivar_viaje(request, nucleo, principal, ruta):
    return _cambiar_estado_viaje(request, nucleo, principal, ruta, "archivar")


@endpoint("/trips/{tripId}/reactivate", local=False)
def reactivar_viaje(request, nucleo, principal, ruta):
    return _cambiar_estado_viaje(request, nucleo, principal, ruta, "reactivar")


# ------------------------------------------------------------------------------------------ reservas

def _idempotente(nucleo, principal, clave: str | None, operacion: str, ejecutar):
    if not clave:
        raise ErrorDominio(400, "idempotency_key_required", "Falta Idempotency-Key")
    with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
        previa = tx.uno("SELECT estado, respuesta FROM idempotencia WHERE user_id = ? AND clave = ?",
                        (principal.user_id, clave))
    if previa:
        return previa["estado"], json.loads(previa["respuesta"])
    estado, cuerpo = ejecutar()
    with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
        tx.ejecutar("INSERT INTO idempotencia (user_id, clave, operacion, estado, respuesta, creado) "
                    "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (user_id, clave) DO NOTHING",
                    (principal.user_id, clave, operacion, estado, json.dumps(cuerpo), iso(nucleo.reloj.ahora())))
    return estado, cuerpo


@endpoint("/bookings")
def crear_reserva(request, nucleo, principal, ruta):
    datos = _json(_cuerpo(request), "BookingInput")

    def ejecutar():
        booking_id = _cambiar(nucleo, principal, lambda tx, unidad: manuales.crear(
            tx, unidad, nucleo.ruteo, nucleo.esquemas, principal.user_id, datos))
        with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
            return 201, reserva_a_api(tx.uno("SELECT * FROM reservas WHERE booking_id = ?", (booking_id,)))

    estado, cuerpo = _idempotente(nucleo, principal, request.headers.get("idempotency-key"), "createBooking", ejecutar)
    return JSONResponse(cuerpo, status_code=estado, headers={"ETag": f'"{cuerpo["version"]}"'})


def _reserva_ajena(request, nucleo, principal, ruta, metodo):
    """Una reserva de otra partición o de otro usuario se rechaza y se audita (endpoint del dueño)."""
    booking_id = request.path_params["bookingId"]
    try:
        nodo = nucleo.ruteo.nodo_de_id(booking_id)
    except IdentificadorInvalido:
        nucleo.comparticion.rechazar_ajeno(principal, metodo, ruta, booking_id=booking_id, existe=False)
    with nodo.transaccion() as tx:
        reserva = tx.uno("SELECT user_id, trip_id FROM reservas WHERE booking_id = ?", (booking_id,))
    if reserva is None:
        if nodo is not nucleo.ruteo.nodo(principal.user_id):
            nucleo.comparticion.rechazar_ajeno(principal, metodo, ruta, booking_id=booking_id, existe=False)
        raise ErrorDominio(404, "not_found", "No existe o no pertenece al usuario")
    if reserva["user_id"] != principal.user_id:
        nucleo.comparticion.rechazar_ajeno(principal, metodo, ruta, trip_id=reserva["trip_id"], booking_id=booking_id)
    return booking_id


@endpoint("/bookings/{bookingId}")
def cambiar_reserva(request, nucleo, principal, ruta):
    booking_id = _reserva_ajena(request, nucleo, principal, ruta, request.method)
    version = request.headers.get("if-match")
    if request.method == "DELETE":
        _cambiar(nucleo, principal, lambda tx, unidad: manuales.borrar(tx, unidad, principal.user_id, booking_id,
                                                                         version))
        return Response(status_code=204)
    datos = _json(_cuerpo(request), "BookingPatch")
    _cambiar(nucleo, principal, lambda tx, unidad: manuales.editar(
        tx, unidad, nucleo.ruteo, nucleo.esquemas, principal.user_id, booking_id, version, datos))
    with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
        reserva = reserva_a_api(tx.uno("SELECT * FROM reservas WHERE booking_id = ?", (booking_id,)))
    return JSONResponse(reserva, headers={"ETag": f'"{reserva["version"]}"'})


# ------------------------------------------------------------------------------------------ compartición

@endpoint("/trips/{tripId}/shares", local=False)
def invitaciones(request, nucleo, principal, ruta):
    trip_id = request.path_params["tripId"]
    if request.method == "GET":
        return JSONResponse({"shares": nucleo.comparticion.listar(principal, trip_id, "GET", ruta)})
    datos = json.loads(_cuerpo(request) or b"{}")
    if not isinstance(datos.get("email"), str) or "@" not in datos["email"] or set(datos) != {"email"}:
        raise ErrorDominio(400, "invalid_request", "Se espera {\"email\": ...}")

    def ejecutar():
        return 201, nucleo.comparticion.invitar(principal, trip_id, datos["email"], "POST", ruta)

    estado, cuerpo = _idempotente(nucleo, principal, request.headers.get("idempotency-key"), "createTripShare",
                                  ejecutar) if principal.region == nucleo.region else ejecutar()
    return JSONResponse(cuerpo, status_code=estado)


@endpoint("/trips/{tripId}/shares/{shareId}", local=False)
def quitar_invitacion(request, nucleo, principal, ruta):
    nucleo.comparticion.quitar(principal, request.path_params["tripId"], request.path_params["shareId"], "DELETE", ruta)
    return Response(status_code=204)


@endpoint("/shares/{shareId}/accept", local=False)
def aceptar_invitacion(request, nucleo, principal, ruta):
    datos = json.loads(_cuerpo(request) or b"{}")
    referencia = nucleo.comparticion.aceptar(principal, request.path_params["shareId"], datos.get("secret", ""),
                                             "POST", ruta)
    return JSONResponse(referencia)


@endpoint("/shared/trips")
def referencias(request, nucleo, principal, ruta):
    with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
        if request.method == "GET":
            return JSONResponse({"trips": perfil.listar_referencias(tx, principal.user_id)})
        datos = _json(_cuerpo(request), "SharedTripRef")
        return JSONResponse(perfil.agregar_referencia(tx, principal.user_id, datos["tripId"], datos["acceptedAt"]))


@endpoint("/shared/trips/{tripId}", local=False)
def viaje_compartido(request, nucleo, principal, ruta):
    trip_id = request.path_params["tripId"]
    if request.method == "DELETE":
        if principal.region != nucleo.region:
            raise ErrorDominio(401, "unauthorized", "El marcador se borra en la región del lector")
        with nucleo.ruteo.nodo(principal.user_id).transaccion() as tx:
            perfil.borrar_referencia(tx, principal.user_id, trip_id)
        return Response(status_code=204)
    datos = nucleo.comparticion.leer(principal, trip_id, "GET", ruta)
    return JSONResponse(datos, headers=ENCABEZADOS_COMPARTIDOS)


# ------------------------------------------------------------------------------------------ operación

async def metricas_proceso(request):
    return JSONResponse(metricas.resumen())


def _ruta(path, funcion, metodos):
    async def asincrona(request: Request):
        request.state.cuerpo = await request.body()
        return await run_in_threadpool(funcion, request)
    return Route(path, asincrona, methods=metodos)


def crear_app(nucleo) -> Starlette:
    app = Starlette(routes=[
        _ruta("/panel", obtener_panel, ["GET"]),
        _ruta("/telemetry/panel-shown", informar_panel_mostrado, ["POST"]),
        _ruta("/trips/archived", listar_archivados, ["GET"]),
        _ruta("/trips/{tripId}", obtener_viaje, ["GET"]),
        _ruta("/trips/{tripId}/archive", archivar_viaje, ["POST"]),
        _ruta("/trips/{tripId}/reactivate", reactivar_viaje, ["POST"]),
        _ruta("/trips/{tripId}/shares", invitaciones, ["GET", "POST"]),
        _ruta("/trips/{tripId}/shares/{shareId}", quitar_invitacion, ["DELETE"]),
        _ruta("/shares/{shareId}/accept", aceptar_invitacion, ["POST"]),
        _ruta("/shared/trips", referencias, ["GET", "POST"]),
        _ruta("/shared/trips/{tripId}", viaje_compartido, ["GET", "DELETE"]),
        _ruta("/bookings", crear_reserva, ["POST"]),
        _ruta("/bookings/{bookingId}", cambiar_reserva, ["PATCH", "DELETE"]),
        Route("/metrics", metricas_proceso, methods=["GET"]),
    ])
    app.state.nucleo = nucleo
    return app
