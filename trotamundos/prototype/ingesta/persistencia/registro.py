"""Registro de sincronización de la ingesta (ADR-0024): almacenamiento propio, no compartido con el núcleo.

Resultados de cada página, casos pendientes, outbox y avance del cursor se confirman en una sola transacción. Una
ejecución que perdió su lease (versión del cursor) no puede confirmar avance. Un elemento reobtenido se reconoce por
su clave de negocio y no genera otra publicación.
"""
from __future__ import annotations

import json
import uuid

from comun.infraestructura import outbox
from comun.infraestructura.db import BaseDatos
from comun.observabilidad import continuar_traza
from contratos.topologia import EXCHANGE_INGESTA, routing_key_novedad

DDL_INGESTA = [
    """CREATE TABLE IF NOT EXISTS vinculaciones (
        connection_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, home_region TEXT NOT NULL, provider_id TEXT NOT NULL,
        fuente TEXT NOT NULL, estado TEXT NOT NULL, revision INTEGER NOT NULL, remitentes TEXT,
        proxima_reconciliacion TEXT, secreto_avisos TEXT)""",
    """CREATE TABLE IF NOT EXISTS cursores (
        connection_id TEXT PRIMARY KEY, valor TEXT, version INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS trabajos (
        trabajo_id TEXT PRIMARY KEY, connection_id TEXT NOT NULL, tipo TEXT NOT NULL, estado TEXT NOT NULL,
        correlation_id TEXT NOT NULL, traceparent TEXT NOT NULL, creado TEXT NOT NULL, reintentar_desde TEXT,
        intentos INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS avisos_recibidos (
        aviso_id TEXT PRIMARY KEY, provider_id TEXT NOT NULL, connection_id TEXT NOT NULL, recibido TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS resultados (
        resultado_id TEXT PRIMARY KEY, connection_id TEXT NOT NULL, item_id TEXT NOT NULL, tipo TEXT NOT NULL,
        motivo TEXT, event_id TEXT, registrado TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS claves_publicadas (
        connection_id TEXT NOT NULL, business_change_key TEXT NOT NULL, event_id TEXT NOT NULL,
        PRIMARY KEY (connection_id, business_change_key))""",
    *outbox.DDL_OUTBOX,
]


class LeasePerdido(Exception):
    """Otra ejecución avanzó el cursor: esta no puede confirmar."""


class Registro:
    def __init__(self, base: BaseDatos):
        self.base = base
        base.crear_esquema(DDL_INGESTA)

    def leer_cursor(self, connection_id: str) -> tuple[str | None, int]:
        with self.base.transaccion() as tx:
            tx.ejecutar("INSERT INTO cursores (connection_id, valor, version) VALUES (?, NULL, 0) "
                        "ON CONFLICT (connection_id) DO NOTHING", (connection_id,))
            fila = tx.uno("SELECT valor, version FROM cursores WHERE connection_id = ?", (connection_id,))
        return fila["valor"], fila["version"]

    def confirmar_pagina(self, connection_id: str, version: int, cursor_nuevo: str, resultados: list,
                         trabajos: list[str], ahora: str, traceparent: str) -> dict:
        """Una transacción: resultados + outbox + avance del cursor (con control de lease) + trabajos hechos."""
        resumen = {"publicados": 0, "repetidos": 0, "descartes": 0, "pendientes": 0}
        with self.base.transaccion() as tx:
            if tx.ejecutar("UPDATE cursores SET valor = ?, version = version + 1 WHERE connection_id = ? AND version = ?",
                           (cursor_nuevo, connection_id, version)) == 0:
                raise LeasePerdido(connection_id)
            for item_id, resultado in resultados:
                event_id = None
                tipo = resultado.tipo
                if tipo == "evento":
                    previo = tx.uno("SELECT event_id FROM claves_publicadas WHERE connection_id = ? "
                                    "AND business_change_key = ?", (connection_id, resultado.business_change_key))
                    if previo:  # elemento reobtenido: no se publica otra vez
                        tipo, event_id = "repetido", previo["event_id"]
                        resumen["repetidos"] += 1
                    else:
                        evento = resultado.evento
                        event_id = evento["eventId"]
                        tx.ejecutar("INSERT INTO claves_publicadas (connection_id, business_change_key, event_id) "
                                    "VALUES (?, ?, ?)", (connection_id, resultado.business_change_key, event_id))
                        outbox.agregar(tx, EXCHANGE_INGESTA, routing_key_novedad(evento["homeRegion"], evento["userId"]),
                                       evento, {"traceparent": continuar_traza(traceparent)}, ahora)
                        resumen["publicados"] += 1
                else:
                    resumen["descartes" if tipo == "descarte" else "pendientes"] += 1
                tx.ejecutar("INSERT INTO resultados (resultado_id, connection_id, item_id, tipo, motivo, event_id, "
                            "registrado) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (str(uuid.uuid4()), connection_id, item_id, tipo, resultado.motivo, event_id, ahora))
            for trabajo_id in trabajos:
                tx.ejecutar("UPDATE trabajos SET estado = 'hecho' WHERE trabajo_id = ?", (trabajo_id,))
        return resumen

    def resultados(self, connection_id: str) -> list[dict]:
        with self.base.transaccion() as tx:
            return tx.todos("SELECT * FROM resultados WHERE connection_id = ? ORDER BY registrado", (connection_id,))

    @staticmethod
    def resumen_json(valor) -> str:
        return json.dumps(valor)
