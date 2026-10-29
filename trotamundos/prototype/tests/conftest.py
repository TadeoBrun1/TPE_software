"""Fixtures: un sistema completo de dos regiones (sa-east y eu-west) en el mismo proceso, con reloj fijo."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comun.infraestructura.reloj import RelojFijo  # noqa: E402
from sistema import Sistema  # noqa: E402

INICIO = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


class Usuario:
    def __init__(self, cliente: "Cliente", email: str, region: str, tokens: dict, clave: str):
        self.cliente = cliente
        self.email = email
        self.region = region
        self.user_id = tokens["userId"]
        self.tokens = tokens
        self._clave = clave

    def renovar(self):
        """Token de acceso nuevo con el de renovación (el de acceso dura 15 minutos)."""
        r = self.cliente.http.post(f"/id/{self.region}/token",
                                   json={"grant_type": "refresh_token", "refresh_token": self.tokens["refresh_token"]})
        assert r.status_code == 200, r.text
        self.tokens = r.json()

    def ingresar(self):
        """Inicio de sesión de nuevo (el token de renovación dura 30 días)."""
        r = self.cliente.http.post(f"/id/{self.region}/token", json={"email": self.email, "password": self._clave})
        assert r.status_code == 200, r.text
        self.tokens = r.json()

    @property
    def h(self) -> dict:
        return {"Authorization": f"Bearer {self.tokens['access_token']}"}

    def get(self, ruta, **kw):
        return self.cliente.http.get(ruta, headers={**self.h, **kw.pop("headers", {})}, **kw)

    def post(self, ruta, json=None, **kw):
        return self.cliente.http.post(ruta, json=json, headers={**self.h, **kw.pop("headers", {})}, **kw)

    def patch(self, ruta, json=None, **kw):
        return self.cliente.http.patch(ruta, json=json, headers={**self.h, **kw.pop("headers", {})}, **kw)

    def delete(self, ruta, **kw):
        return self.cliente.http.delete(ruta, headers={**self.h, **kw.pop("headers", {})}, **kw)

    def reserva(self, clave: str, **datos):
        cuerpo = {"type": "hotel", "startsAt": "2026-11-10T15:00:00+01:00", "endsAt": "2026-11-14T11:00:00+01:00",
                  "location": "Madrid", **datos}
        respuesta = self.post("/bookings", cuerpo, headers={"Idempotency-Key": clave})
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()


class Cliente:
    """Cliente HTTP contra la entrada global, como lo usarían la web o la app."""

    def __init__(self, sistema: Sistema):
        self.sistema = sistema
        self.http = TestClient(sistema.entrada.app)

    def registrar(self, email: str, pais: str, clave: str = "clave-segura") -> Usuario:
        region = self.http.post("/login/region", json={"email": email, "country": pais}).json()["region"]
        assert self.http.post(f"/id/{region}/accounts",
                              json={"email": email, "password": clave, "country": pais}).status_code == 201
        tokens = self.http.post(f"/id/{region}/token", json={"email": email, "password": clave}).json()
        return Usuario(self, email, region, tokens, clave)


@pytest.fixture
def reloj():
    return RelojFijo(INICIO)


@pytest.fixture
def sistema(tmp_path, reloj):
    return Sistema(str(tmp_path), reloj=reloj, salida_logs=None)


@pytest.fixture
def cliente(sistema):
    return Cliente(sistema)


@pytest.fixture
def juan(cliente):
    return cliente.registrar("juan@example.com", "AR")  # región sa-east


@pytest.fixture
def ana(cliente):
    return cliente.registrar("ana@example.com", "ES")   # región eu-west
