"""Registro de versiones del modelo regional (ADR-0083, QA-15).

* Siempre hay una versión activa (la inicial usa `PESOS_INICIALES`).
* Una versión nueva entra como canario para el 5 % de los viajeros, elegidos por un hash estable del `userId`.
* `evaluar_canario` compara su tasa de aceptación con la de la activa: con una muestra mínima, si cae más de un 10 %
  relativo se retira (vuelta atrás automática); si no, pasa a activa.
* Volver atrás es cambiar qué versión está activa: un cambio de datos, sin desplegar código (táctica *diferir el
  enlace*).
"""
from __future__ import annotations

import hashlib
import json
import uuid

from comun.infraestructura.db import BaseDatos
from comun.infraestructura.reloj import Reloj, iso
from recomendacion.modelo.caracteristicas import PESOS_INICIALES

PORCENTAJE_CANARIO = 5      # suposición (QA-15)
CAIDA_MAXIMA = 0.10         # suposición (QA-15): caída relativa de la tasa de aceptación
MUESTRA_MINIMA = 200        # suposición: sugerencias mostradas con la versión antes de decidir


def en_canario(user_id: str, porcentaje: int = PORCENTAJE_CANARIO) -> bool:
    return int(hashlib.sha256(user_id.encode()).hexdigest()[:8], 16) % 100 < porcentaje


class RegistroModelos:
    def __init__(self, base: BaseDatos, reloj: Reloj, logger, muestra_minima: int = MUESTRA_MINIMA):
        self.base = base
        self.reloj = reloj
        self.logger = logger
        self.muestra_minima = muestra_minima
        with base.transaccion() as tx:
            tx.ejecutar("CREATE TABLE IF NOT EXISTS historial_modelos_activos ("
                        "version_id TEXT PRIMARY KEY, anterior TEXT)")
        with base.transaccion() as tx:
            if not tx.uno("SELECT 1 AS x FROM versiones_modelo WHERE estado = 'activa'"):
                self._insertar(tx, "v0-inicial", PESOS_INICIALES, "activa", 0, {"origen": "pesos iniciales"})

    def _insertar(self, tx, version_id, pesos, estado, ejemplos, evaluacion):
        ahora = iso(self.reloj.ahora())
        tx.ejecutar("INSERT INTO versiones_modelo (version_id, pesos, estado, ejemplos, evaluacion, creada, "
                    "cambio_estado) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (version_id, json.dumps(pesos), estado, ejemplos, json.dumps(evaluacion), ahora, ahora))

    def _por_estado(self, tx, estado: str) -> dict | None:
        fila = tx.uno("SELECT * FROM versiones_modelo WHERE estado = ? ORDER BY creada DESC LIMIT 1", (estado,))
        return {**fila, "pesos": json.loads(fila["pesos"])} if fila else None

    def _leer(self, tx, funcion):
        """Usa la transacción del llamador si la hay (SQLite no admite transacciones anidadas)."""
        if tx is not None:
            return funcion(tx)
        with self.base.transaccion() as propia:
            return funcion(propia)

    def activa(self, tx=None) -> dict:
        return self._leer(tx, lambda t: self._por_estado(t, "activa"))

    def canario(self, tx=None) -> dict | None:
        return self._leer(tx, lambda t: self._por_estado(t, "canario"))

    def version_para(self, user_id: str, tx=None) -> dict:
        """La versión que ordena las sugerencias de este viajero (canario o activa)."""
        canario = self.canario(tx)
        return canario if canario and en_canario(user_id) else self.activa(tx)

    def pesos_de(self, version_id: str, tx=None) -> list[float]:
        return self._leer(tx, lambda t: json.loads(t.uno("SELECT pesos FROM versiones_modelo WHERE version_id = ?",
                                                          (version_id,))["pesos"]))

    def publicar_canario(self, pesos: list[float], ejemplos: int, evaluacion: dict) -> str:
        version_id = f"v{self.reloj.ahora():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"
        with self.base.transaccion() as tx:
            tx.ejecutar("UPDATE versiones_modelo SET estado = 'retirada', cambio_estado = ? WHERE estado = 'canario'",
                        (iso(self.reloj.ahora()),))  # a lo sumo un canario a la vez
            self._insertar(tx, version_id, pesos, "canario", ejemplos, evaluacion)
        self.logger.info("modelo_canario_publicado", version=version_id, ejemplos=ejemplos)
        return version_id

    def tasa(self, version_id: str) -> tuple[int, float]:
        """(sugerencias mostradas con la versión, tasa de aceptación)."""
        with self.base.transaccion() as tx:
            fila = tx.uno("SELECT COUNT(*) AS mostradas, SUM(CASE WHEN estado = 'accepted' THEN 1 ELSE 0 END) AS "
                          "aceptadas FROM sugerencias WHERE version_modelo = ? AND mostrada = 1", (version_id,))
        mostradas = fila["mostradas"] or 0
        return mostradas, ((fila["aceptadas"] or 0) / mostradas if mostradas else 0.0)

    def evaluar_canario(self) -> str:
        """Decide sobre el canario: `sin_canario`, `esperando_muestra`, `retirado` o `promovido`."""
        canario, activa = self.canario(), self.activa()
        if canario is None:
            return "sin_canario"
        mostradas, tasa_canario = self.tasa(canario["version_id"])
        _, tasa_activa = self.tasa(activa["version_id"])
        if mostradas < self.muestra_minima:
            return "esperando_muestra"
        ahora = iso(self.reloj.ahora())
        with self.base.transaccion() as tx:
            if tasa_activa and tasa_canario < tasa_activa * (1 - CAIDA_MAXIMA):
                tx.ejecutar("UPDATE versiones_modelo SET estado = 'retirada', cambio_estado = ? WHERE version_id = ?",
                            (ahora, canario["version_id"]))
                resultado = "retirado"
            else:
                tx.ejecutar("INSERT INTO historial_modelos_activos (version_id, anterior) VALUES (?, ?) "
                            "ON CONFLICT (version_id) DO NOTHING", (canario["version_id"], activa["version_id"]))
                tx.ejecutar("UPDATE versiones_modelo SET estado = 'retirada', cambio_estado = ? "
                            "WHERE estado = 'activa'",
                            (ahora,))
                tx.ejecutar("UPDATE versiones_modelo SET estado = 'activa', cambio_estado = ? WHERE version_id = ?",
                            (ahora, canario["version_id"]))
                resultado = "promovido"
        self.logger.info("modelo_canario_evaluado", version=canario["version_id"], resultado=resultado,
                         tasa_canario=round(tasa_canario, 3), tasa_activa=round(tasa_activa, 3))
        return resultado

    def volver_atras(self) -> str | None:
        """Vuelta atrás manual: retira el canario o, si no hay, reactiva la versión activa anterior."""
        ahora = iso(self.reloj.ahora())
        with self.base.transaccion() as tx:
            canario = self._por_estado(tx, "canario")
            if canario:
                tx.ejecutar("UPDATE versiones_modelo SET estado = 'retirada', cambio_estado = ? WHERE version_id = ?",
                            (ahora, canario["version_id"]))
                return canario["version_id"]
            activa = self._por_estado(tx, "activa")
            anterior = tx.uno("SELECT anterior AS version_id FROM historial_modelos_activos WHERE version_id = ?",
                              (activa["version_id"],))
            if not anterior:
                return None
            tx.ejecutar("UPDATE versiones_modelo SET estado = 'retirada', cambio_estado = ? WHERE version_id = ?",
                        (ahora, activa["version_id"]))
            tx.ejecutar("UPDATE versiones_modelo SET estado = 'activa', cambio_estado = ? WHERE version_id = ?",
                        (ahora, anterior["version_id"]))
            return anterior["version_id"]
