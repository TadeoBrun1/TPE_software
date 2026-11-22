"""Puerto de búsqueda de ofertas y adaptadores por proveedor (ADR-0082, Ports and Adapters).

El puerto recibe una consulta normalizada y devuelve ofertas normalizadas según `specs/offer-search.md`. Cada
adaptador traduce el formato propio de su proveedor y no inventa datos que el proveedor no da. Los errores se
clasifican como en ADR-0023 (temporal, cuota, autorización, datos).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from simuladores.proveedores import ErrorAutorizacion, ErrorCuota, ErrorTemporal  # noqa: F401 - clasificación

TIPOS_TRANSPORTE = ("flight", "train", "bus", "car")


@dataclass(frozen=True)
class Consulta:
    type: str
    location: str
    date: str
    arrivalLocation: str | None = None
    nights: int | None = None
    currency: str = "EUR"

    @property
    def clave(self) -> str:
        """Clave de búsqueda (sin datos del viajero): se agrupan y cachean las consultas iguales."""
        return "|".join(str(v) for v in (self.type, self.location, self.arrivalLocation or "", self.date,
                                          self.nights or "", self.currency))


class PuertoBusqueda:
    proveedor: str
    tipos: tuple[str, ...]
    limite_por_minuto: int

    def buscar(self, consulta: Consulta) -> list[dict]:  # pragma: no cover - interfaz
        raise NotImplementedError


def _con_zona(local: str, zona: str) -> str:
    return datetime.fromisoformat(local).replace(tzinfo=ZoneInfo(zona)).isoformat()


def _valida(oferta: dict) -> bool:
    """Una oferta sin precio, sin enlace o sin inicio se descarta (error de datos)."""
    return bool(oferta.get("price") and oferta.get("offerUrl") and oferta.get("startsAt"))


class AdaptadorBusquedaHotel(PuertoBusqueda):
    tipos = ("hotel",)

    def __init__(self, api, limite_por_minuto: int | None = None):
        self.api = api
        self.proveedor = api.proveedor
        self.limite_por_minuto = limite_por_minuto or api.limite_por_minuto

    def buscar(self, consulta: Consulta) -> list[dict]:
        crudas = self.api.buscar(consulta.location, consulta.date, consulta.nights or 1, consulta.currency)
        ofertas = []
        for c in crudas:
            zona = c.get("timeZone")
            entrada = f"{c['checkIn']}T{c.get('checkInTime', '15:00')}"
            salida = (date.fromisoformat(c["checkIn"]) + timedelta(days=c["nights"])).isoformat() + "T11:00"
            oferta = {"offerId": c["hotelOfferId"], "type": "hotel", "provider": self.proveedor,
                      "startsAt": _con_zona(entrada, zona) if zona else None,
                      "endsAt": _con_zona(salida, zona) if zona else None, "timeZone": zona,
                      "location": c["city"], "stops": 0,
                      "price": {"amount": c["total"]["value"], "currency": c["total"]["currencyCode"]},
                      "offerUrl": c.get("bookingLink"), "expiresAt": c.get("validUntil")}
            oferta = {k: v for k, v in oferta.items() if v is not None}
            if _valida(oferta):
                ofertas.append(oferta)
        return ofertas


class AdaptadorBusquedaAerolinea(PuertoBusqueda):
    tipos = ("flight",)

    def __init__(self, api, limite_por_minuto: int | None = None):
        self.api = api
        self.proveedor = api.proveedor
        self.limite_por_minuto = limite_por_minuto or api.limite_por_minuto

    def buscar(self, consulta: Consulta) -> list[dict]:
        crudas = self.api.buscar(consulta.location, consulta.arrivalLocation, consulta.date, consulta.currency)
        ofertas = []
        for c in crudas:
            tramos = c.get("segments") or []
            if not tramos:
                continue
            primero, ultimo = tramos[0], tramos[-1]
            oferta = {"offerId": c["fareId"], "type": "flight", "provider": self.proveedor,
                      "startsAt": _con_zona(primero["dep"], primero["depTz"]),
                      "endsAt": _con_zona(ultimo["arr"], ultimo["arrTz"]),
                      "timeZone": primero["depTz"], "arrivalTimeZone": ultimo["arrTz"],
                      "location": primero["from"], "arrivalLocation": ultimo["to"], "stops": len(tramos) - 1,
                      "price": c.get("price"), "offerUrl": c.get("deepLink")}
            if _valida(oferta):
                ofertas.append(oferta)
        return ofertas
