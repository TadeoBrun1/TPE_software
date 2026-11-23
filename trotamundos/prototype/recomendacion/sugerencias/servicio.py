"""Sugerencias y feedback (ADR-0082 a ADR-0084, `specs/recommendation.md`).

* `procesar_pendientes`: agrupa las búsquedas pendientes por clave, busca una vez por clave y genera las sugerencias
  de cada búsqueda: filtro por límites explícitos, orden con la versión del modelo del viajero, 3 mostradas y el
  resto como candidatas; `suggestions.available.v1` en la outbox.
* `feedback`: aceptar publica `suggestion.accepted.v1`; rechazar ajusta el modelo del viajero y reordena; ajustar
  cambia las preferencias, cuenta como rechazo débil cada sugerencia mostrada que el ajuste excluye y reordena.
  Rechazar y ajustar responden con las sugerencias reordenadas (QA-13). Una oferta vencida responde 409.
* `entrenar`: trabajo diario por región; si la versión nueva no empeora con el feedback reservado, queda canario.
  También borra las sugerencias vencidas o no mostradas de más de 30 días (ADR-0081).
"""
from __future__ import annotations

import hashlib
import json
import random
import uuid
from datetime import timedelta

from comun.infraestructura.db import con_reintentos
from comun.infraestructura.reloj import iso, parsear
from comun.observabilidad import metricas
from recomendacion.busqueda.adaptadores import Consulta
from recomendacion.modelo import caracteristicas, entrenamiento, ranking
from recomendacion.sugerencias import eventos

MAX_CANDIDATAS = 10              # suposición: se guardan las 10 mejores (3 mostradas y 7 candidatas)
ESPERA_MAXIMA = timedelta(minutes=2)  # suposición: tope de la espera creciente entre reintentos (QA-17)
MIN_EJEMPLOS_ENTRENAMIENTO = 30  # suposición: con menos feedback no se entrena una versión nueva
RETENCION_SUGERENCIAS = timedelta(days=30)  # suposición (ADR-0081)


class NoEncontrada(Exception):
    pass


class EstadoInvalido(Exception):
    pass


def _fila_sugerencia(fila: dict) -> dict:
    return {**fila, "oferta": json.loads(fila["oferta"]), "caracteristicas": json.loads(fila["caracteristicas"]),
            "motivos": json.loads(fila["motivos"])}


class Sugerencias:
    def __init__(self, app, semilla: int | None = None):
        self.app = app
        self.azar = random.Random(semilla)

    # ------------------------------------------------------------------------------------------ generar

    def procesar_pendientes(self) -> int:
        app = self.app
        ahora = app.reloj.ahora()
        with app.base.transaccion() as tx:
            pendientes = tx.todos("SELECT * FROM busquedas WHERE estado = 'pendiente' AND "
                                  "(reintentar_desde IS NULL OR reintentar_desde <= ?) ORDER BY creada",
                                  (iso(ahora),))
        por_clave: dict[str, list[dict]] = {}
        for busqueda in pendientes:
            por_clave.setdefault(busqueda["clave"], []).append(busqueda)
        hechas = 0
        for clave, grupo in por_clave.items():
            resultado = app.buscador.buscar(Consulta(**json.loads(grupo[0]["consulta"])))  # una consulta por clave
            for busqueda in grupo:
                if resultado.pendiente:
                    self._reintentar(busqueda, resultado.reintentar_en)
                else:
                    con_reintentos(lambda b=busqueda: self._generar(b, resultado.ofertas, resultado.parcial))
                    hechas += 1
        return hechas

    def _reintentar(self, busqueda: dict, espera: timedelta | None):
        intentos = busqueda["intentos"] + 1
        espera = espera or min(timedelta(seconds=5 * 2 ** intentos), ESPERA_MAXIMA)
        with self.app.base.transaccion() as tx:
            tx.ejecutar("UPDATE busquedas SET intentos = ?, reintentar_desde = ? WHERE busqueda_id = ?",
                        (intentos, iso(self.app.reloj.ahora() + espera), busqueda["busqueda_id"]))
        metricas.incrementar("busqueda_pendiente_reintento")

    def _ordenar(self, perfil: dict, ofertas: list[dict], cancelada: dict, pesos: list[float]):
        ctx = caracteristicas.contexto(ofertas)
        candidatas = [(o, caracteristicas.vector(o, cancelada, perfil, ctx)) for o in ofertas
                      if caracteristicas.cumple_limites(o, perfil["preferencias"])]
        return ranking.ordenar(candidatas, pesos, perfil["ajuste"])

    def _generar(self, busqueda: dict, ofertas: list[dict], parcial: bool):
        app = self.app
        ahora = iso(app.reloj.ahora())
        busqueda = {**busqueda, "cancelada": json.loads(busqueda["cancelada"])}
        with app.base.transaccion() as tx:
            actual = tx.uno("SELECT estado FROM busquedas WHERE busqueda_id = ?", (busqueda["busqueda_id"],))
            if actual is None or actual["estado"] != "pendiente":
                return  # borrada (perfil o cuenta borrados) o ya generada
            if app.perfiles.eliminada(tx, busqueda["user_id"]):
                return  # la cuenta se eliminó mientras se buscaba (ADR-0085); el barrido borra la búsqueda
            perfil = app.perfiles.obtener(tx, busqueda["user_id"])
            if not perfil["activada"]:
                tx.ejecutar("UPDATE busquedas SET estado = 'descartada', terminada = ? WHERE busqueda_id = ?",
                            (ahora, busqueda["busqueda_id"]))
                return
            anteriores = [_fila_sugerencia(f) for f in tx.todos(
                "SELECT * FROM sugerencias WHERE busqueda_id = ?", (busqueda["busqueda_id"],))]
            if any(f["estado"] == "accepted" for f in anteriores):
                tx.ejecutar("UPDATE busquedas SET estado = 'lista', parcial = 0 WHERE busqueda_id = ?",
                            (busqueda["busqueda_id"],))
                return
            por_oferta = {(f["oferta"]["provider"], f["oferta"]["offerId"]): f for f in anteriores}
            version = app.registro.version_para(busqueda["user_id"], tx)
            ordenadas = self._ordenar(perfil, ofertas, busqueda["cancelada"], version["pesos"])[:MAX_CANDIDATAS]
            elegidos = ranking.elegir(ordenadas, self.azar)
            mostrados = {indice: (posicion, explora) for posicion, (indice, explora) in enumerate(elegidos, 1)}
            resto = iter(range(len(elegidos) + 1, len(ordenadas) + 1))
            for indice, (oferta, x, _) in enumerate(ordenadas):
                posicion, explora = mostrados[indice] if indice in mostrados else (next(resto), False)
                if (oferta["provider"], oferta["offerId"]) in por_oferta:
                    continue  # conserva ID, aceptación/rechazo y feedback de lo ya mostrado
                tx.ejecutar(
                    "INSERT INTO sugerencias (suggestion_id, busqueda_id, user_id, trip_id, cancelled_booking_id, "
                    "posicion, oferta, caracteristicas, version_modelo, exploracion, motivos, estado, mostrada, "
                    "creada) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), busqueda["busqueda_id"], busqueda["user_id"], busqueda["trip_id"],
                     busqueda["cancelled_booking_id"], posicion, json.dumps(oferta), json.dumps(x),
                     version["version_id"], 1 if explora else 0,
                     json.dumps(caracteristicas.motivos(oferta, x, perfil)),
                     "available" if indice in mostrados else "candidate", 1 if indice in mostrados else 0, ahora))
            if anteriores:
                self._reordenar(tx, perfil, busqueda["busqueda_id"])
            visibles = tx.todos("SELECT suggestion_id FROM sugerencias WHERE busqueda_id = ? AND estado = 'available'",
                               (busqueda["busqueda_id"],))
            estado = "pendiente" if parcial else ("lista" if visibles else "sin_resultados")
            tx.ejecutar("UPDATE busquedas SET estado = ?, parcial = ?, terminada = ?, reintentar_desde = ? "
                        "WHERE busqueda_id = ?",
                        (estado, int(parcial), ahora,
                         iso(app.reloj.ahora() + ESPERA_MAXIMA) if parcial else None, busqueda["busqueda_id"]))
            antes = {f["suggestion_id"] for f in anteriores if f["estado"] == "available"}
            despues = {f["suggestion_id"] for f in visibles}
            if visibles and (antes != despues or bool(busqueda["parcial"]) != parcial):
                eventos.sugerencias_disponibles(tx, busqueda, len(visibles), parcial, ahora)
        # QA-11 se mide desde la cancelación confirmada en el núcleo; el tramo hasta el push lo mide el notificador.
        desde = busqueda.get("cancelacion_confirmada") or busqueda["creada"]
        demora = (app.reloj.ahora() - parsear(desde)).total_seconds()
        metricas.observar("qa11_cancelacion_a_sugerencias_s", max(demora, 0.0))
        app.logger.info("sugerencias_generadas", busqueda=busqueda["busqueda_id"], mostradas=len(elegidos),
                        version=version["version_id"], parcial=parcial)

    # ------------------------------------------------------------------------------------------ leer

    def listar(self, user_id: str, trip_id: str) -> dict:
        """SuggestionList del viaje: las sugerencias mostradas que siguen cumpliendo los límites del viajero."""
        app = self.app
        with app.base.transaccion() as tx:
            perfil = app.perfiles.obtener(tx, user_id, crear=False)  # leer no crea perfiles
            busquedas = tx.todos("SELECT estado, parcial FROM busquedas WHERE user_id = ? AND trip_id = ?",
                                 (user_id, trip_id))
            filas = tx.todos("SELECT * FROM sugerencias WHERE user_id = ? AND trip_id = ? AND estado <> 'candidate' "
                             "ORDER BY cancelled_booking_id, posicion", (user_id, trip_id))
        estados = {b["estado"] for b in busquedas}
        if any(b["parcial"] for b in busquedas):
            estado = "partial"
        elif "pendiente" in estados:
            estado = "pending"
        elif "lista" in estados:
            estado = "ready"
        else:
            estado = "none"
        sugerencias = []
        for fila in map(_fila_sugerencia, filas):
            if fila["estado"] == "available" and not caracteristicas.cumple_limites(fila["oferta"],
                                                                                   perfil["preferencias"]):
                continue  # un ajuste posterior la excluye (QA-13)
            sugerencias.append(self.a_api(fila))
        return {"tripId": trip_id, "searchStatus": estado, "suggestions": sugerencias}

    @staticmethod
    def a_api(fila: dict) -> dict:
        oferta = fila["oferta"]
        datos = {"id": fila["suggestion_id"], "tripId": fila["trip_id"], "cancelledBookingId":
                 fila["cancelled_booking_id"], "rank": fila["posicion"], "status": fila["estado"],
                 "reasonCodes": fila["motivos"]}
        for campo in ("type", "provider", "startsAt", "endsAt", "timeZone", "arrivalTimeZone", "location",
                      "arrivalLocation", "stops", "price", "offerUrl", "expiresAt"):
            if oferta.get(campo) is not None:
                datos[campo] = oferta[campo]
        return datos

    # ------------------------------------------------------------------------------------------ feedback

    def feedback(self, user_id: str, suggestion_id: str, accion: str, motivo: str | None = None,
                 preferencias: dict | None = None) -> tuple[int, dict]:
        app = self.app
        ahora = iso(app.reloj.ahora())
        with app.base.transaccion() as tx:
            fila = tx.uno("SELECT * FROM sugerencias WHERE suggestion_id = ? AND user_id = ?", (suggestion_id, user_id))
            if fila is None or fila["estado"] == "candidate":
                raise NoEncontrada(suggestion_id)
            fila = _fila_sugerencia(fila)
            vence = fila["oferta"].get("expiresAt")
            if fila["estado"] == "available" and vence and parsear(vence) <= app.reloj.ahora():
                tx.ejecutar("UPDATE sugerencias SET estado = 'expired' WHERE suggestion_id = ?", (suggestion_id,))
                fila["estado"] = "expired"
        if fila["estado"] != "available":
            raise EstadoInvalido(fila["estado"])  # 409: ya respondida o la oferta venció
        with app.base.transaccion() as tx:
            actual = tx.uno("SELECT estado FROM sugerencias WHERE suggestion_id = ?", (suggestion_id,))
            if actual is None or actual["estado"] != "available":  # otra solicitud la respondió en el medio
                raise EstadoInvalido(actual["estado"] if actual else "deleted")
            perfil = app.perfiles.obtener(tx, user_id)
            pesos = app.registro.pesos_de(fila["version_modelo"], tx)
            if accion in ("accept", "reject"):
                etiqueta = 1 if accion == "accept" else 0
                tx.ejecutar("INSERT INTO feedback (feedback_id, user_id, suggestion_id, accion, motivo, "
                            "caracteristicas, "
                            "version_modelo, posicion, creado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (str(uuid.uuid4()), user_id, suggestion_id, accion, motivo,
                             json.dumps(fila["caracteristicas"]), fila["version_modelo"], fila["posicion"], ahora))
                perfil["ajuste"] = entrenamiento.paso_viajero(perfil["ajuste"], fila["caracteristicas"], etiqueta,
                                                              pesos)
            if accion == "accept":
                tx.ejecutar("UPDATE busquedas SET estado = 'lista', parcial = 0 WHERE busqueda_id = ?",
                            (fila["busqueda_id"],))
                tx.ejecutar("UPDATE sugerencias SET estado = 'accepted' WHERE suggestion_id = ?", (suggestion_id,))
                tx.ejecutar("UPDATE sugerencias SET estado = 'expired' WHERE busqueda_id = ? AND suggestion_id <> ? "
                            "AND estado IN ('available', 'candidate')", (fila["busqueda_id"], suggestion_id))
                app.perfiles.registrar_aceptacion(perfil, fila["oferta"])
                app.perfiles.guardar(tx, perfil)
                correlacion = tx.uno("SELECT correlation_id FROM busquedas WHERE busqueda_id = ?",
                                     (fila["busqueda_id"],))
                eventos.sugerencia_aceptada(tx, app.region, fila, fila["oferta"],
                                            correlacion["correlation_id"] if correlacion else None, ahora)
                metricas.incrementar("sugerencia_aceptada")
                return 202, {"suggestionId": suggestion_id, "status": "accepted",
                             "offerUrl": fila["oferta"]["offerUrl"]}
            if accion == "reject":
                tx.ejecutar("UPDATE sugerencias SET estado = 'rejected' WHERE suggestion_id = ?", (suggestion_id,))
                metricas.incrementar("sugerencia_rechazada")
            else:  # adjust: las preferencias nuevas cambian el filtro y lo que excluyen es un rechazo débil
                cambios = {k: v for k, v in (preferencias or {}).items() if k != "enabled"}
                perfil["preferencias"] = {**perfil["preferencias"], **cambios}
                self._rechazos_debiles(tx, perfil, fila["busqueda_id"], pesos, ahora)
            app.perfiles.guardar(tx, perfil)
            self._reordenar(tx, perfil, fila["busqueda_id"])
        return 200, self.listar(user_id, fila["trip_id"])

    def _rechazos_debiles(self, tx, perfil: dict, busqueda_id: str, pesos: list[float], ahora: str):
        """Ajustar también refina el modelo (enunciado, RF-09.3): cada sugerencia mostrada que las preferencias nuevas
        excluyen se guarda como feedback `adjust` (etiqueta 0, la mitad del peso) y mueve el modelo del viajero."""
        mostradas = [_fila_sugerencia(f) for f in tx.todos(
            "SELECT * FROM sugerencias WHERE busqueda_id = ? AND estado = 'available'", (busqueda_id,))]
        for fila in mostradas:
            if caracteristicas.cumple_limites(fila["oferta"], perfil["preferencias"]):
                continue
            tx.ejecutar("INSERT INTO feedback (feedback_id, user_id, suggestion_id, accion, motivo, caracteristicas, "
                        "version_modelo, posicion, creado) VALUES (?, ?, ?, 'adjust', NULL, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), perfil["user_id"], fila["suggestion_id"],
                         json.dumps(fila["caracteristicas"]), fila["version_modelo"], fila["posicion"], ahora))
            perfil["ajuste"] = entrenamiento.paso_viajero(perfil["ajuste"], fila["caracteristicas"], 0, pesos,
                                                          entrenamiento.PESO_AJUSTE)
            metricas.incrementar("sugerencia_excluida_por_ajuste")

    def _reordenar(self, tx, perfil: dict, busqueda_id: str):
        """Vuelve a ordenar lo pendiente del grupo con el ajuste y los límites actuales; las 3 mejores se muestran."""
        filas = [_fila_sugerencia(f) for f in tx.todos(
            "SELECT * FROM sugerencias WHERE busqueda_id = ? AND estado IN ('available', 'candidate')", (busqueda_id,))]
        if not filas:
            return
        resueltas = tx.uno("SELECT COUNT(*) AS n FROM sugerencias WHERE busqueda_id = ? AND estado IN "
                           "('accepted', 'rejected')", (busqueda_id,))["n"]
        ordenadas = sorted(
            filas, key=lambda f: (not caracteristicas.cumple_limites(f["oferta"], perfil["preferencias"]),
                                  -ranking.puntaje(f["caracteristicas"],
                                                   self.app.registro.pesos_de(f["version_modelo"], tx),
                                                   perfil["ajuste"]),
                                  f["oferta"]["price"]["amount"]))
        for orden, fila in enumerate(ordenadas):
            visible = orden < ranking.MOSTRAR and caracteristicas.cumple_limites(fila["oferta"], perfil["preferencias"])
            tx.ejecutar("UPDATE sugerencias SET posicion = ?, estado = ?, mostrada = CASE WHEN ? THEN 1 ELSE mostrada "
                        "END WHERE suggestion_id = ?",
                        (resueltas + orden + 1, "available" if visible else "candidate", 1 if visible else 0,
                         fila["suggestion_id"]))

    # ------------------------------------------------------------------------------------------ entrenar

    def entrenar(self) -> dict:
        """Trabajo diario por región (ADR-0083): entrena con el feedback de la región y publica un canario."""
        app = self.app
        if app.registro.canario() is not None:
            return {"resultado": "esperando_canario"}  # no reiniciar la muestra cada noche
        with app.base.transaccion() as tx:
            tx.ejecutar("DELETE FROM sugerencias WHERE estado IN ('expired', 'candidate') AND creada < ?",
                        (iso(app.reloj.ahora() - RETENCION_SUGERENCIAS),))
            filas = tx.todos("SELECT feedback_id, accion, caracteristicas, posicion FROM feedback "
                             "WHERE accion IN ('accept', 'reject', 'adjust')")
        ejemplos = [(json.loads(f["caracteristicas"]), 1 if f["accion"] == "accept" else 0,
                     entrenamiento.peso_por_posicion(f["posicion"] - 1)
                     * (entrenamiento.PESO_AJUSTE if f["accion"] == "adjust" else 1.0), f["feedback_id"])
                    for f in filas]
        if len(ejemplos) < MIN_EJEMPLOS_ENTRENAMIENTO:
            return {"resultado": "sin_datos_suficientes", "ejemplos": len(ejemplos)}
        prueba = [e[:3] for e in ejemplos if int(hashlib.sha256(e[3].encode()).hexdigest()[:4], 16) % 5 == 0]
        entrenar_con = [e[:3] for e in ejemplos if int(hashlib.sha256(e[3].encode()).hexdigest()[:4], 16) % 5 != 0]
        activa = app.registro.activa()
        pesos = entrenamiento.entrenar(entrenar_con, activa["pesos"])
        evaluacion = {"perdida_nueva": round(entrenamiento.perdida(prueba, pesos), 4),
                      "perdida_activa": round(entrenamiento.perdida(prueba, activa["pesos"]), 4),
                      "ejemplos_prueba": len(prueba)}
        if prueba and evaluacion["perdida_nueva"] > evaluacion["perdida_activa"]:
            return {"resultado": "descartada", **evaluacion}
        version = app.registro.publicar_canario(pesos, len(entrenar_con), evaluacion)
        return {"resultado": "canario", "version": version, **evaluacion}
