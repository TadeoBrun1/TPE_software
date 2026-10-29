"""Puerto de escritura de solo agregado al registro de auditoría (ADR-0061, `specs/access-audit.md`).

Ningún proceso de la aplicación modifica ni borra registros: este módulo solo expone `registrar`. Se escribe antes
de responder; si no se puede escribir, quien llama rechaza la solicitud con `503`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from comun.infraestructura.db import BaseDatos
from comun.infraestructura.reloj import Reloj, iso
from comun.observabilidad import contexto_correlacion

ACCIONES = {"share.read", "share.invite", "share.accept", "share.remove", "share.gateway_reject"}
MOTIVOS = {"no_permission", "owner_endpoint", "removed", "expired", "secret_mismatch", "email_mismatch",
           "not_found", "unauthenticated", "rate_limited", "bad_region", "owner_region_unavailable"}


class AuditoriaNoDisponible(Exception):
    pass


@dataclass
class Actor:
    user_id: str | None
    region: str | None
    issuer: str | None


class RegistroAuditoria:
    def __init__(self, base: BaseDatos, region: str, reloj: Reloj, logger):
        self.base = base
        self.region = region
        self.reloj = reloj
        self.logger = logger

    def registrar(self, accion: str, resultado: str, actor: Actor, metodo: str, ruta: str, entry_region: str,
                  motivo: str | None = None, trip_id: str | None = None, share_id: str | None = None,
                  booking_id: str | None = None):
        assert accion in ACCIONES and resultado in ("allowed", "denied") and (motivo is None or motivo in MOTIVOS)
        registro = (str(uuid.uuid4()), iso(self.reloj.ahora()), accion, resultado, motivo, actor.user_id,
                    actor.region, actor.issuer, metodo, ruta, booking_id, entry_region, trip_id, share_id,
                    contexto_correlacion.get())
        try:
            with self.base.transaccion() as tx:
                tx.ejecutar("INSERT INTO auditoria (record_id, at, action, result, reason, actor_user_id, "
                            "actor_region, actor_issuer, method, route, booking_id, entry_region, trip_id, share_id, "
                            "correlation_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", registro)
        except Exception as error:
            # El rechazo igual ocurre; el evento queda en los logs con una alerta (ADR-0061).
            self.logger.alerta("auditoria_no_disponible", accion=accion, resultado=resultado, motivo=motivo,
                               tripId=trip_id, shareId=share_id, bookingId=booking_id, metodo=metodo, ruta=ruta)
            raise AuditoriaNoDisponible(str(error)) from error

    def consultar(self, **filtros) -> list[dict]:
        """Consulta para el equipo de seguridad y para las pruebas."""
        condiciones = " AND ".join(f"{k} = ?" for k in filtros) or "1 = 1"
        with self.base.transaccion() as tx:
            return tx.todos(f"SELECT * FROM auditoria WHERE {condiciones} ORDER BY at", tuple(filtros.values()))
