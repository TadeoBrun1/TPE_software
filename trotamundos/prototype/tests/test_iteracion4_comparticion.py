"""Iteración 4: compartición entre regiones, autenticación en la puerta y auditoría de accesos.

ADR-0060 (identidad y tokens), ADR-0061 (permisos y auditoría), ADR-0062 (enrutamiento entre regiones) y
`specs/access-audit.md`. Juan vive en sa-east y es dueño del viaje; Ana vive en eu-west y es la invitada.
"""
from __future__ import annotations

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient

from contratos.esquemas import validar_api

CAMPOS_PRIVADOS = {"notes", "providerReference", "details", "price", "userEditedFields", "origin"}


def auditoria(sistema, region: str, **filtros) -> list[dict]:
    return sistema.regiones[region].nucleo.auditoria.consultar(**filtros)


def motivos(sistema, region: str, accion: str) -> list[str]:
    return [r["reason"] for r in auditoria(sistema, region, action=accion)]


@pytest.fixture
def viaje(juan):
    reserva = juan.reserva("compartir", notes="código de la caja: 1234", providerReference="HX-99",
                           price={"amount": 480, "currency": "EUR"})
    return reserva["tripId"]


@pytest.fixture
def invitacion(sistema, juan, viaje):
    respuesta = juan.post(f"/trips/{viaje}/shares", {"email": "ana@example.com"},
                          headers={"Idempotency-Key": "inv-1"})
    assert respuesta.status_code == 201, respuesta.text
    validar_api("Share", respuesta.json())
    correo = sistema.regiones["sa-east"].nucleo.correo.ultimo_para("ana@example.com")
    return {"shareId": respuesta.json()["id"], "secret": correo["secret"]}


@pytest.fixture
def compartido(ana, viaje, invitacion):
    aceptada = ana.post(f"/shares/{invitacion['shareId']}/accept", {"secret": invitacion["secret"]})
    assert aceptada.status_code == 200, aceptada.text
    validar_api("SharedTripRef", aceptada.json())
    assert ana.post("/shared/trips", aceptada.json()).status_code == 200  # marcador en la región de Ana
    return viaje


# ------------------------------------------------------------------------------------------ camino feliz

def test_invitar_aceptar_y_leer_entre_regiones(sistema, juan, ana, compartido, invitacion):
    assert juan.region == "sa-east" and ana.region == "eu-west" and compartido.startswith("sa-east:")
    assert [r["tripId"] for r in ana.get("/shared/trips").json()["trips"]] == [compartido]
    lectura = ana.get(f"/shared/trips/{compartido}")
    assert lectura.status_code == 200 and lectura.headers["cache-control"] == "no-store"
    validar_api("SharedTrip", lectura.json())
    [reserva] = lectura.json()["bookings"]
    assert not CAMPOS_PRIVADOS & set(reserva)  # proyección explícita: sin notas, códigos ni detalles
    # El dueño ve la invitación aceptada; aceptar otra vez con la misma cuenta no cambia nada.
    [share] = juan.get(f"/trips/{compartido}/shares").json()["shares"]
    assert share["status"] == "accepted"
    otra_vez = ana.post(f"/shares/{invitacion['shareId']}/accept", {"secret": invitacion["secret"]})
    assert otra_vez.json()["acceptedAt"] == share["acceptedAt"]
    # Los accesos permitidos quedan en el registro de la región del dueño, con la región de entrada.
    lectura_auditada = auditoria(sistema, "sa-east", action="share.read", result="allowed")[0]
    assert lectura_auditada["actor_region"] == "eu-west" and lectura_auditada["entry_region"] == "eu-west"
    assert lectura_auditada["actor_user_id"] == ana.user_id and lectura_auditada["trip_id"] == compartido
    assert {r["action"] for r in auditoria(sistema, "sa-east", result="allowed")} >= {"share.invite", "share.accept"}


def test_invitacion_idempotente(sistema, juan, viaje, invitacion):
    repetida = juan.post(f"/trips/{viaje}/shares", {"email": "ana@example.com"}, headers={"Idempotency-Key": "inv-1"})
    assert repetida.json()["id"] == invitacion["shareId"]
    assert len(juan.get(f"/trips/{viaje}/shares").json()["shares"]) == 1


# ------------------------------------------------------------------------------------------ rechazos auditados

def test_aceptar_con_otra_cuenta_o_secreto_incorrecto(sistema, cliente, ana, invitacion):
    pedro = cliente.registrar("pedro@example.com", "ES")
    con_otra_cuenta = pedro.post(f"/shares/{invitacion['shareId']}/accept", {"secret": invitacion["secret"]})
    assert con_otra_cuenta.status_code == 404
    secreto_malo = ana.post(f"/shares/{invitacion['shareId']}/accept", {"secret": "adivinado"})
    assert secreto_malo.status_code == 404
    assert motivos(sistema, "sa-east", "share.accept") == ["email_mismatch", "secret_mismatch"]


def test_leer_sin_permiso_o_por_el_endpoint_del_dueno(sistema, cliente, ana, compartido):
    pedro = cliente.registrar("pedro@example.com", "ES")
    assert pedro.get(f"/shared/trips/{compartido}").status_code == 404
    assert ana.get(f"/trips/{compartido}").status_code == 404  # el invitado no usa el endpoint del dueño
    assert motivos(sistema, "sa-east", "share.read") == ["no_permission", "owner_endpoint"]
    # Un método que no está en la tabla sobre una ruta de recurso también se rechaza y se audita.
    assert ana.patch(f"/trips/{compartido}/archive").status_code == 404
    assert motivos(sistema, "eu-west", "share.gateway_reject") == ["not_found"]


def test_sin_token_la_puerta_audita_el_rechazo(sistema, cliente, compartido):
    respuesta = cliente.http.get(f"/shared/trips/{compartido}")
    assert respuesta.status_code == 401
    [registro] = auditoria(sistema, "sa-east", action="share.gateway_reject")
    assert registro["reason"] == "unauthenticated" and registro["trip_id"] == compartido
    assert registro["actor_user_id"] is None


def test_quitar_permiso_y_borrar_el_marcador(sistema, juan, ana, compartido, invitacion):
    assert juan.delete(f"/trips/{compartido}/shares/{invitacion['shareId']}").status_code == 204
    assert ana.get(f"/shared/trips/{compartido}").status_code == 404
    assert motivos(sistema, "sa-east", "share.read") == ["removed"]
    assert [r["reason"] for r in auditoria(sistema, "sa-east", action="share.remove")] == [None]
    # El marcador sigue en la región de Ana hasta que ella lo borra.
    assert len(ana.get("/shared/trips").json()["trips"]) == 1
    assert ana.delete(f"/shared/trips/{compartido}").status_code == 204
    assert ana.get("/shared/trips").json()["trips"] == []


def test_region_del_dueno_no_disponible(sistema, ana, compartido):
    sistema.regiones["eu-west"].puerta.otras_regiones["sa-east"].disponible = False
    respuesta = ana.get(f"/shared/trips/{compartido}")
    assert respuesta.status_code == 503 and respuesta.headers["retry-after"] == "30"
    [registro] = auditoria(sistema, "eu-west", action="share.gateway_reject")
    assert registro["reason"] == "owner_region_unavailable" and registro["actor_user_id"] == ana.user_id
    # El marcador se borra en la región de Ana sin consultar a la región del dueño.
    assert ana.delete(f"/shared/trips/{compartido}").status_code == 204


def test_prefijo_de_region_desconocido(sistema, ana):
    respuesta = ana.get("/shared/trips/ap-south:000-" + "0" * 32)
    assert respuesta.status_code == 404
    assert motivos(sistema, "eu-west", "share.gateway_reject") == ["bad_region"]


def test_sin_auditoria_no_hay_acceso(sistema, juan, ana, viaje, compartido):
    sistema.regiones["sa-east"].auditoria.disponible = False
    lectura = ana.get(f"/shared/trips/{compartido}")
    assert lectura.status_code == 503 and lectura.json()["code"] == "audit_unavailable"
    invitacion = juan.post(f"/trips/{viaje}/shares", {"email": "pedro@example.com"},
                           headers={"Idempotency-Key": "inv-2"})
    assert invitacion.status_code == 503
    sin_token = juan.cliente.http.get(f"/shared/trips/{compartido}")
    assert sin_token.status_code == 503  # el rechazo de la puerta tampoco se responde sin registrarlo
    alertas = sistema.regiones["sa-east"].nucleo.logger.registros
    assert any(r["evento"] == "auditoria_no_disponible" for r in alertas)
    sistema.regiones["sa-east"].auditoria.disponible = True
    assert len(juan.get(f"/trips/{viaje}/shares").json()["shares"]) == 1  # la invitación fallida no quedó creada
    assert juan.post(f"/trips/{viaje}/shares", {"email": "pedro@example.com"},
                     headers={"Idempotency-Key": "inv-2"}).status_code == 201


# ------------------------------------------------------------------------------------------ tokens (ADR-0060)

def test_tokens_rechazados_por_la_puerta(sistema, juan, ana, reloj):
    identidad = sistema.regiones["sa-east"].identidad
    puerta = TestClient(sistema.regiones["sa-east"].puerta.app)

    def estado(token: str) -> int:
        return puerta.get("/panel", headers={"Authorization": f"Bearer {token}"}).status_code

    assert estado(juan.tokens["access_token"]) == 200
    assert estado(identidad.emitir_acceso(juan.user_id, juan.email, aud="otra-api")) == 401
    assert estado(identidad.emitir_acceso(juan.user_id, juan.email, typ="JWT")) == 401       # ID token
    assert estado(identidad.emitir_acceso(juan.user_id, juan.email, iss="https://id.falso.example")) == 401
    assert estado(identidad.emitir_acceso(juan.user_id, juan.email, homeRegion="eu-west")) == 401
    assert estado(ana.tokens["access_token"]) == 401  # token de otra región fuera del canal entre puertas
    reclamos = jwt.decode(juan.tokens["access_token"], options={"verify_signature": False})
    otra_clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert estado(jwt.encode(reclamos, otra_clave, algorithm="RS256",
                             headers={"kid": identidad.kid, "typ": "at+jwt"})) == 401  # firma inválida
    assert estado(jwt.encode(reclamos, "secreto-compartido-de-al-menos-32-bytes", algorithm="HS256",
                             headers={"kid": identidad.kid, "typ": "at+jwt"})) == 401  # algoritmo no permitido
    canal = puerta.get("/__interregion/trips/sa-east:000-" + "0" * 32,
                       headers={"Authorization": f"Bearer {ana.tokens['access_token']}",
                                "X-Inter-Region-Key": "incorrecta", "X-Entry-Region": "eu-west"})
    assert canal.status_code == 401
    reloj.adelantar(minutes=16)
    assert estado(juan.tokens["access_token"]) == 401  # vencido (15 min + 30 s de tolerancia)
    juan.renovar()
    assert estado(juan.tokens["access_token"]) == 200


def test_un_solo_salto_entre_regiones(sistema, ana, compartido):
    """Por el canal solo se aceptan operaciones de la tabla y solo sobre identificadores de la región destino."""
    clave = sistema.claves["canal"]
    puerta_eu = TestClient(sistema.regiones["eu-west"].puerta.app)
    encabezados = {"Authorization": f"Bearer {ana.tokens['access_token']}", "X-Inter-Region-Key": clave,
                   "X-Entry-Region": "eu-west"}
    reenvio = puerta_eu.get(f"/__interregion/shared/trips/{compartido}", headers=encabezados)
    assert reenvio.status_code == 404  # el viaje es de sa-east: no se reenvía otra vez
    assert motivos(sistema, "eu-west", "share.gateway_reject") == ["bad_region"]
    puerta_sa = TestClient(sistema.regiones["sa-east"].puerta.app)
    assert puerta_sa.get("/__interregion/panel", headers=encabezados).status_code == 404  # no está en la tabla


def test_mismo_identificador_en_otra_region_no_comparte_permisos(sistema, cliente, juan, compartido):
    """El principal es (homeRegion, userId): un usuario de eu-west con el mismo userId local no es Juan."""
    impostor = sistema.regiones["eu-west"].identidad.emitir_acceso(juan.user_id, "otro@example.com")
    encabezados = {"Authorization": f"Bearer {impostor}"}
    assert cliente.http.get(f"/trips/{compartido}", headers=encabezados).status_code == 404
    assert cliente.http.get(f"/shared/trips/{compartido}", headers=encabezados).status_code == 404
    assert motivos(sistema, "sa-east", "share.read") == ["owner_endpoint", "no_permission"]
