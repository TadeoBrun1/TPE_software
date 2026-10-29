"""Tabla de enrutamiento por método y ruta (ADR-0062) y clasificación por prioridad (ADR-0047).

La ruta completa y su método se evalúan antes de usar el prefijo de región. No se reenvía toda petición que
contenga un tripId: solo las operaciones remotas de la tabla.

* `local`: se ejecuta en la región del usuario autenticado.
* `prefijo`: se ejecuta en la región del prefijo del identificador (viaje o invitación).
* `recurso`: la puerta audita sus rechazos previos al núcleo (`specs/access-audit.md`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Ruta:
    metodo: str
    plantilla: str
    destino: str        # local | prefijo | puerta | notificador | ingesta
    prioridad: str      # alta | media | baja
    recurso: bool
    parametro: str | None = None  # parámetro con el prefijo de región

    @property
    def patron(self) -> re.Pattern:
        return re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", self.plantilla) + "$")


RUTAS = [
    Ruta("GET", "/panel", "local", "alta", False),
    Ruta("POST", "/panel/events/ticket", "puerta", "alta", False),
    Ruta("GET", "/panel/events", "notificador", "alta", False),
    Ruta("POST", "/telemetry/panel-shown", "local", "baja", False),
    Ruta("GET", "/trips/archived", "local", "baja", False),
    Ruta("GET", "/trips/{tripId}", "prefijo", "alta", True, "tripId"),
    Ruta("POST", "/trips/{tripId}/archive", "prefijo", "baja", True, "tripId"),
    Ruta("POST", "/trips/{tripId}/reactivate", "prefijo", "baja", True, "tripId"),
    Ruta("GET", "/trips/{tripId}/shares", "prefijo", "baja", True, "tripId"),
    Ruta("POST", "/trips/{tripId}/shares", "prefijo", "media", True, "tripId"),
    Ruta("DELETE", "/trips/{tripId}/shares/{shareId}", "prefijo", "alta", True, "tripId"),
    Ruta("POST", "/shares/{shareId}/accept", "prefijo", "media", True, "shareId"),
    Ruta("GET", "/shared/trips", "local", "baja", True),
    Ruta("POST", "/shared/trips", "local", "media", True),
    Ruta("GET", "/shared/trips/{tripId}", "prefijo", "alta", True, "tripId"),
    Ruta("DELETE", "/shared/trips/{tripId}", "local", "alta", True),  # borra el marcador sin consultar al dueño
    Ruta("POST", "/bookings", "local", "media", False),
    Ruta("PATCH", "/bookings/{bookingId}", "local", "media", True),
    Ruta("DELETE", "/bookings/{bookingId}", "local", "media", True),
    Ruta("POST", "/avisos/{providerId}", "ingesta", "alta", False),
]

# Operaciones que una puerta acepta por el canal entre regiones (un solo salto).
REENVIABLES = {("GET", "/trips/{tripId}"), ("POST", "/trips/{tripId}/archive"), ("POST", "/trips/{tripId}/reactivate"),
               ("GET", "/trips/{tripId}/shares"), ("POST", "/trips/{tripId}/shares"),
               ("DELETE", "/trips/{tripId}/shares/{shareId}"), ("POST", "/shares/{shareId}/accept"),
               ("GET", "/shared/trips/{tripId}")}

# Rutas de recurso que no coinciden con ningún método conocido igual se auditan como rechazo.
_PREFIJOS_RECURSO = ("/trips/", "/bookings/", "/shared/trips", "/shares/")


def clasificar(metodo: str, camino: str) -> tuple[Ruta | None, dict]:
    for ruta in RUTAS:
        if ruta.metodo == metodo:
            coincidencia = ruta.patron.match(camino)
            if coincidencia:
                return ruta, coincidencia.groupdict()
    return None, {}


def es_recurso(camino: str) -> bool:
    return camino.startswith(_PREFIJOS_RECURSO)
