"""Validación de tokens en la puerta de entrada (perfil de ADR-0060) y tickets SSE.

Comprobaciones, en orden, antes de atribuir una identidad:
1. `typ=at+jwt`, `aud` contiene `trotamundos-api` e `iss` es un emisor registrado (se rechazan ID tokens, tokens de
   renovación y tickets SSE aunque tengan firma válida).
2. Firma con la clave de la configuración confiable del emisor; `kid` solo elige dentro de esas claves; lista de
   algoritmos permitidos por emisor; nunca claves o URLs propuestas por el token.
3. `exp` y `nbf` con 30 s de tolerancia de reloj.
4. `sub`, `userId` y `homeRegion` presentes; la región del emisor coincide con `homeRegion`.
El principal canónico es `(homeRegion, userId)`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta

import jwt
from jwt.algorithms import RSAAlgorithm

TOLERANCIA_RELOJ_S = 30
AUDIENCIA_API = "trotamundos-api"
AUDIENCIA_SSE = "trotamundos-sse"
TIPO_TICKET = "trotamundos-sse-ticket+jwt"
VIDA_TICKET = timedelta(seconds=30)


class TokenInvalido(Exception):
    pass


@dataclass
class Identidad:
    region: str
    user_id: str
    issuer: str
    email_hmac: str | None


@dataclass
class Emisor:
    iss: str
    region: str
    claves: dict  # kid → clave pública
    algoritmos: tuple = ("RS256",)


class Emisores:
    """Configuración confiable de emisores (uno por región). Las claves se cargan del `/jwks` de cada proveedor."""

    def __init__(self):
        self._por_iss: dict[str, Emisor] = {}

    def registrar(self, iss: str, region: str, jwks: dict):
        claves = {k["kid"]: RSAAlgorithm.from_jwk(json.dumps(k)) for k in jwks["keys"]}
        self._por_iss[iss] = Emisor(iss, region, claves)

    def validar(self, token: str, ahora) -> Identidad:
        try:
            encabezado = jwt.get_unverified_header(token)
            sin_verificar = jwt.decode(token, options={"verify_signature": False})
        except jwt.PyJWTError as error:
            raise TokenInvalido("formato") from error
        if encabezado.get("typ") != "at+jwt":
            raise TokenInvalido("typ")  # ID token, ticket SSE u otro tipo
        emisor = self._por_iss.get(sin_verificar.get("iss"))
        if emisor is None:
            raise TokenInvalido("emisor desconocido")
        if encabezado.get("alg") not in emisor.algoritmos:
            raise TokenInvalido("algoritmo no permitido")
        clave = emisor.claves.get(encabezado.get("kid"))
        if clave is None:
            raise TokenInvalido("clave desconocida")
        try:
            reclamos = jwt.decode(token, clave, algorithms=list(emisor.algoritmos), audience=AUDIENCIA_API,
                                  issuer=emisor.iss, leeway=TOLERANCIA_RELOJ_S,
                                  options={"require": ["exp", "sub", "iss", "aud"], "verify_iat": False,
                                           "verify_exp": False, "verify_nbf": False})
        except jwt.PyJWTError as error:
            raise TokenInvalido(type(error).__name__) from error
        momento = ahora.timestamp()
        if reclamos["exp"] + TOLERANCIA_RELOJ_S < momento:
            raise TokenInvalido("vencido")
        if "nbf" in reclamos and reclamos["nbf"] - TOLERANCIA_RELOJ_S > momento:
            raise TokenInvalido("todavía no válido")
        if not reclamos.get("userId") or not reclamos.get("homeRegion"):
            raise TokenInvalido("faltan reclamos")
        if reclamos["homeRegion"] != emisor.region:
            raise TokenInvalido("la región no corresponde al emisor")
        return Identidad(reclamos["homeRegion"], reclamos["userId"], emisor.iss, reclamos.get("emailHmac"))


class Tickets:
    """Tickets SSE: firmados por la puerta, con prefijo de región, 30 s de vigencia y perfil propio."""

    def __init__(self, region: str, secreto: str):
        self.region = region
        self.secreto = secreto
        self.emisor = f"puerta-{region}"

    def emitir(self, identidad: Identidad, ahora) -> tuple[str, str]:
        vence = ahora + VIDA_TICKET
        reclamos = {"iss": self.emisor, "aud": AUDIENCIA_SSE, "sub": identidad.user_id, "userId": identidad.user_id,
                    "homeRegion": identidad.region, "exp": int(vence.timestamp())}
        firmado = jwt.encode(reclamos, self.secreto, algorithm="HS256", headers={"typ": TIPO_TICKET})
        return f"{self.region}:{firmado}", vence.strftime("%Y-%m-%dT%H:%M:%SZ")

    def validar(self, ticket: str, ahora) -> Identidad:
        region, _, firmado = (ticket or "").partition(":")
        if region != self.region:
            raise TokenInvalido("ticket de otra región")
        try:
            if jwt.get_unverified_header(firmado).get("typ") != TIPO_TICKET:
                raise TokenInvalido("typ")
            reclamos = jwt.decode(firmado, self.secreto, algorithms=["HS256"], audience=AUDIENCIA_SSE,
                                  issuer=self.emisor, options={"verify_exp": False})
        except jwt.PyJWTError as error:
            raise TokenInvalido(type(error).__name__) from error
        if reclamos["exp"] < ahora.timestamp():
            raise TokenInvalido("ticket vencido")
        if reclamos["homeRegion"] != self.region:
            raise TokenInvalido("la región no corresponde")
        return Identidad(reclamos["homeRegion"], reclamos["userId"], self.emisor, None)
