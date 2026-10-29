"""Escritura de los rechazos previos al núcleo en el registro de auditoría de la región (`specs/access-audit.md`).

El formato del registro es el del contrato; la puerta no comparte código con el núcleo. Se escribe antes de
responder; si falla, la solicitud se rechaza con 503 y el evento queda en los logs con una alerta.
"""
from __future__ import annotations

import uuid

from comun.infraestructura.db import BaseDatos
from comun.infraestructura.reloj import Reloj, iso
from comun.observabilidad import contexto_correlacion


class AuditoriaPuerta:
    def __init__(self, base: BaseDatos, reloj: Reloj, logger):
        self.base = base
        self.reloj = reloj
        self.logger = logger

    def rechazo(self, motivo: str, metodo: str, ruta: str, entry_region: str, identidad=None, parametros=None) -> bool:
        parametros = parametros or {}
        registro = (str(uuid.uuid4()), iso(self.reloj.ahora()), "share.gateway_reject", "denied", motivo,
                    identidad.user_id if identidad else None, identidad.region if identidad else None,
                    identidad.issuer if identidad else None, metodo, ruta, parametros.get("bookingId"), entry_region,
                    parametros.get("tripId"), parametros.get("shareId"), contexto_correlacion.get())
        try:
            with self.base.transaccion() as tx:
                tx.ejecutar("INSERT INTO auditoria (record_id, at, action, result, reason, actor_user_id, actor_region, "
                            "actor_issuer, method, route, booking_id, entry_region, trip_id, share_id, correlation_id) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", registro)
            return True
        except Exception:
            self.logger.alerta("auditoria_no_disponible", accion="share.gateway_reject", motivo=motivo, metodo=metodo,
                               ruta=ruta, **{k: v for k, v in parametros.items() if k != "providerId"})
            return False
