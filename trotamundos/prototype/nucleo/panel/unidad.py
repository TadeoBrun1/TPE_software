"""Unidad de cambio de un usuario: junta lo que cambió en una transacción y, al confirmar, deja todo coherente.

En la misma transacción local de la partición del usuario (ADR-0040, ADR-0042, ADR-0027):
  1. recalcula las fechas de los viajes tocados;
  2. actualiza el panel (versión + 1) y deja `panel.changed.v1` en la outbox;
  3. deja `trip.changed.v1` y `booking.facts.v1` en la outbox.
"""
from __future__ import annotations

from comun.infraestructura.db import Transaccion
from comun.infraestructura.reloj import Reloj, iso
from nucleo.mensajeria import eventos
from nucleo.panel import proyector

_PRECEDENCIA_VIAJE = ["deleted", "archived", "reactivated", "created", "updated"]


class UnidadDeCambio:
    def __init__(self, tx: Transaccion, region: str, user_id: str, reloj: Reloj, correlation_ids=None):
        self.tx = tx
        self.region = region
        self.user_id = user_id
        self.reloj = reloj
        self.ahora = iso(reloj.ahora())
        self.version_anterior = proyector.bloquear(tx, user_id, self.ahora)  # bloqueo por usuario primero
        self.motivos: list[str] = []
        self.correlation_ids: list[str] = list(correlation_ids or [])
        self.viajes: dict[str, str] = {}
        self.hechos: list[tuple[dict, str]] = []
        self.hubo_cambios = False

    def motivo(self, motivo: str):
        self.motivos.append(motivo)
        self.hubo_cambios = True

    def viaje(self, trip_id: str | None, tipo: str = "updated"):
        if not trip_id:
            return
        actual = self.viajes.get(trip_id)
        if actual is None or _PRECEDENCIA_VIAJE.index(tipo) < _PRECEDENCIA_VIAJE.index(actual):
            self.viajes[trip_id] = tipo
        self.hubo_cambios = True

    def reserva(self, fila: dict, tipo: str):
        self.hechos.append((dict(fila), tipo))
        self.hubo_cambios = True

    def confirmar(self) -> int | None:
        """Devuelve la nueva versión del panel, o None si no hubo cambios."""
        if not self.hubo_cambios:
            return None
        for trip_id, tipo in self.viajes.items():
            if tipo != "deleted":
                recalcular_fechas(self.tx, trip_id)
        version = proyector.actualizar(self.tx, self.region, self.user_id, self.motivos, self.correlation_ids,
                                       self.reloj)
        for trip_id, tipo in self.viajes.items():
            eventos.viaje_cambiado(self.tx, self.region, self.user_id, trip_id, tipo, version, self.ahora)
        for fila, tipo in self.hechos:
            eventos.hechos_reserva(self.tx, self.region, fila, tipo, self.ahora)
        return version


def recalcular_fechas(tx: Transaccion, trip_id: str):
    """Las fechas del viaje salen de los datos de sus reservas (ADR-0045)."""
    fila = tx.uno("SELECT MIN(substr(inicio, 1, 10)) AS desde, MAX(substr(COALESCE(fin, inicio), 1, 10)) AS hasta "
                  "FROM reservas WHERE trip_id = ? AND inicio IS NOT NULL", (trip_id,))
    if fila and fila["desde"]:
        tx.ejecutar("UPDATE viajes SET fecha_inicio = ?, fecha_fin = ? WHERE trip_id = ?",
                    (fila["desde"], fila["hasta"], trip_id))
