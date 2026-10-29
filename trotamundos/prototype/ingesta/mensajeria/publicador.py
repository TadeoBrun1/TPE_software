"""Publicador de novedades: envía la outbox de la ingesta a `travel.ingestion` con routing key por shard de usuario
(`booking.change.detected.v1.s0` a `.s7`), con `mandatory` y confirmación del broker (ADR-0024, ADR-0028)."""
from __future__ import annotations

from comun.infraestructura.outbox import PublicadorOutbox


def crear_publicador(base, broker, reloj, logger) -> PublicadorOutbox:
    return PublicadorOutbox([base], broker, reloj, logger)
