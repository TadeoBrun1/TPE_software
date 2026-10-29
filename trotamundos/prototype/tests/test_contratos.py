"""Pruebas de contrato (spec-driven): lo que el prototipo publica y responde cumple los archivos de `specs/`.

Estas pruebas no demuestran seguridad, latencia ni recuperación (ingestion-validation.md): solo forma y reglas.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from contratos.esquemas import ARCHIVOS_EVENTOS, ContratoInvalido, validar_api, validar_evento, version_contrato
from contratos.topologia import (COLA_NUCLEO, COLA_PUSH, EXCHANGE_DOMINIO, EXCHANGE_INGESTA, SHARDS,
                                 cola_instancia_notificador, routing_key_novedad, shard_de_usuario, topologia_region)
from nucleo.esquemas.registro import ESQUEMAS_POR_DEFECTO

RK_A_EVENTO = {"panel.changed.v1": "panel.changed.v1", "trip.changed.v1": "trip.changed.v1",
               "booking.facts.v1": "booking.facts.v1"}


def evento_de(routing_key: str) -> str:
    return "booking.change.detected.v1" if routing_key.startswith("booking.change.detected.v1.s") \
        else RK_A_EVENTO[routing_key]


def test_versiones_de_los_contratos_que_implementa_el_prototipo():
    assert version_contrato("booking.change.detected.v1") == "0.2.0"
    assert version_contrato("panel.changed.v1") == "0.2.0"
    assert version_contrato("trip.changed.v1") == "0.1.0"
    assert version_contrato("booking.facts.v1") == "0.1.0"
    assert set(ARCHIVOS_EVENTOS) >= {"booking.change.detected.v1", "panel.changed.v1", "trip.changed.v1",
                                     "booking.facts.v1"}


def test_todo_lo_publicado_cumple_su_contrato(sistema, juan, ana):
    """Recorrido con cambios manuales, novedades de proveedor, archivado y compartición: cada mensaje se valida."""
    region = sistema.regiones["sa-east"]
    region.nucleo.registrar_vinculacion("con-hotel", juan.user_id, "hotel-sol")
    region.ingesta.vinculaciones.registrar("con-hotel", juan.user_id, "sa-east", "hotel-sol", "provider")
    region.fuentes["hotel"].publicar("con-hotel", {"reservationId": "HS-1", "version": 1, "status": "CONFIRMED",
                                                   "checkIn": "2026-11-10", "checkOut": "2026-11-14",
                                                   "city": "Madrid", "timeZone": "Europe/Madrid"})
    reserva = juan.reserva("c1", type="train", details={"schema": "train.v1", "trainNumber": "AVE 3172"})
    juan.patch(f"/bookings/{reserva['id']}", {"notes": "andén 4"}, headers={"If-Match": '"1"'})
    juan.post(f"/trips/{reserva['tripId']}/archive")
    ana.reserva("a1")
    sistema.procesar()
    publicados = [m for r in sistema.regiones.values() for m in r.broker.publicados]
    assert {evento_de(m.routing_key) for m in publicados} == {"booking.change.detected.v1", "panel.changed.v1",
                                                              "trip.changed.v1", "booking.facts.v1"}
    for mensaje in publicados:
        validar_evento(evento_de(mensaje.routing_key), mensaje.cuerpo)
        assert mensaje.encabezados["traceparent"].startswith("00-")  # contexto W3C en cada mensaje (ADR-0067)
        assert "notes" not in json.dumps(mensaje.cuerpo)  # los eventos no llevan notas del usuario


def test_respuestas_de_la_api_cumplen_la_openapi(juan):
    reserva = juan.reserva("api")
    validar_api("Booking", reserva)
    validar_api("Panel", juan.get("/panel").json())
    validar_api("Trip", juan.get(f"/trips/{reserva['tripId']}").json())
    error = juan.post("/bookings", {"type": "hotel"}, headers={"Idempotency-Key": "x"})
    assert error.status_code == 400
    validar_api("Error", error.json())
    with pytest.raises(ContratoInvalido):
        validar_api("BookingInput", {"type": "submarino"})


def test_regla_de_shards_por_usuario():
    """Primeros 16 hexadecimales de SHA-256 del JSON compacto [homeRegion,userId], como entero, módulo 8."""
    usuario = "f3a1c2d4-0000-4000-8000-000000000001"
    esperado = int(hashlib.sha256(b'["sa-east","' + usuario.encode() + b'"]').hexdigest()[:16], 16) % 8
    assert shard_de_usuario("sa-east", usuario) == esperado
    assert routing_key_novedad("sa-east", usuario) == f"booking.change.detected.v1.s{esperado}"
    repartidos = {shard_de_usuario("eu-west", f"usuario-{i}") for i in range(200)}
    assert repartidos == set(range(SHARDS))


def test_topologia_del_broker():
    topologia = topologia_region()
    assert set(topologia.exchanges) == {EXCHANGE_INGESTA, EXCHANGE_DOMINIO}
    colas = {c.nombre: c for c in topologia.colas}
    for shard in range(SHARDS):
        cola = colas[COLA_NUCLEO.format(shard=shard)]
        assert cola.tipo == "quorum" and cola.argumentos["x-single-active-consumer"] is True
        assert cola.enlaces == [(EXCHANGE_INGESTA, f"booking.change.detected.v1.s{shard}")]
    assert colas[COLA_PUSH].tipo == "quorum"
    instancia = cola_instancia_notificador("abc")
    assert instancia.tipo == "classic" and instancia.exclusiva and not instancia.durable  # única excepción
    assert all(c.tipo == "quorum" for c in topologia.colas)


def test_esquemas_de_detalles_registrados():
    """ADR-0066: cada tipo con detalles tiene su esquema versionado en specs/schemas."""
    from contratos.esquemas import RAIZ_SPECS, esquema_detalles

    for identificador in ESQUEMAS_POR_DEFECTO:
        assert esquema_detalles(identificador) is not None
    archivos = {r.name.removeprefix("details-").removesuffix(".json") for r in (RAIZ_SPECS / "schemas").glob("details-*.json")}
    assert archivos == set(ESQUEMAS_POR_DEFECTO)
