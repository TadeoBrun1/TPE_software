"""APIs de búsqueda de ofertas simuladas (iteración 5, CON-1, CON-2): datos sintéticos y deterministas.

Cada proveedor tiene su propio formato, distinto del contrato normalizado de `specs/offer-search.md`, para que el
adaptador tenga algo que traducir (ADR-0082):

* `BusquedaHotelSimulada`: ofertas de hotel con `hotelOfferId`, `checkIn`/`checkInTime`, `nights`, `total` y
  `bookingLink`.
* `BusquedaAerolineaSimulada`: tarifas con `fareId`, `segments` (un tramo por escala), `price` y `deepLink`.

Cada API tiene un límite de consultas por minuto, como los proveedores reales: si se excede, responde con cuota
agotada y lo cuenta en `cuota_excedida` (la prueba de QA-12 verifica que nunca pase). También permite inyectar
fallas (temporal, cuota, autorización), como las APIs de reservas.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, timedelta

from simuladores.proveedores import ErrorCuota, _Fuente


def _semilla(*partes) -> int:
    return int(hashlib.sha256("|".join(map(str, partes)).encode()).hexdigest()[:12], 16)


class _BusquedaSimulada(_Fuente):
    def __init__(self, proveedor: str, limite_por_minuto: int = 60, reloj=None):
        super().__init__()
        self.proveedor = proveedor
        self.limite_por_minuto = limite_por_minuto
        self.reloj = reloj
        self.cuota_excedida = 0
        self.fijas: dict[tuple, list[dict]] = {}
        self._ventana: list[datetime] = []

    def _controlar_cuota(self):
        if self.reloj is None:
            return
        ahora = self.reloj.ahora()
        self._ventana = [t for t in self._ventana if ahora - t < timedelta(minutes=1)]
        if len(self._ventana) >= self.limite_por_minuto:
            self.cuota_excedida += 1
            raise ErrorCuota(reintentar_en=60)
        self._ventana.append(ahora)

    def _consultar_con_cuota(self):
        self._consultar()  # fallas inyectadas y contador de consultas
        self._controlar_cuota()


class BusquedaHotelSimulada(_BusquedaSimulada):
    def fijar(self, ciudad: str, check_in: str, noches: int, ofertas: list[dict]):
        self.fijas[(ciudad, check_in, noches)] = ofertas

    def buscar(self, ciudad: str, check_in: str, noches: int, moneda: str = "EUR") -> list[dict]:
        self._consultar_con_cuota()
        if (ciudad, check_in, noches) in self.fijas:
            return [dict(o) for o in self.fijas[(ciudad, check_in, noches)]]
        azar = random.Random(_semilla(self.proveedor, ciudad, check_in, noches))
        ofertas = []
        for i in range(4):
            por_noche = azar.choice([70, 90, 110, 140, 180, 220])
            ofertas.append({
                "hotelOfferId": f"{self.proveedor}-{ciudad}-{check_in}-{i}",
                "hotelName": f"{self.proveedor.split('-')[-1].title()} {ciudad} {i + 1}",
                "checkIn": check_in, "checkInTime": azar.choice(["14:00", "15:00", "16:00"]), "nights": noches,
                "city": ciudad, "timeZone": "Europe/Madrid",
                "total": {"value": float(por_noche * noches), "currencyCode": moneda},
                "bookingLink": f"https://{self.proveedor}.example/ofertas/{ciudad}-{check_in}-{i}",
            })
        return ofertas


class BusquedaAerolineaSimulada(_BusquedaSimulada):
    def fijar(self, origen: str, destino: str, fecha: str, tarifas: list[dict]):
        self.fijas[(origen, destino, fecha)] = tarifas

    def buscar(self, origen: str, destino: str, fecha: str, moneda: str = "EUR") -> list[dict]:
        self._consultar_con_cuota()
        if (origen, destino, fecha) in self.fijas:
            return [dict(t) for t in self.fijas[(origen, destino, fecha)]]
        azar = random.Random(_semilla(self.proveedor, origen, destino, fecha))
        dia = date.fromisoformat(fecha)
        tarifas = []
        for i in range(5):
            salida = datetime(dia.year, dia.month, dia.day, azar.choice([6, 9, 13, 17, 21, 23]), 0)
            escalas = azar.choice([0, 0, 1, 1, 2])
            duracion = timedelta(hours=12 + 3 * escalas + azar.choice([0, 1, 2]))
            puntos = [origen] + [f"X{i}{k}" for k in range(escalas)] + [destino]
            tramos, hora = [], salida
            for k in range(len(puntos) - 1):
                llegada = hora + duracion / (escalas + 1)
                tramos.append({"from": puntos[k], "to": puntos[k + 1], "dep": hora.isoformat(timespec="minutes"),
                               "depTz": "America/Argentina/Buenos_Aires" if k == 0 else "UTC",
                               "arr": llegada.isoformat(timespec="minutes"),
                               "arrTz": "Europe/Madrid" if k == len(puntos) - 2 else "UTC"})
                hora = llegada
            tarifas.append({
                "fareId": f"{self.proveedor}-{origen}{destino}-{fecha}-{i}", "carrier": self.proveedor,
                "segments": tramos,
                "price": {"amount": float(azar.choice([450, 600, 750, 900, 1100, 1400]) - 80 * escalas),
                          "currency": moneda},
                "deepLink": f"https://{self.proveedor}.example/tarifas/{origen}{destino}-{fecha}-{i}",
            })
        return tarifas
