"""Endpoints de simulación para la demo con docker compose (no forman parte del contrato de la API).

Reemplazan lo que el prototipo no implementa: la vinculación de cuentas (RF-02) y los sistemas externos. Solo se
exponen dentro de la red de docker y piden la clave de administración `X-Admin-Key`.
"""
from __future__ import annotations

import hmac

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


def _autorizado(request: Request, clave: str) -> bool:
    return bool(clave) and hmac.compare_digest(request.headers.get("x-admin-key", ""), clave)


def rutas_nucleo(nucleo, clave: str) -> list[Route]:
    async def vinculacion(request: Request):
        if not _autorizado(request, clave):
            return JSONResponse({"code": "unauthorized"}, status_code=401)
        datos = await request.json()
        nucleo.registrar_vinculacion(datos["connectionId"], datos["userId"], datos["providerId"])
        return JSONResponse({"ok": True})

    async def tarea_diaria(request: Request):
        if not _autorizado(request, clave):
            return JSONResponse({"code": "unauthorized"}, status_code=401)
        return JSONResponse(nucleo.tarea_diaria())

    return [Route("/simulacion/vinculaciones", vinculacion, methods=["POST"]),
            Route("/simulacion/tarea-diaria", tarea_diaria, methods=["POST"])]


def rutas_ingesta(ingesta, fuentes: dict, clave: str) -> list[Route]:
    async def vinculacion(request: Request):
        if not _autorizado(request, clave):
            return JSONResponse({"code": "unauthorized"}, status_code=401)
        d = await request.json()
        ingesta.vinculaciones.registrar(d["connectionId"], d["userId"], d["homeRegion"], d["providerId"], d["fuente"],
                                        remitentes=d.get("remitentes"), secreto_avisos=d.get("secretoAvisos", ""))
        return JSONResponse({"ok": True})

    async def fuente(request: Request):
        if not _autorizado(request, clave):
            return JSONResponse({"code": "unauthorized"}, status_code=401)
        d = await request.json()
        nombre = request.path_params["fuente"]
        if nombre == "correo":
            fuentes["buzon"].recibir(d["connectionId"], d["from"], d["body"])
        elif nombre in ("hotel", "aerolinea"):
            fuentes[nombre].publicar(d["connectionId"], d["reserva"])
        else:
            return JSONResponse({"code": "not_found"}, status_code=404)
        return JSONResponse({"ok": True})

    return [Route("/simulacion/vinculaciones", vinculacion, methods=["POST"]),
            Route("/simulacion/{fuente}", fuente, methods=["POST"])]


def rutas_recomendacion(recomendacion, clave: str) -> list[Route]:
    """Iteración 5: falla inyectada en una API de búsqueda y entrenamiento a pedido (sin esperar a la hora diaria)."""
    async def falla(request: Request):
        if not _autorizado(request, clave):
            return JSONResponse({"code": "unauthorized"}, status_code=401)
        d = await request.json()
        api = recomendacion.apis.get(request.path_params["proveedor"])
        if api is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        from simuladores.proveedores import ErrorTemporal

        for _ in range(int(d.get("veces", 1))):
            api.fallar_proxima(ErrorTemporal("falla simulada"))
        return JSONResponse({"ok": True})

    async def entrenar(request: Request):
        if not _autorizado(request, clave):
            return JSONResponse({"code": "unauthorized"}, status_code=401)
        return JSONResponse(recomendacion.entrenar())

    return [Route("/simulacion/busqueda/{proveedor}/falla", falla, methods=["POST"]),
            Route("/simulacion/entrenamiento", entrenar, methods=["POST"])]
