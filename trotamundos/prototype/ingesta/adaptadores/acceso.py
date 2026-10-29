"""Adaptadores de acceso por proveedor (ADR-0023, Ports and Adapters).

Cada adaptador conoce la API, la paginación y los errores de su fuente, y devuelve elementos crudos con su formato.
El acceso al buzón y el formato de una confirmación son responsabilidades distintas: los extractores por formato
están en `ingesta/procesamiento`. Un adaptador no depende de otro adaptador.
"""
from __future__ import annotations

from dataclasses import dataclass

from simuladores.proveedores import ApiAerolineaSimulada, ApiHotelSimulada, BuzonSimulado


@dataclass
class Elemento:
    item_id: str        # identificador estable en la fuente (mensaje o reserva + versión)
    formato: str        # elige el extractor
    crudo: dict


@dataclass
class Pagina:
    elementos: list[Elemento]
    cursor: str


class AdaptadorAcceso:
    fuente = "provider"  # email | provider (campo `source` del contrato)

    def consultar(self, vinculacion: dict, cursor: str | None) -> Pagina:
        raise NotImplementedError


class AdaptadorCorreo(AdaptadorAcceso):
    fuente = "email"

    def __init__(self, buzon: BuzonSimulado):
        self.buzon = buzon

    def consultar(self, vinculacion, cursor):
        mensajes, siguiente = self.buzon.listar(vinculacion["connection_id"], cursor)
        return Pagina([Elemento(m["id"], "correo:texto", m) for m in mensajes], siguiente)


class AdaptadorHotel(AdaptadorAcceso):
    def __init__(self, api: ApiHotelSimulada):
        self.api = api

    def consultar(self, vinculacion, cursor):
        reservas, siguiente = self.api.cambios_desde(vinculacion["connection_id"], cursor)
        return Pagina([Elemento(f"{r['reservationId']}@{r['version']}", "api:hotel", r) for r in reservas], siguiente)


class AdaptadorAerolinea(AdaptadorAcceso):
    def __init__(self, api: ApiAerolineaSimulada):
        self.api = api

    def consultar(self, vinculacion, cursor):
        reservas, siguiente = self.api.cambios_desde(vinculacion["connection_id"], cursor)
        return Pagina([Elemento(f"{r['pnr']}@{r['rev']}", "api:aerolinea", r) for r in reservas], siguiente)
