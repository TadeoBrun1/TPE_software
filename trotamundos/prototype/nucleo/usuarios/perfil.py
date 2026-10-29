"""Perfil del usuario (región, idioma y país, ADR-0065) y marcadores de viajes compartidos conmigo (ADR-0062).

Las credenciales y el email viven en el proveedor de identidad de la región (ADR-0060), no acá.
El marcador solo guarda el identificador del viaje y la fecha de aceptación: no da permiso ni datos del itinerario.
"""
from __future__ import annotations

from comun.infraestructura.db import Transaccion


def asegurar(tx: Transaccion, user_id: str, region: str, ahora: str):
    tx.ejecutar("INSERT INTO usuarios (user_id, home_region, creado) VALUES (?, ?, ?) ON CONFLICT (user_id) DO NOTHING",
                (user_id, region, ahora))


def agregar_referencia(tx: Transaccion, user_id: str, trip_id: str, aceptada_en: str) -> dict:
    tx.ejecutar("INSERT INTO referencias_compartidas (user_id, trip_id, aceptada_en) VALUES (?, ?, ?) "
                "ON CONFLICT (user_id, trip_id) DO NOTHING", (user_id, trip_id, aceptada_en))
    fila = tx.uno("SELECT trip_id, aceptada_en FROM referencias_compartidas WHERE user_id = ? AND trip_id = ?",
                  (user_id, trip_id))
    return {"tripId": fila["trip_id"], "acceptedAt": fila["aceptada_en"]}


def listar_referencias(tx: Transaccion, user_id: str) -> list[dict]:
    filas = tx.todos("SELECT trip_id, aceptada_en FROM referencias_compartidas WHERE user_id = ? ORDER BY aceptada_en",
                     (user_id,))
    return [{"tripId": f["trip_id"], "acceptedAt": f["aceptada_en"]} for f in filas]


def borrar_referencia(tx: Transaccion, user_id: str, trip_id: str):
    tx.ejecutar("DELETE FROM referencias_compartidas WHERE user_id = ? AND trip_id = ?", (user_id, trip_id))
