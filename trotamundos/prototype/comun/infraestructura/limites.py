"""Límite de tasa por cliente (token bucket). Biblioteca técnica sin dominio."""
from __future__ import annotations

import threading
import time


class LimitePorCliente:
    """Token bucket por principal (o por dirección si no hay token válido)."""

    def __init__(self, capacidad: int = 60, por_segundo: float = 20.0):
        self.capacidad = capacidad
        self.por_segundo = por_segundo
        self._cubetas: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def permitir(self, clave: str) -> bool:
        ahora = time.monotonic()
        with self._lock:
            fichas, ultimo = self._cubetas.get(clave, (float(self.capacidad), ahora))
            fichas = min(self.capacidad, fichas + (ahora - ultimo) * self.por_segundo)
            if fichas < 1:
                self._cubetas[clave] = (fichas, ahora)
                return False
            self._cubetas[clave] = (fichas - 1, ahora)
            return True
