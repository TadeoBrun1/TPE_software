"""Transactional Outbox (ADR-0024 y ADR-0027): el evento se guarda en la misma transacción que el cambio y un
publicador lo envía después. Se marca enviado solo tras la confirmación del broker y sin retorno por falta de ruta;
si el proceso cae antes de marcarlo, se republica con el mismo eventId. Biblioteca técnica sin dominio.
"""
from __future__ import annotations

import json
from typing import Callable

from comun.infraestructura.broker import Broker, MensajeNoEnrutado, PublicacionNoConfirmada
from comun.infraestructura.db import BaseDatos, Transaccion
from comun.infraestructura.reloj import Reloj, iso

DDL_OUTBOX = [
    """CREATE TABLE IF NOT EXISTS outbox (
        event_id TEXT PRIMARY KEY,
        orden INTEGER NOT NULL,
        exchange TEXT NOT NULL,
        routing_key TEXT NOT NULL,
        cuerpo TEXT NOT NULL,
        encabezados TEXT NOT NULL,
        creado TEXT NOT NULL,
        enviado TEXT,
        intentos INTEGER NOT NULL DEFAULT 0,
        ultimo_error TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS outbox_pendientes ON outbox (enviado, orden)",
]


def agregar(tx: Transaccion, exchange: str, routing_key: str, cuerpo: dict, encabezados: dict, ahora: str):
    """Agrega un evento a la outbox dentro de la transacción del cambio. El contexto de traza se guarda con él."""
    siguiente = tx.uno("SELECT COALESCE(MAX(orden), 0) + 1 AS n FROM outbox")["n"]
    tx.ejecutar(
        "INSERT INTO outbox (event_id, orden, exchange, routing_key, cuerpo, encabezados, creado) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cuerpo["eventId"], siguiente, exchange, routing_key, json.dumps(cuerpo), json.dumps(encabezados), ahora),
    )


class PublicadorOutbox:
    def __init__(self, bases: list[BaseDatos], broker: Broker, reloj: Reloj, logger, lote: int = 100,
                 despues_de_confirmar: Callable[[str], None] | None = None):
        self.bases = bases
        self.broker = broker
        self.reloj = reloj
        self.logger = logger
        self.lote = lote
        # Punto de inyección de fallas para las pruebas: se llama entre la confirmación y la marca de enviado.
        self.despues_de_confirmar = despues_de_confirmar

    def publicar_pendientes(self) -> int:
        enviados = 0
        for base in self.bases:
            enviados += self._publicar_base(base)
        return enviados

    def _publicar_base(self, base: BaseDatos) -> int:
        try:
            with base.transaccion() as tx:
                pendientes = tx.todos(
                    "SELECT event_id, exchange, routing_key, cuerpo, encabezados FROM outbox "
                    "WHERE enviado IS NULL ORDER BY orden LIMIT ?", (self.lote,))
        except ConnectionError:
            return 0
        enviados = 0
        for fila in pendientes:
            cuerpo = json.loads(fila["cuerpo"])
            try:
                self.broker.publicar(fila["exchange"], fila["routing_key"], cuerpo, json.loads(fila["encabezados"]))
            except MensajeNoEnrutado as error:
                self._registrar_fallo(base, fila["event_id"], f"sin ruta: {error}")
                self.logger.alerta("outbox_mensaje_sin_ruta", eventId=fila["event_id"], routingKey=fila["routing_key"])
                break  # se conserva el orden de publicación
            except PublicacionNoConfirmada as error:
                self._registrar_fallo(base, fila["event_id"], f"sin confirmación: {error}")
                break
            if self.despues_de_confirmar:
                self.despues_de_confirmar(fila["event_id"])
            with base.transaccion() as tx:
                tx.ejecutar("UPDATE outbox SET enviado = ?, intentos = intentos + 1 WHERE event_id = ?",
                            (iso(self.reloj.ahora()), fila["event_id"]))
            enviados += 1
        return enviados

    def _registrar_fallo(self, base: BaseDatos, event_id: str, motivo: str):
        with base.transaccion() as tx:
            tx.ejecutar("UPDATE outbox SET intentos = intentos + 1, ultimo_error = ? WHERE event_id = ?",
                        (motivo, event_id))

    @staticmethod
    def antiguedad_pendientes(base: BaseDatos) -> int:
        with base.transaccion() as tx:
            return tx.uno("SELECT COUNT(*) AS n FROM outbox WHERE enviado IS NULL")["n"]
