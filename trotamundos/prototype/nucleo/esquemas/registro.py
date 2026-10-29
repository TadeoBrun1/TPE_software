"""Registro de esquemas de `details` por configuración (ADR-0066).

Los esquemas se cargan al arrancar desde los archivos de `specs/schemas/` listados en la configuración; no se
compilan dentro del código. Agregar un medio nuevo es agregar su archivo y su identificador a la configuración.
"""
from __future__ import annotations

from contratos.esquemas import esquema_detalles

ESQUEMAS_POR_DEFECTO = ("flight.v1", "train.v1")


class DetallesInvalidos(ValueError):
    pass


class RegistroEsquemas:
    def __init__(self, identificadores=ESQUEMAS_POR_DEFECTO):
        self._validadores = {}
        for identificador in identificadores:
            validador = esquema_detalles(identificador)
            if validador is None:
                raise FileNotFoundError(f"no existe specs/schemas para {identificador}")
            self._validadores[identificador] = validador

    def validar(self, tipo: str, detalles: dict | None):
        if detalles is None:
            return
        identificador = detalles.get("schema", "")
        if identificador not in self._validadores:
            raise DetallesInvalidos(f"esquema de detalles no registrado: {identificador}")
        if identificador.split(".")[0] != tipo:
            raise DetallesInvalidos(f"el esquema {identificador} no corresponde al tipo {tipo}")
        errores = sorted(e.message for e in self._validadores[identificador].iter_errors(detalles))
        if errores:
            raise DetallesInvalidos("; ".join(errores))
