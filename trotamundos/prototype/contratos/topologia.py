"""Topología de RabbitMQ de `specs/ingestion-operations.md` y regla de shards por usuario."""
from __future__ import annotations

import hashlib
import json

from comun.infraestructura.broker import Cola, Topologia

EXCHANGE_INGESTA = "travel.ingestion"
EXCHANGE_DOMINIO = "travel.domain"

SHARDS = 8  # no se cambia sin drenar y coordinar colas (ingestion-operations.md)

RK_NOVEDAD = "booking.change.detected.v1.s{shard}"
RK_PANEL = "panel.changed.v1"
RK_VIAJE = "trip.changed.v1"
RK_HECHOS = "booking.facts.v1"
RK_RESERVA = "booking.changed.v1"

COLA_NUCLEO = "core.bookings.s{shard}"
COLA_ANALITICA = "analytics.facts"
COLA_PUSH = "notifier.push"
COLA_INSTANCIA_NOTIFICADOR = "notifier.instance.{instancia}"


def shard_de_usuario(home_region: str, user_id: str) -> int:
    """Primeros 16 hexadecimales de SHA-256 del JSON compacto [homeRegion,userId], como entero, módulo 8."""
    datos = json.dumps([home_region, user_id], separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return int(hashlib.sha256(datos).hexdigest()[:16], 16) % SHARDS


def routing_key_novedad(home_region: str, user_id: str) -> str:
    return RK_NOVEDAD.format(shard=shard_de_usuario(home_region, user_id))


def topologia_region() -> Topologia:
    """Exchanges y colas durables de una región. Las colas por instancia del notificador las declara cada instancia."""
    colas = [
        Cola(COLA_NUCLEO.format(shard=s), tipo="quorum",
             argumentos={"x-single-active-consumer": True},
             enlaces=[(EXCHANGE_INGESTA, RK_NOVEDAD.format(shard=s))])
        for s in range(SHARDS)
    ]
    # La analítica (fuera del alcance del prototipo) tiene su cola declarada para que los eventos tengan ruta.
    colas.append(Cola(COLA_ANALITICA, tipo="quorum", enlaces=[(EXCHANGE_DOMINIO, RK_HECHOS),
                                                              (EXCHANGE_DOMINIO, RK_VIAJE)]))
    colas.append(Cola(COLA_PUSH, tipo="quorum", enlaces=[(EXCHANGE_DOMINIO, RK_PANEL)]))
    return Topologia(exchanges=[EXCHANGE_INGESTA, EXCHANGE_DOMINIO], colas=colas)


def cola_instancia_notificador(instancia: str) -> Cola:
    """Cola classic, exclusiva y temporal: única excepción a las colas quorum (ADR-0046)."""
    return Cola(COLA_INSTANCIA_NOTIFICADOR.format(instancia=instancia), tipo="classic", durable=False,
                exclusiva=True, auto_borrar=True, argumentos={"x-message-ttl": 60_000, "x-max-length": 10_000},
                enlaces=[(EXCHANGE_DOMINIO, RK_PANEL)])
