"""Biblioteca común de observabilidad (ADR-0067, vista de módulos).

Propaga el identificador de correlación y el contexto de traza W3C (`traceparent`), registra logs estructurados
sin datos personales y lleva métricas simples por proceso. No contiene lógica de dominio.
"""
from __future__ import annotations

import json
import re
import secrets
import sys
import threading
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar

# Claves que nunca se escriben en un log (ADR-0067: sin emails, nombres, códigos de reserva ni tokens).
_CLAVES_PROHIBIDAS = {
    "email", "password", "contrasena", "token", "accesstoken", "refreshtoken", "authorization", "secret",
    "secreto", "ticket", "notes", "notas", "providerreference", "externalreservationid", "displayname",
    "nombre", "cuerpo", "body",
}

_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")

contexto_traza: ContextVar[str | None] = ContextVar("contexto_traza", default=None)
contexto_correlacion: ContextVar[str | None] = ContextVar("contexto_correlacion", default=None)


def nuevo_correlation_id() -> str:
    return str(uuid.uuid4())


def nuevo_traceparent() -> str:
    """Abre una traza nueva (W3C Trace Context)."""
    return f"00-{secrets.token_hex(16)}-{secrets.token_hex(8)}-01"


def traceparent_valido(valor: str | None) -> bool:
    return bool(valor) and bool(_TRACEPARENT.match(valor))


def continuar_traza(traceparent: str | None) -> str:
    """Devuelve un tramo hijo de la traza recibida, o una traza nueva si falta o es inválida.

    Nunca se rechaza un mensaje por no traer el contexto (ingestion-operations.md, sección 5).
    """
    if not traceparent_valido(traceparent):
        metricas.incrementar("traza_ausente_o_invalida")
        return nuevo_traceparent()
    trace_id = _TRACEPARENT.match(traceparent).group(1)  # type: ignore[union-attr]
    return f"00-{trace_id}-{secrets.token_hex(8)}-01"


def trace_id(traceparent: str | None) -> str | None:
    if not traceparent_valido(traceparent):
        return None
    return _TRACEPARENT.match(traceparent).group(1)  # type: ignore[union-attr]


def _limpiar(valor):
    if isinstance(valor, dict):
        return {k: ("[omitido]" if k.lower().replace("_", "") in _CLAVES_PROHIBIDAS else _limpiar(v))
                for k, v in valor.items()}
    if isinstance(valor, list):
        return [_limpiar(v) for v in valor]
    return valor


class Logger:
    """Logs estructurados en JSON, una línea por evento."""

    def __init__(self, proceso: str, region: str | None = None, salida=sys.stdout):
        self.proceso = proceso
        self.region = region
        self.salida = salida  # None: sin salida (pruebas); los registros quedan en memoria
        self.registros: list[dict] = []  # copia en memoria, útil para pruebas
        self._lock = threading.Lock()

    def info(self, evento: str, **campos):
        self._escribir("info", evento, campos)

    def alerta(self, evento: str, **campos):
        self._escribir("alerta", evento, campos)

    def error(self, evento: str, **campos):
        self._escribir("error", evento, campos)

    def _escribir(self, nivel: str, evento: str, campos: dict):
        registro = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "nivel": nivel,
            "proceso": self.proceso,
            "region": self.region,
            "evento": evento,
            "traceId": trace_id(contexto_traza.get()),
            "correlationId": contexto_correlacion.get(),
            **_limpiar(campos),
        }
        with self._lock:
            self.registros.append(registro)
            if self.salida is not None:
                try:
                    self.salida.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
                except ValueError:
                    pass


class Metricas:
    """Contadores y duraciones en memoria. Cada proceso los expone en GET /metrics."""

    def __init__(self):
        self._lock = threading.Lock()
        self.contadores: dict[str, int] = defaultdict(int)
        self.duraciones: dict[str, list[float]] = defaultdict(list)

    def incrementar(self, nombre: str, cantidad: int = 1):
        with self._lock:
            self.contadores[nombre] += cantidad

    def observar(self, nombre: str, segundos: float):
        with self._lock:
            self.duraciones[nombre].append(segundos)

    def resumen(self) -> dict:
        with self._lock:
            duraciones = {}
            for nombre, valores in self.duraciones.items():
                ordenados = sorted(valores)
                p95 = ordenados[min(len(ordenados) - 1, int(len(ordenados) * 0.95))]
                duraciones[nombre] = {"n": len(valores), "max": max(valores), "p95": p95}
            return {"contadores": dict(self.contadores), "duraciones": duraciones}


metricas = Metricas()
