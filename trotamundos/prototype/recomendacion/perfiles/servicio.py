"""Perfiles de preferencias (ADR-0081): perfil resumido por viajero en su región, opt-out y borrado (QA-14).

El perfil guarda métricas resumidas (contadores por proveedor, tipo y ciudad, y los precios de las ofertas
aceptadas), las preferencias explícitas y el ajuste del modelo por viajero. No guarda reservas, códigos, nombres
ni textos. Sobrevive al borrado de los viajes (ADR-0045) y se borra a pedido o con la cuenta.
"""
from __future__ import annotations

import json

from comun.infraestructura.db import BaseDatos, Transaccion
from comun.infraestructura.reloj import Reloj, iso

METRICAS_VACIAS = {"proveedores": {}, "tipos": {}, "ciudades": {}, "precios_aceptados": []}


class Perfiles:
    def __init__(self, base: BaseDatos, region: str, reloj: Reloj):
        self.base = base
        self.region = region
        self.reloj = reloj

    def obtener(self, tx: Transaccion, user_id: str) -> dict:
        """Perfil del viajero; si no existe se crea con la recomendación activada (opt-out, RF-09.4)."""
        fila = tx.uno("SELECT * FROM perfiles WHERE user_id = ?", (user_id,))
        if fila is None:
            tx.ejecutar("INSERT INTO perfiles (user_id, home_region, activada, preferencias, metricas, ajuste, "
                        "actualizado) VALUES (?, ?, 1, '{}', ?, '[]', ?)",
                        (user_id, self.region, json.dumps(METRICAS_VACIAS), iso(self.reloj.ahora())))
            fila = tx.uno("SELECT * FROM perfiles WHERE user_id = ?", (user_id,))
        return {"user_id": fila["user_id"], "activada": bool(fila["activada"]),
                "preferencias": json.loads(fila["preferencias"]), "metricas": json.loads(fila["metricas"]),
                "ajuste": json.loads(fila["ajuste"])}

    def guardar(self, tx: Transaccion, perfil: dict):
        tx.ejecutar("UPDATE perfiles SET activada = ?, preferencias = ?, metricas = ?, ajuste = ?, actualizado = ? "
                    "WHERE user_id = ?",
                    (1 if perfil["activada"] else 0, json.dumps(perfil["preferencias"]),
                     json.dumps(perfil["metricas"]), json.dumps(perfil["ajuste"]), iso(self.reloj.ahora()),
                     perfil["user_id"]))

    @staticmethod
    def registrar_hecho(perfil: dict, hecho: dict):
        """Una reserva real creada suma a las métricas del perfil (las propuestas no generan hechos)."""
        if hecho["changeType"] != "created" or hecho["status"] == "cancelled":
            return
        metricas = perfil["metricas"]
        for clave, valor in (("proveedores", hecho.get("provider")), ("tipos", hecho["type"]),
                             ("ciudades", hecho.get("arrivalCity") or hecho.get("locationCity"))):
            if valor:
                metricas[clave][valor] = metricas[clave].get(valor, 0) + 1

    @staticmethod
    def registrar_aceptacion(perfil: dict, oferta: dict):
        precios = perfil["metricas"]["precios_aceptados"]
        precios.append(oferta["price"]["amount"])
        del precios[:-20]  # se guardan los últimos 20 (suposición)
        proveedores = perfil["metricas"]["proveedores"]
        proveedores[oferta["provider"]] = proveedores.get(oferta["provider"], 0) + 1

    def preferencias_api(self, user_id: str) -> dict:
        with self.base.transaccion() as tx:
            perfil = self.obtener(tx, user_id)
        return {"enabled": perfil["activada"], **perfil["preferencias"]}

    def cambiar_preferencias(self, user_id: str, datos: dict) -> dict:
        """PUT: reemplaza las preferencias explícitas; `enabled` ausente conserva la activación actual."""
        with self.base.transaccion() as tx:
            perfil = self.obtener(tx, user_id)
            if "enabled" in datos:
                perfil["activada"] = bool(datos["enabled"])
            perfil["preferencias"] = {k: v for k, v in datos.items() if k != "enabled"}
            self.guardar(tx, perfil)
        return {"enabled": perfil["activada"], **perfil["preferencias"]}

    def borrar(self, user_id: str):
        """Borra perfil, preferencias, feedback, sugerencias y búsquedas del viajero en su región (QA-14)."""
        with self.base.transaccion() as tx:
            fila = tx.uno("SELECT activada FROM perfiles WHERE user_id = ?", (user_id,))
            for tabla in ("perfiles", "feedback", "sugerencias", "busquedas", "hechos_recibidos"):
                tx.ejecutar(f"DELETE FROM {tabla} WHERE user_id = ?", (user_id,))
            if fila is not None and not fila["activada"]:
                # Borrar no reactiva: se conserva solo la marca de desactivada, sin datos del perfil.
                perfil = self.obtener(tx, user_id)
                perfil["activada"] = False
                self.guardar(tx, perfil)
