"""Proveedores externos simulados (CON-1, CON-2): datos sintéticos, sin credenciales ni correos reales.

* `BuzonSimulado`: buzón de correo con mensajes de texto y paginación por cursor.
* `ApiHotelSimulada`: API de una cadena hotelera con versión por reserva y estados CONFIRMED/ON_HOLD/CANCELLED.
* `ApiAerolineaSimulada`: API de una aerolínea con revisión y estados HK/UN/XX (campos distintos a los del hotel).

Cada simulador permite inyectar fallas (temporal, cuota, autorización) para las pruebas de V11.
"""
from __future__ import annotations

import threading


class ErrorTemporal(Exception):
    pass


class ErrorCuota(Exception):
    def __init__(self, reintentar_en: int):
        super().__init__(f"cuota agotada, Retry-After {reintentar_en}")
        self.reintentar_en = reintentar_en


class ErrorAutorizacion(Exception):
    pass


class _Fuente:
    def __init__(self):
        self._lock = threading.Lock()
        self.fallas: list[Exception] = []
        self.consultas = 0

    def fallar_proxima(self, error: Exception):
        self.fallas.append(error)

    def _consultar(self):
        self.consultas += 1
        if self.fallas:
            raise self.fallas.pop(0)


class BuzonSimulado(_Fuente):
    def __init__(self):
        super().__init__()
        self.mensajes: dict[str, list[dict]] = {}

    def recibir(self, connection_id: str, remitente: str, texto: str) -> str:
        with self._lock:
            lista = self.mensajes.setdefault(connection_id, [])
            message_id = f"msg-{connection_id}-{len(lista) + 1}"
            lista.append({"id": message_id, "from": remitente, "body": texto})
            return message_id

    def listar(self, connection_id: str, cursor: str | None, tamano: int = 10) -> tuple[list[dict], str]:
        self._consultar()
        desde = int(cursor or 0)
        with self._lock:
            lista = self.mensajes.get(connection_id, [])
            pagina = lista[desde:desde + tamano]
        return [dict(m) for m in pagina], str(desde + len(pagina))


class _ApiConCambios(_Fuente):
    clave = "id"

    def __init__(self):
        super().__init__()
        self.cambios: dict[str, list[dict]] = {}

    def publicar(self, connection_id: str, reserva: dict):
        with self._lock:
            self.cambios.setdefault(connection_id, []).append(dict(reserva))

    def cambios_desde(self, connection_id: str, cursor: str | None, tamano: int = 10) -> tuple[list[dict], str]:
        self._consultar()
        desde = int(cursor or 0)
        with self._lock:
            lista = self.cambios.get(connection_id, [])
            pagina = lista[desde:desde + tamano]
        return [dict(r) for r in pagina], str(desde + len(pagina))


class ApiHotelSimulada(_ApiConCambios):
    """Ej.: {"reservationId", "version", "status", "checkIn", "checkInTime", "checkOut", "checkOutTime",
    "city", "timeZone", "updatedAt"}."""


class ApiAerolineaSimulada(_ApiConCambios):
    """Ej.: {"pnr", "rev", "state", "flightNumber", "from": {"airport", "time", "tz"}, "to": {...}}."""
