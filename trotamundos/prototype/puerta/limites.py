"""Límite por cliente (429) y degradación por prioridad ante sobrecarga (503 con Retry-After), ADR-0047.

Prioridad alta (panel, lecturas por clave, quitar un permiso): se atiende. Media (cambios manuales): se rechaza si
la carga en curso supera el 80 % de la capacidad. Baja (viajes anteriores, archivar, reactivar, telemetría): se
rechaza a partir del 50 %.
"""
from __future__ import annotations

import threading

from comun.infraestructura.limites import LimitePorCliente  # noqa: F401 - se reexporta para la puerta


class ControlSobrecarga:
    UMBRALES = {"alta": None, "media": 0.8, "baja": 0.5}

    def __init__(self, capacidad: int = 200):
        self.capacidad = capacidad
        self.en_curso = 0
        self.forzada: float | None = None  # para pruebas y demostraciones
        self._lock = threading.Lock()

    def nivel(self) -> float:
        return self.forzada if self.forzada is not None else self.en_curso / self.capacidad

    def admitir(self, prioridad: str) -> bool:
        umbral = self.UMBRALES[prioridad]
        return umbral is None or self.nivel() < umbral

    def __enter__(self):
        with self._lock:
            self.en_curso += 1

    def __exit__(self, *_):
        with self._lock:
            self.en_curso -= 1
