"""Contratos generados desde `specs/` (spec-driven): el prototipo no copia los esquemas, los lee de los archivos.

* Eventos: el payload de cada mensaje de `specs/asyncapi/*.v1.yaml`.
* API: los esquemas de `components.schemas` de `specs/openapi/itinerary-api.v1.yaml`.
* Detalles por tipo de reserva: `specs/schemas/details-<tipo>.v<n>.json` (ADR-0066).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import yaml
from jsonschema import Draft7Validator, Draft202012Validator

RAIZ_SPECS = Path(os.environ.get("TROTAMUNDOS_SPECS", Path(__file__).resolve().parents[2] / "specs"))

# Nombre lógico del evento → archivo AsyncAPI (el nombre lógico no es la routing key, ingestion-operations.md).
ARCHIVOS_EVENTOS = {
    "booking.change.detected.v1": "booking-change-detected.v1.yaml",
    "booking.changed.v1": "booking-confirmed.v1.yaml",
    "booking.facts.v1": "booking-facts.v1.yaml",
    "trip.changed.v1": "trip-changed.v1.yaml",
    "panel.changed.v1": "panel-changed.v1.yaml",
}


class ContratoInvalido(ValueError):
    def __init__(self, contrato: str, errores: list[str]):
        super().__init__(f"{contrato}: {'; '.join(errores)}")
        self.contrato = contrato
        self.errores = errores


@lru_cache(maxsize=None)
def _asyncapi(nombre_evento: str) -> dict:
    with open(RAIZ_SPECS / "asyncapi" / ARCHIVOS_EVENTOS[nombre_evento], encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


@lru_cache(maxsize=None)
def _validador_evento(nombre_evento: str) -> Draft7Validator:
    documento = _asyncapi(nombre_evento)
    canal = next(iter(documento["channels"].values()))
    referencia = canal["publish"]["message"]["$ref"].split("/")[-1]
    payload = documento["components"]["messages"][referencia]["payload"]
    return Draft7Validator(payload)


def validar_evento(nombre_evento: str, payload: dict) -> None:
    errores = sorted(e.message for e in _validador_evento(nombre_evento).iter_errors(payload))
    if errores:
        raise ContratoInvalido(nombre_evento, errores)


def version_contrato(nombre_evento: str) -> str:
    return _asyncapi(nombre_evento)["info"]["version"]


@lru_cache(maxsize=None)
def openapi() -> dict:
    with open(RAIZ_SPECS / "openapi" / "itinerary-api.v1.yaml", encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


@lru_cache(maxsize=None)
def _validador_api(nombre_esquema: str) -> Draft7Validator:
    documento = openapi()
    esquema = {"$ref": f"#/components/schemas/{nombre_esquema}", "components": documento["components"]}
    return Draft7Validator(esquema)


def validar_api(nombre_esquema: str, valor) -> None:
    """Valida un cuerpo de la API contra `components.schemas.<nombre>` de la OpenAPI."""
    errores = sorted(e.message for e in _validador_api(nombre_esquema).iter_errors(valor))
    if errores:
        raise ContratoInvalido(nombre_esquema, errores)


@lru_cache(maxsize=None)
def esquema_detalles(identificador: str) -> Draft202012Validator | None:
    """`train.v1` → validador de `specs/schemas/details-train.v1.json`, o None si no existe el archivo."""
    tipo, _, version = identificador.partition(".")
    ruta = RAIZ_SPECS / "schemas" / f"details-{tipo}.{version}.json"
    if not ruta.exists():
        return None
    with open(ruta, encoding="utf-8") as archivo:
        return Draft202012Validator(json.load(archivo))
