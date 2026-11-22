"""Características de una oferta para un viajero (ADR-0083, `specs/recommendation.md` §3).

Describen la oferta por lo que el viajero valora, relativo a la reserva cancelada y a su perfil, no por su
identidad: así el modelo funciona con ofertas nuevas y con viajeros sin historial. No incluyen datos personales.
"""
from __future__ import annotations

import statistics
from datetime import datetime
from zoneinfo import ZoneInfo

NOMBRES = ["sesgo", "precio_rel", "duracion_rel", "escalas", "desvio_horario", "mismo_proveedor", "afinidad",
           "preferido"]
# Pesos de la versión inicial del modelo regional, antes de tener feedback (suposición, straw man).
PESOS_INICIALES = [0.0, -0.5, -0.3, -0.3, -0.5, 0.3, 0.3, 0.8]


def _momento(texto: str | None) -> datetime | None:
    return datetime.fromisoformat(texto) if texto else None


def _horas(oferta: dict) -> float | None:
    inicio, fin = _momento(oferta.get("startsAt")), _momento(oferta.get("endsAt"))
    if not inicio or not fin or oferta["type"] == "hotel":
        return None
    return (fin - inicio).total_seconds() / 3600


def contexto(candidatas: list[dict]) -> dict:
    """Valores de referencia del grupo de ofertas: los precios y duraciones se comparan contra la mediana."""
    precios = [o["price"]["amount"] for o in candidatas if o.get("price")]
    horas = [h for h in (_horas(o) for o in candidatas) if h]
    return {"precio": statistics.median(precios) if precios else 0.0,
            "horas": statistics.median(horas) if horas else 0.0}


def vector(oferta: dict, cancelada: dict, perfil: dict, ctx: dict) -> list[float]:
    precio_rel = oferta["price"]["amount"] / ctx["precio"] - 1 if ctx["precio"] else 0.0
    horas = _horas(oferta)
    duracion_rel = horas / ctx["horas"] - 1 if horas and ctx["horas"] else 0.0
    desvio = 0.0
    if oferta.get("startsAt") and cancelada.get("startsAt"):
        desvio = min(abs((_momento(oferta["startsAt"]) - _momento(cancelada["startsAt"])).total_seconds()) / 86400,
                     2.0)
    proveedores = perfil.get("metricas", {}).get("proveedores", {})
    total = sum(proveedores.values())
    afinidad = proveedores.get(oferta["provider"], 0) / total if total else 0.0
    preferido = 1.0 if oferta["provider"] in perfil.get("preferencias", {}).get("preferredProviders", []) else 0.0
    return [1.0, precio_rel, duracion_rel, float(oferta.get("stops", 0)), desvio,
            1.0 if oferta["provider"] == cancelada.get("provider") else 0.0, afinidad, preferido]


def motivos(oferta: dict, x: list[float], perfil: dict) -> list[str]:
    """Códigos para que la app explique la sugerencia en el idioma del viajero (ADR-0065)."""
    codigos = []
    if x[1] < -0.05:
        codigos.append("cheaper")
    elif abs(x[1]) <= 0.05:
        codigos.append("similar_price")
    if x[5]:
        codigos.append("same_provider")
    if x[7]:
        codigos.append("preferred_provider")
    if oferta["type"] != "hotel" and oferta.get("stops", 0) == 0:
        codigos.append("fewer_stops")
    if x[2] < -0.05:
        codigos.append("shorter")
    if x[4] <= 0.125:  # menos de 3 horas de diferencia
        codigos.append("similar_schedule")
    return codigos


def _hora_local(oferta: dict) -> str | None:
    inicio = _momento(oferta.get("startsAt"))
    if not inicio:
        return None
    if oferta.get("timeZone"):
        inicio = inicio.astimezone(ZoneInfo(oferta["timeZone"]))
    return inicio.strftime("%H:%M")


def cumple_limites(oferta: dict, preferencias: dict) -> bool:
    """Filtro previo al ranking: ninguna sugerencia viola un límite explícito del viajero (QA-13)."""
    maximo = preferencias.get("maxPrice")
    if maximo and maximo.get("currency") == oferta["price"]["currency"] and \
            oferta["price"]["amount"] > maximo["amount"]:
        return False
    if preferencias.get("maxStops") is not None and oferta.get("stops", 0) > preferencias["maxStops"]:
        return False
    if oferta["provider"] in preferencias.get("excludedProviders", []):
        return False
    franja = preferencias.get("departureWindow")
    hora = _hora_local(oferta)
    if franja and hora:
        desde, hasta = franja["from"], franja["to"]
        dentro = desde <= hora <= hasta if desde <= hasta else (hora >= desde or hora <= hasta)
        if not dentro:
            return False
    return True
