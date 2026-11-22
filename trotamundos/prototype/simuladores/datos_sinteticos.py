"""Viajeros sintéticos con preferencias ocultas, para probar el human-in-the-loop sin datos reales (ADR-0083).

Cada viajero tiene pesos ocultos sobre atributos de las ofertas (precio relativo, escalas, diferencia de horario
con la reserva cancelada y si es el mismo proveedor). Al ver sus sugerencias en orden, rechaza las que no le sirven
y acepta la primera cuya utilidad supera su umbral, con algo de ruido. El modelo de recomendación no ve estos pesos:
solo el feedback, igual que en producción. Así se puede medir si aprende.

La utilidad se calcula con los atributos crudos de la oferta normalizada (`specs/offer-search.md`), no con las
características del modelo, para que la prueba no le regale la respuesta.
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass
from datetime import datetime

# Media de la población (suposición): el horario y las escalas pesan más que el precio.
MEDIA = {"precio": -1.0, "escalas": -1.2, "desvio": -2.5, "proveedor": 0.8}
DESVIO_ENTRE_VIAJEROS = 0.5


@dataclass
class ViajeroSintetico:
    user_id: str
    pesos: dict
    sesgo: float = 0.6
    ruido: float = 0.3

    def utilidad(self, oferta: dict, cancelada: dict, mediana_precio: float, azar: random.Random) -> float:
        precio_rel = oferta["price"]["amount"] / mediana_precio - 1 if mediana_precio else 0.0
        desvio = abs((datetime.fromisoformat(oferta["startsAt"]) -
                      datetime.fromisoformat(cancelada["startsAt"])).total_seconds()) / 86400
        mismo = 1.0 if oferta["provider"] == cancelada.get("provider") else 0.0
        return (self.sesgo + self.pesos["precio"] * precio_rel + self.pesos["escalas"] * oferta.get("stops", 0)
                + self.pesos["desvio"] * min(desvio, 2.0) + self.pesos["proveedor"] * mismo
                + azar.gauss(0, self.ruido))

    def decidir(self, mostradas: list[dict], cancelada: dict, candidatas: list[dict],
                azar: random.Random) -> list[tuple[int, str]]:
        """Recorre las sugerencias en orden: rechaza hasta aceptar una. Devuelve (posición, acción)."""
        mediana = statistics.median(o["price"]["amount"] for o in candidatas) if candidatas else 0.0
        acciones = []
        for posicion, oferta in enumerate(mostradas):
            if self.utilidad(oferta, cancelada, mediana, azar) > 0:
                acciones.append((posicion, "accept"))
                break
            acciones.append((posicion, "reject"))
        return acciones


def generar_viajeros(cantidad: int, semilla: int = 7, prefijo: str = "sintetico") -> list[ViajeroSintetico]:
    azar = random.Random(semilla)
    return [ViajeroSintetico(f"{prefijo}-{i}", {k: azar.gauss(v, DESVIO_ENTRE_VIAJEROS) for k, v in MEDIA.items()})
            for i in range(cantidad)]


def vuelo_cancelado(azar: random.Random, rutas=(("EZE", "MAD"), ("EZE", "BCN"), ("AEP", "MAD"))) -> dict:
    """Reserva de vuelo cancelada, con los campos que llegan a la recomendación por `booking.facts.v1`."""
    origen, destino = azar.choice(rutas)
    dia = azar.randint(1, 27)
    hora = azar.choice([8, 13, 18, 22])
    return {"type": "flight", "provider": azar.choice(["aerolinea-sur", "aerolinea-norte"]),
            "startsAt": f"2026-12-{dia:02d}T{hora:02d}:00:00-03:00", "location": origen, "arrivalLocation": destino,
            "startDate": f"2026-12-{dia:02d}"}
