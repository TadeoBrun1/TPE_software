"""Gestor de vinculaciones de la ingesta: vigencia y estado técnico (ADR-0021). El núcleo es la autoridad; la
ingesta conserva la configuración técnica (fuente, remitentes permitidos, secreto de avisos, próxima reconciliación)
y comprueba la vigencia al iniciar cada consulta."""
from __future__ import annotations

import json

from comun.infraestructura.db import BaseDatos


class GestorVinculaciones:
    def __init__(self, base: BaseDatos):
        self.base = base

    def registrar(self, connection_id: str, user_id: str, home_region: str, provider_id: str, fuente: str,
                  remitentes: list[str] | None = None, secreto_avisos: str = ""):
        with self.base.transaccion() as tx:
            tx.ejecutar(
                "INSERT INTO vinculaciones (connection_id, user_id, home_region, provider_id, fuente, estado, revision, "
                "remitentes, secreto_avisos) VALUES (?, ?, ?, ?, ?, 'activa', 1, ?, ?) "
                "ON CONFLICT (connection_id) DO UPDATE SET estado = 'activa', revision = vinculaciones.revision + 1",
                (connection_id, user_id, home_region, provider_id, fuente, json.dumps(remitentes or []),
                 secreto_avisos))

    def vigente(self, connection_id: str) -> dict | None:
        with self.base.transaccion() as tx:
            fila = tx.uno("SELECT * FROM vinculaciones WHERE connection_id = ?", (connection_id,))
        return fila if fila and fila["estado"] == "activa" else None

    def obtener(self, connection_id: str) -> dict | None:
        with self.base.transaccion() as tx:
            return tx.uno("SELECT * FROM vinculaciones WHERE connection_id = ?", (connection_id,))

    def marcar(self, connection_id: str, estado: str):
        with self.base.transaccion() as tx:
            tx.ejecutar("UPDATE vinculaciones SET estado = ?, revision = revision + 1 WHERE connection_id = ?",
                        (estado, connection_id))

    def activas(self) -> list[dict]:
        with self.base.transaccion() as tx:
            return tx.todos("SELECT * FROM vinculaciones WHERE estado = 'activa'")
