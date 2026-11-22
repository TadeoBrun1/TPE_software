"""Proveedor de identidad de una región (ADR-0060), simulado con un subconjunto de OpenID Connect / OAuth 2.0.

* Guarda emails y credenciales solo de los usuarios de su región (CON-3).
* Emite tokens de acceso firmados (RS256) de 15 minutos con `typ: at+jwt`, `aud: trotamundos-api`, `userId`,
  `homeRegion` y `emailHmac` (HMAC del email verificado con la clave común a todas las regiones).
* Emite tokens de renovación opacos de 30 días, revocables.
* Publica sus claves públicas en `/jwks` para que las puertas de entrada validen sin consultarlo en cada solicitud.

Iteración 5 (ADR-0085): al recibir `account.deleted.v1` (cola `identity.accounts`) borra la cuenta, sus tokens de
renovación y su entrada del directorio global. En el sistema real esto lo hace un adaptador con la API de
administración del producto de identidad.

Simplificación del prototipo: el login usa usuario y contraseña directo (sin pantallas ni redirecciones OIDC).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from comun.infraestructura import db as db_mod
from comun.infraestructura.db import BaseDatos
from comun.infraestructura.reloj import Reloj, iso, parsear
from comun.observabilidad import Logger

VIDA_ACCESO = timedelta(minutes=15)
VIDA_RENOVACION = timedelta(days=30)  # suposición (ADR-0060)
AUDIENCIA = "trotamundos-api"

DDL = [
    """CREATE TABLE IF NOT EXISTS cuentas (
        user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, sal TEXT NOT NULL, clave TEXT NOT NULL,
        pais TEXT NOT NULL, bloqueada INTEGER NOT NULL DEFAULT 0, creado TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS renovaciones (
        token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, vence TEXT NOT NULL, revocado INTEGER NOT NULL)""",
]


def email_hmac(clave: bytes, email: str) -> str:
    return hmac.new(clave, email.strip().lower().encode(), hashlib.sha256).hexdigest()


def _hash_clave(clave: str, sal: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), 50_000).hex()


class ProveedorIdentidad:
    def __init__(self, region: str, base: BaseDatos, clave_email: bytes, registrar_en_directorio=None,
                 reloj: Reloj | None = None, logger: Logger | None = None, borrar_de_directorio=None):
        self.region = region
        self.emisor = f"https://id.{region}.trotamundos.example"
        self.base = base
        self.clave_email = clave_email
        self.registrar_en_directorio = registrar_en_directorio or (lambda email, region: None)
        self.borrar_de_directorio = borrar_de_directorio or (lambda email: None)
        self.reloj = reloj or Reloj()
        self.logger = logger or Logger("identidad", region)
        self.kid = f"{region}-1"
        self._privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        base.crear_esquema(DDL)
        self.app = self._crear_app()

    # ---------------------------------------------------------------- claves y tokens

    def jwks(self) -> dict:
        jwk = json.loads(RSAAlgorithm.to_jwk(self._privada.public_key()))
        jwk.update({"kid": self.kid, "alg": "RS256", "use": "sig"})
        return {"keys": [jwk]}

    def emitir_acceso(self, user_id: str, email: str, auth_time: int | None = None, **cambios) -> str:
        """Token de acceso. `auth_time` es el momento del inicio de sesión (OIDC): un token renovado conserva el del
        login original. `cambios` permite a las pruebas fabricar tokens inválidos (vencidos, otra audiencia)."""
        ahora = self.reloj.ahora()
        reclamos = {"iss": self.emisor, "sub": user_id, "aud": AUDIENCIA, "iat": int(ahora.timestamp()),
                    "auth_time": auth_time or int(ahora.timestamp()),
                    "nbf": int(ahora.timestamp()), "exp": int((ahora + VIDA_ACCESO).timestamp()),
                    "jti": uuid.uuid4().hex, "userId": user_id, "homeRegion": self.region,
                    "emailHmac": email_hmac(self.clave_email, email)}
        tipo = cambios.pop("typ", "at+jwt")
        reclamos.update(cambios)
        return jwt.encode(reclamos, self._privada, algorithm="RS256", headers={"kid": self.kid, "typ": tipo})

    def _emitir_renovacion(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with self.base.transaccion() as tx:
            tx.ejecutar("INSERT INTO renovaciones (token_hash, user_id, vence, revocado) VALUES (?, ?, ?, 0)",
                        (hashlib.sha256(token.encode()).hexdigest(), user_id,
                         iso(self.reloj.ahora() + VIDA_RENOVACION)))
        return token

    def _respuesta_tokens(self, cuenta: dict) -> dict:
        return {"access_token": self.emitir_acceso(cuenta["user_id"], cuenta["email"]), "token_type": "Bearer",
                "expires_in": int(VIDA_ACCESO.total_seconds()),
                "refresh_token": self._emitir_renovacion(cuenta["user_id"]), "userId": cuenta["user_id"],
                "homeRegion": self.region}

    # ---------------------------------------------------------------- operaciones

    def crear_cuenta(self, email: str, clave: str, pais: str) -> str:
        user_id = uuid.uuid4().hex
        sal = secrets.token_hex(16)
        with self.base.transaccion() as tx:
            if tx.uno("SELECT 1 AS x FROM cuentas WHERE email = ?", (email.strip().lower(),)):
                raise ValueError("cuenta existente")
            tx.ejecutar("INSERT INTO cuentas (user_id, email, sal, clave, pais, creado) VALUES (?, ?, ?, ?, ?, ?)",
                        (user_id, email.strip().lower(), sal, _hash_clave(clave, sal), pais, iso(self.reloj.ahora())))
        self.registrar_en_directorio(email, self.region)  # el directorio guarda solo HMAC(email) → región
        return user_id

    def login(self, email: str, clave: str) -> dict | None:
        with self.base.transaccion() as tx:
            cuenta = tx.uno("SELECT * FROM cuentas WHERE email = ?", (email.strip().lower(),))
        if cuenta is None or cuenta["bloqueada"] or not hmac.compare_digest(
                cuenta["clave"], _hash_clave(clave, cuenta["sal"])):
            return None
        return self._respuesta_tokens(cuenta)

    def renovar(self, token: str) -> dict | None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.base.transaccion() as tx:
            fila = tx.uno("SELECT r.*, c.email, c.bloqueada FROM renovaciones r JOIN cuentas c ON c.user_id = r.user_id "
                          "WHERE r.token_hash = ?", (token_hash,))
        if fila is None or fila["revocado"] or fila["bloqueada"] or parsear(fila["vence"]) < self.reloj.ahora():
            return None
        inicio = int((parsear(fila["vence"]) - VIDA_RENOVACION).timestamp())  # el login que emitió la renovación
        return {"access_token": self.emitir_acceso(fila["user_id"], fila["email"], auth_time=inicio),
                "token_type": "Bearer", "expires_in": int(VIDA_ACCESO.total_seconds())}

    def revocar(self, token: str):
        with self.base.transaccion() as tx:
            tx.ejecutar("UPDATE renovaciones SET revocado = 1 WHERE token_hash = ?",
                        (hashlib.sha256(token.encode()).hexdigest(),))

    def eliminar(self, user_id: str) -> bool:
        """Borra la cuenta y sus tokens de renovación (ADR-0085). Idempotente; devuelve si existía."""
        with self.base.transaccion() as tx:
            tx.ejecutar("DELETE FROM renovaciones WHERE user_id = ?", (user_id,))
            return tx.ejecutar("DELETE FROM cuentas WHERE user_id = ?", (user_id,)) > 0

    def procesar_baja(self, mensaje):
        """Consumidor de `account.deleted.v1` en `identity.accounts`. Si el directorio no responde, el mensaje se
        reentrega: borrar la cuenta otra vez no es un error y la entrada del directorio se borra al reintentar."""
        from contratos.esquemas import validar_evento

        validar_evento("account.deleted.v1", mensaje.cuerpo)
        if mensaje.cuerpo["homeRegion"] != self.region:
            return
        with self.base.transaccion() as tx:
            cuenta = tx.uno("SELECT email FROM cuentas WHERE user_id = ?", (mensaje.cuerpo["userId"],))
        if cuenta is not None:
            # El directorio guarda solo HMAC(email) → región. Se borra antes que la cuenta: si falla, se reintenta.
            self.borrar_de_directorio(cuenta["email"])
        self.eliminar(mensaje.cuerpo["userId"])
        self.logger.info("cuenta_eliminada_en_identidad", existia=cuenta is not None)

    def _crear_app(self) -> Starlette:
        proveedor = self

        async def cuentas(request: Request):
            datos = await request.json()
            try:
                user_id = proveedor.crear_cuenta(datos["email"], datos["password"], datos.get("country", ""))
            except (KeyError, ValueError):
                return JSONResponse({"code": "invalid_request", "message": "No se pudo crear la cuenta"}, 400)
            return JSONResponse({"userId": user_id, "homeRegion": proveedor.region}, status_code=201)

        async def token(request: Request):
            datos = await request.json()
            respuesta = proveedor.login(datos.get("email", ""), datos.get("password", "")) \
                if datos.get("grant_type", "password") == "password" else proveedor.renovar(datos.get("refresh_token", ""))
            if respuesta is None:  # respuesta genérica: no revela si la cuenta existe
                return JSONResponse({"error": "invalid_grant"}, status_code=401)
            return JSONResponse(respuesta)

        async def revocar(request: Request):
            proveedor.revocar((await request.json()).get("refresh_token", ""))
            return Response(status_code=204)

        async def jwks(request: Request):
            return JSONResponse(proveedor.jwks())

        return Starlette(routes=[Route("/accounts", cuentas, methods=["POST"]),
                                 Route("/token", token, methods=["POST"]),
                                 Route("/revoke", revocar, methods=["POST"]),
                                 Route("/jwks", jwks, methods=["GET"])])


def desde_entorno() -> ProveedorIdentidad:  # pragma: no cover - docker compose
    import urllib.request

    def registrar(email: str, region: str):
        pedido = urllib.request.Request(os.environ["URL_DIRECTORIO"], method="POST",
                                        data=json.dumps({"email": email, "region": region}).encode(),
                                        headers={"Content-Type": "application/json",
                                                 "X-Internal-Key": os.environ["CLAVE_INTERNA_DIRECTORIO"]})
        urllib.request.urlopen(pedido, timeout=5).read()

    def borrar(email: str):
        pedido = urllib.request.Request(os.environ["URL_DIRECTORIO"], method="DELETE",
                                        data=json.dumps({"email": email}).encode(),
                                        headers={"Content-Type": "application/json",
                                                 "X-Internal-Key": os.environ["CLAVE_INTERNA_DIRECTORIO"]})
        urllib.request.urlopen(pedido, timeout=5).read()

    from comun.infraestructura import broker as broker_mod
    from contratos.topologia import COLA_IDENTIDAD_CUENTAS, topologia_region

    region = os.environ["REGION"]
    proveedor = ProveedorIdentidad(region, db_mod.abrir(os.environ["BASE_IDENTIDAD"], f"{region}-identidad"),
                                   os.environ["CLAVE_EMAIL_HMAC"].encode(), registrar, borrar_de_directorio=borrar)
    if os.environ.get("BROKER"):  # bajas de cuentas (ADR-0085)
        broker = broker_mod.abrir(os.environ["BROKER"])
        broker.declarar(topologia_region())
        broker.consumir(COLA_IDENTIDAD_CUENTAS, proveedor.procesar_baja)
        broker.iniciar()
    return proveedor
