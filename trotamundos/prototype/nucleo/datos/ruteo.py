"""Ruteo de particiones (ADR-0042, módulo `ruteo-particiones` de la vista de módulos).

La base de la región se divide en 256 particiones lógicas según un hash del usuario; las particiones se reparten en
nodos físicos. Todo lo de un usuario vive en su partición y ninguna transacción cruza particiones.

Los identificadores de viajes, reservas e invitaciones llevan la partición del dueño (y los de viajes e
invitaciones, además, el prefijo de su región, ADR-0062). Así se lee por clave, sin buscar en todos los nodos:
`sa-east:017-6f1c...` es el viaje de un usuario de la partición 17 de la región sa-east.
"""
from __future__ import annotations

import hashlib
import re
import uuid

from comun.infraestructura.db import BaseDatos

PARTICIONES = 256
_ID_CON_REGION = re.compile(r"^(?P<region>[a-z]+-[a-z]+):(?P<particion>\d{3})-[0-9a-f]{32}$")
_ID_SIN_REGION = re.compile(r"^(?P<particion>\d{3})-[0-9a-f]{32}$")


class IdentificadorInvalido(ValueError):
    pass


def region_de_id(identificador: str) -> str | None:
    """Prefijo de región de un viaje o una invitación, o None si el formato no es válido."""
    coincidencia = _ID_CON_REGION.match(identificador or "")
    return coincidencia.group("region") if coincidencia else None


class RuteoParticiones:
    def __init__(self, region: str, nodos: list[BaseDatos]):
        self.region = region
        self.nodos = nodos

    @staticmethod
    def particion(user_id: str) -> int:
        return int(hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:8], 16) % PARTICIONES

    def nodo_de_particion(self, particion: int) -> BaseDatos:
        return self.nodos[particion % len(self.nodos)]

    def nodo(self, user_id: str) -> BaseDatos:
        return self.nodo_de_particion(self.particion(user_id))

    def particiones_de(self, nodo: BaseDatos) -> list[int]:
        indice = self.nodos.index(nodo)
        return [p for p in range(PARTICIONES) if p % len(self.nodos) == indice]

    def nuevo_id_con_region(self, user_id: str) -> str:
        return f"{self.region}:{self.particion(user_id):03d}-{uuid.uuid4().hex}"

    def nuevo_id(self, user_id: str) -> str:
        return f"{self.particion(user_id):03d}-{uuid.uuid4().hex}"

    def nodo_de_id(self, identificador: str) -> BaseDatos:
        """Nodo de un identificador de esta región. Lanza IdentificadorInvalido si no es de esta región."""
        coincidencia = _ID_CON_REGION.match(identificador or "")
        if coincidencia:
            if coincidencia.group("region") != self.region:
                raise IdentificadorInvalido(identificador)
            return self.nodo_de_particion(int(coincidencia.group("particion")))
        coincidencia = _ID_SIN_REGION.match(identificador or "")
        if coincidencia:
            return self.nodo_de_particion(int(coincidencia.group("particion")))
        raise IdentificadorInvalido(identificador)
