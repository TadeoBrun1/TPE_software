"""Composición de la ingesta de una región (iteración 2, vista de ingesta).

Módulos: `avisos/receptor`, `planificacion/planificador`, `coordinacion/coordinador`, `vinculaciones/gestor`,
`adaptadores/acceso`, `procesamiento/tuberia`, `persistencia/registro` y `mensajeria/publicador`.
La ingesta no escribe en la base del núcleo ni importa su código: le entrega novedades por el broker.
"""
from __future__ import annotations

import os
import threading
import time

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from comun.infraestructura import broker as broker_mod
from comun.infraestructura import db as db_mod
from comun.infraestructura.broker import Broker
from comun.infraestructura.db import BaseDatos
from comun.infraestructura.reloj import Reloj
from comun.observabilidad import Logger, metricas
from contratos.topologia import topologia_region
from ingesta.adaptadores.acceso import AdaptadorAcceso, AdaptadorAerolinea, AdaptadorCorreo, AdaptadorHotel
from ingesta.avisos.receptor import Receptor, firma_aviso  # noqa: F401 - firma_aviso se usa en pruebas y demo
from ingesta.coordinacion.coordinador import Coordinador
from ingesta.mensajeria.publicador import crear_publicador
from ingesta.persistencia.registro import Registro
from ingesta.planificacion.planificador import Planificador
from ingesta.procesamiento.tuberia import Tuberia
from ingesta.vinculaciones.gestor import GestorVinculaciones
from simuladores.proveedores import ApiAerolineaSimulada, ApiHotelSimulada, BuzonSimulado


class Ingesta:
    def __init__(self, region: str, base: BaseDatos, broker: Broker, adaptadores: dict[str, AdaptadorAcceso],
                 reloj: Reloj | None = None, logger: Logger | None = None):
        self.region = region
        self.reloj = reloj or Reloj()
        self.logger = logger or Logger("ingesta", region)
        self.broker = broker
        self.registro = Registro(base)
        self.vinculaciones = GestorVinculaciones(base)
        self.adaptadores = adaptadores
        self.planificador = Planificador(self.registro, self.vinculaciones, self.reloj)
        self.tuberia = Tuberia(self.reloj)
        self.coordinador = Coordinador(self)
        self.publicador = crear_publicador(base, broker, self.reloj, self.logger)
        self.receptor = Receptor(self.registro, self.vinculaciones, self.planificador, self.reloj)

        async def estado(request):
            return JSONResponse(metricas.resumen())

        self.app = Starlette(routes=[Route("/avisos/{providerId}", self.receptor.recibir, methods=["POST"]),
                                     Route("/metrics", estado, methods=["GET"])])
        self._activo = False

    def agendar(self, connection_id: str, tipo: str) -> str:
        return self.planificador.agendar(connection_id, tipo)

    def ciclo(self) -> dict:
        """Un ciclo completo: planificar, ejecutar trabajo pendiente y publicar la outbox."""
        return {"agendadas": self.planificador.planificar(), "vinculaciones": self.coordinador.ejecutar_pendientes(),
                "publicados": self.publicador.publicar_pendientes()}

    def iniciar_trabajadores(self, intervalo: float = 0.5):
        self._activo = True

        def trabajar():
            while self._activo:
                try:
                    if not any(self.ciclo().values()):
                        time.sleep(intervalo)
                except Exception as error:
                    self.logger.error("ciclo_ingesta_fallo", error=str(error))
                    time.sleep(1)

        threading.Thread(target=trabajar, daemon=True, name="ingesta").start()


def proveedores_simulados() -> tuple[dict[str, AdaptadorAcceso], dict]:
    buzon, hotel, aerolinea = BuzonSimulado(), ApiHotelSimulada(), ApiAerolineaSimulada()
    adaptadores = {"correo-demo": AdaptadorCorreo(buzon), "hotel-sol": AdaptadorHotel(hotel),
                   "aerolinea-sur": AdaptadorAerolinea(aerolinea)}
    return adaptadores, {"buzon": buzon, "hotel": hotel, "aerolinea": aerolinea}


def desde_entorno() -> Ingesta:  # pragma: no cover - docker compose
    region = os.environ["REGION"]
    adaptadores, fuentes = proveedores_simulados()
    broker = broker_mod.abrir(os.environ.get("BROKER", "memoria"))
    broker.declarar(topologia_region())
    ingesta = Ingesta(region, db_mod.abrir(os.environ["BASE_INGESTA"], f"{region}-ingesta"), broker, adaptadores)
    ingesta.fuentes = fuentes
    if os.environ.get("CLAVE_ADMIN"):
        from simuladores.admin import rutas_ingesta

        ingesta.app.router.routes.extend(rutas_ingesta(ingesta, fuentes, os.environ["CLAVE_ADMIN"]))
    ingesta.iniciar_trabajadores()
    return ingesta
