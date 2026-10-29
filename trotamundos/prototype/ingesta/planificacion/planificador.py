"""Planificador (ADR-0020): agenda el trabajo de la ingesta.

* Trabajo por aviso: lo crea el receptor cuando llega un aviso nuevo de un proveedor.
* Reconciliación de respaldo: cada vinculación activa se consulta periódicamente aunque no lleguen avisos, para
  recuperar huecos. El intervalo es el del perfil "actividad reciente" de `ingestion-operations.md` (15 min).
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from comun.infraestructura.reloj import iso, parsear
from comun.observabilidad import nuevo_correlation_id, nuevo_traceparent

INTERVALO_RECONCILIACION = timedelta(minutes=15)


class Planificador:
    def __init__(self, registro, vinculaciones, reloj):
        self.registro = registro
        self.vinculaciones = vinculaciones
        self.reloj = reloj

    def agendar(self, connection_id: str, tipo: str) -> str:
        """Trabajo durable. La traza se abre al detectar (aviso o consulta de reconciliación), ADR-0067."""
        trabajo_id = str(uuid.uuid4())
        with self.registro.base.transaccion() as tx:
            tx.ejecutar("INSERT INTO trabajos (trabajo_id, connection_id, tipo, estado, correlation_id, traceparent, "
                        "creado) VALUES (?, ?, ?, 'pendiente', ?, ?, ?)",
                        (trabajo_id, connection_id, tipo, nuevo_correlation_id(), nuevo_traceparent(),
                         iso(self.reloj.ahora())))
        return trabajo_id

    def planificar(self) -> int:
        ahora = self.reloj.ahora()
        agendadas = 0
        for vinculacion in self.vinculaciones.activas():
            proxima = vinculacion["proxima_reconciliacion"]
            if proxima is None or parsear(proxima) <= ahora:
                self.agendar(vinculacion["connection_id"], "reconciliacion")
                with self.registro.base.transaccion() as tx:
                    tx.ejecutar("UPDATE vinculaciones SET proxima_reconciliacion = ? WHERE connection_id = ?",
                                (iso(ahora + INTERVALO_RECONCILIACION), vinculacion["connection_id"]))
                agendadas += 1
        return agendadas
