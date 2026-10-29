"""Reloj inyectable: en producción usa la hora del sistema; en las pruebas se fija o se adelanta."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


class Reloj:
    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)

    def hoy(self) -> date:
        return self.ahora().date()


class RelojFijo(Reloj):
    def __init__(self, inicio: datetime):
        self._ahora = inicio

    def ahora(self) -> datetime:
        return self._ahora

    def adelantar(self, **delta):
        self._ahora = self._ahora + timedelta(**delta)

    def fijar(self, momento: datetime):
        self._ahora = momento


def iso(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parsear(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))
