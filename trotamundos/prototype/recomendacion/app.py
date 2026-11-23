"""Composición del proceso de recomendación de una región (iteración 5, ADR-0081 a ADR-0084).

Módulos: `hechos` (consumidor de `booking.facts.v1`), `perfiles`, `busqueda` (puerto, adaptadores y buscador con
caché), `modelo` (características, ranking, entrenamiento y registro de versiones), `sugerencias` (generación,
feedback y eventos) y `api`. No lee la base del núcleo ni la de la ingesta, ni importa su código: se entera de las
cancelaciones por el broker y le avisa al núcleo de una aceptación con `suggestion.accepted.v1`.

Trabajadores: consumo de `recommendation.facts`, procesamiento de búsquedas pendientes, publicador de la outbox, el
entrenamiento diario y la evaluación del canario.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import timedelta

from comun.infraestructura import broker as broker_mod
from comun.infraestructura import db as db_mod
from comun.infraestructura.broker import Broker
from comun.infraestructura.db import BaseDatos
from comun.infraestructura.outbox import PublicadorOutbox
from comun.infraestructura.reloj import Reloj
from comun.observabilidad import Logger
from contratos.topologia import COLA_RECOMENDACION, topologia_region
from recomendacion.api.rutas import crear_app
from recomendacion.busqueda.adaptadores import AdaptadorBusquedaAerolinea, AdaptadorBusquedaHotel, PuertoBusqueda
from recomendacion.busqueda.buscador import Buscador
from recomendacion.datos.esquema import DDL_RECOMENDACION
from recomendacion.hechos.consumidor import ConsumidorHechos
from recomendacion.modelo.registro import MUESTRA_MINIMA, RegistroModelos
from recomendacion.perfiles.servicio import Perfiles
from recomendacion.sugerencias.servicio import Sugerencias
from simuladores.busqueda import BusquedaAerolineaSimulada, BusquedaHotelSimulada

EVALUACION_CANARIO = timedelta(minutes=5)  # suposición: cada cuánto se evalúa el canario (QA-15)


class Recomendacion:
    def __init__(self, region: str, base: BaseDatos, broker: Broker, adaptadores: list[PuertoBusqueda],
                 clave_puerta: str, reloj: Reloj | None = None, logger: Logger | None = None,
                 semilla: int | None = None, muestra_minima: int = MUESTRA_MINIMA):
        self.region = region
        self.base = base
        self.broker = broker
        self.clave_puerta = clave_puerta
        self.reloj = reloj or Reloj()
        self.logger = logger or Logger("recomendacion", region)
        base.crear_esquema(DDL_RECOMENDACION)
        self.perfiles = Perfiles(base, region, self.reloj)
        self.buscador = Buscador(adaptadores, self.reloj, self.logger)
        self.registro = RegistroModelos(base, self.reloj, self.logger, muestra_minima)
        self.sugerencias = Sugerencias(self, semilla)
        self.hechos = ConsumidorHechos(self)
        self.publicador = PublicadorOutbox([base], broker, self.reloj, self.logger)
        self.app = crear_app(self)
        self._activo = False
        self._ultima_evaluacion = None

    def preparar_mensajeria(self):
        self.broker.declarar(topologia_region())  # idempotente: no depende de que el núcleo arranque antes
        self.broker.consumir(COLA_RECOMENDACION, self.hechos.procesar, prefetch=20)

    def ciclo(self) -> int:
        """Un ciclo de trabajo (pruebas, demo y modo servicio): búsquedas pendientes, outbox, barrido de cuentas
        eliminadas y, cada 5 minutos, la evaluación del canario (QA-15: se decide apenas junta la muestra)."""
        self.perfiles.barrer_eliminadas()
        ahora = self.reloj.ahora()
        if self._ultima_evaluacion is None or ahora - self._ultima_evaluacion >= EVALUACION_CANARIO:
            self._ultima_evaluacion = ahora
            self.registro.evaluar_canario()
        return self.sugerencias.procesar_pendientes() + self.publicador.publicar_pendientes()

    def entrenar(self) -> dict:
        """Trabajo diario: decide sobre el canario y entrena una versión nueva. Si el canario todavía no juntó la
        muestra, se conserva y se posterga el entrenamiento. El feedback queda almacenado para el siguiente lote;
        no se garantiza publicar una nueva versión regional dentro de 24 h.
        """
        self.perfiles.purgar_marcas()  # marcas de cuentas eliminadas vencidas (ADR-0085)
        canario = self.registro.evaluar_canario()
        return {"canario": canario, "entrenamiento": self.sugerencias.entrenar()}

    def iniciar_trabajadores(self, intervalo: float = 0.5, hora_entrenamiento: int = 3, entrenar: bool = True):
        """En la arquitectura el entrenamiento es un único trabajo programado por región (ADR-0083). En el prototipo
        corre como hilo de la instancia que tiene `entrenar=True` (variable ENTRENAR); con varias instancias, solo una
        debe tenerlo."""
        self._activo = True
        self.broker.iniciar()

        def trabajar():
            while self._activo:
                try:
                    if self.ciclo() == 0:
                        time.sleep(intervalo)
                except Exception as error:  # el ciclo nunca debe morir; reintenta en el próximo
                    self.logger.error("ciclo_recomendacion_fallo", error=str(error))
                    time.sleep(1)

        def diaria():
            ultimo = None
            while self._activo:
                ahora = self.reloj.ahora()
                if ahora.hour == hora_entrenamiento and ultimo != ahora.date():
                    self.logger.info("entrenamiento_diario", **self.entrenar())
                    ultimo = ahora.date()
                time.sleep(60)

        threading.Thread(target=trabajar, daemon=True, name="recomendacion").start()
        if entrenar:
            threading.Thread(target=diaria, daemon=True, name="entrenamiento").start()

    def detener(self):
        self._activo = False
        self.broker.detener()


def apis_busqueda_simuladas(reloj: Reloj | None = None) -> dict:
    """Cuatro APIs de búsqueda sintéticas por región: dos cadenas de hoteles y dos aerolíneas (CON-1, CON-2)."""
    return {"hotel-sol": BusquedaHotelSimulada("hotel-sol", 60, reloj),
            "hotel-luna": BusquedaHotelSimulada("hotel-luna", 60, reloj),
            "aerolinea-sur": BusquedaAerolineaSimulada("aerolinea-sur", 60, reloj),
            "aerolinea-norte": BusquedaAerolineaSimulada("aerolinea-norte", 60, reloj)}


def adaptadores_para(apis: dict) -> list[PuertoBusqueda]:
    return [AdaptadorBusquedaHotel(api) if isinstance(api, BusquedaHotelSimulada) else AdaptadorBusquedaAerolinea(api)
            for api in apis.values()]


def desde_entorno() -> Recomendacion:  # pragma: no cover - docker compose
    region = os.environ["REGION"]
    reloj = Reloj()
    apis = apis_busqueda_simuladas(reloj)
    recomendacion = Recomendacion(region, db_mod.abrir(os.environ["BASE_RECOMENDACION"], f"{region}-recomendacion"),
                                  broker_mod.abrir(os.environ.get("BROKER", "memoria")), adaptadores_para(apis),
                                  os.environ["CLAVE_PUERTA"], reloj=reloj)
    recomendacion.apis = apis
    recomendacion.preparar_mensajeria()
    if os.environ.get("CLAVE_ADMIN"):
        from simuladores.admin import rutas_recomendacion

        recomendacion.app.router.routes.extend(rutas_recomendacion(recomendacion, os.environ["CLAVE_ADMIN"]))
    recomendacion.iniciar_trabajadores(entrenar=os.environ.get("ENTRENAR", "1") == "1")
    return recomendacion
