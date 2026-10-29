"""Composición del núcleo de una región: base particionada, registro de auditoría, broker, API y trabajadores.

El núcleo es un monolito modular sin estado (ADR-0001): varias instancias pueden correr detrás de la puerta de
entrada. Los trabajadores son el publicador de la outbox, el consumidor de novedades (8 shards) y la tarea diaria.
"""
from __future__ import annotations

import os
import threading
import time

from comun.infraestructura import broker as broker_mod
from comun.infraestructura import db as db_mod
from comun.infraestructura.broker import Broker
from comun.infraestructura.db import BaseDatos
from comun.infraestructura.outbox import PublicadorOutbox
from comun.infraestructura.reloj import Reloj
from comun.observabilidad import Logger
from contratos.topologia import topologia_region
from nucleo.api.rutas import crear_app
from nucleo.auditoria.registro import RegistroAuditoria
from nucleo.comparticion.correo import CorreoSimulado
from nucleo.comparticion.servicio import Comparticion
from nucleo.datos.esquema import DDL_AUDITORIA, DDL_NODO
from nucleo.datos.ruteo import RuteoParticiones
from nucleo.esquemas.registro import ESQUEMAS_POR_DEFECTO, RegistroEsquemas
from nucleo.mensajeria.consumidor_novedades import ConsumidorNovedades
from nucleo.viajes import ciclo_vida


class Nucleo:
    def __init__(self, region: str, nodos: list[BaseDatos], base_auditoria: BaseDatos, broker: Broker,
                 clave_puerta: str, clave_email: bytes, reloj: Reloj | None = None, correo=None,
                 esquemas=ESQUEMAS_POR_DEFECTO, logger: Logger | None = None):
        self.region = region
        self.reloj = reloj or Reloj()
        self.logger = logger or Logger("nucleo", region)
        self.broker = broker
        self.clave_puerta = clave_puerta
        for nodo in nodos:
            nodo.crear_esquema(DDL_NODO)
        base_auditoria.crear_esquema(DDL_AUDITORIA)
        self.ruteo = RuteoParticiones(region, nodos)
        self.auditoria = RegistroAuditoria(base_auditoria, region, self.reloj, self.logger)
        self.esquemas = RegistroEsquemas(esquemas)
        self.correo = correo or CorreoSimulado()
        self.comparticion = Comparticion(region, self.ruteo, self.auditoria, self.reloj, clave_email, self.correo)
        self.publicador = PublicadorOutbox(nodos, broker, self.reloj, self.logger)
        self.consumidor = ConsumidorNovedades(self)
        self.app = crear_app(self)
        self._activo = False

    def preparar_mensajeria(self):
        self.broker.declarar(topologia_region())
        self.consumidor.suscribir(self.broker)

    def registrar_vinculacion(self, connection_id: str, user_id: str, provider_id: str, estado: str = "activa"):
        """El núcleo es la autoridad de las vinculaciones (iteración 2). RF-02 no está en el alcance del prototipo,
        así que las vinculaciones de prueba se cargan con esta función."""
        with self.ruteo.nodo(user_id).transaccion() as tx:
            tx.ejecutar("INSERT INTO vinculaciones (connection_id, user_id, home_region, provider_id, estado, revision) "
                        "VALUES (?, ?, ?, ?, ?, 1) ON CONFLICT (connection_id) DO UPDATE SET estado = excluded.estado",
                        (connection_id, user_id, self.region, provider_id, estado))

    def tarea_diaria(self) -> dict:
        return ciclo_vida.tarea_diaria(self.ruteo, self.reloj, self.region, self.logger)

    def iniciar_trabajadores(self, intervalo_outbox: float = 0.2, hora_tarea_diaria: int = 4):
        """Modo servicio: publicador de outbox en un hilo, consumo del broker y tarea diaria a la hora configurada."""
        self._activo = True
        self.broker.iniciar()

        def publicar():
            while self._activo:
                try:
                    if self.publicador.publicar_pendientes() == 0:
                        time.sleep(intervalo_outbox)
                except Exception as e:  # el publicador nunca debe morir; reintenta en el próximo ciclo
                    self.logger.error("publicador_outbox_fallo", error=str(e))
                    time.sleep(1)

        def diaria():
            ultimo = None
            while self._activo:
                ahora = self.reloj.ahora()
                if ahora.hour == hora_tarea_diaria and ultimo != ahora.date():
                    self.tarea_diaria()
                    ultimo = ahora.date()
                time.sleep(60)

        threading.Thread(target=publicar, daemon=True, name="publicador-outbox").start()
        threading.Thread(target=diaria, daemon=True, name="tarea-diaria").start()

    def detener(self):
        self._activo = False
        self.broker.detener()


def desde_entorno() -> Nucleo:  # pragma: no cover - docker compose
    """Configuración por variables de entorno (docker compose o ejecución local)."""
    region = os.environ["REGION"]
    nodos = [db_mod.abrir(url, f"{region}-nodo{i}") for i, url in enumerate(os.environ["NODOS"].split(","))]
    nucleo = Nucleo(
        region=region, nodos=nodos, base_auditoria=db_mod.abrir(os.environ["BASE_AUDITORIA"], f"{region}-auditoria"),
        broker=broker_mod.abrir(os.environ.get("BROKER", "memoria")), clave_puerta=os.environ["CLAVE_PUERTA"],
        clave_email=os.environ["CLAVE_EMAIL_HMAC"].encode(),
        correo=CorreoSimulado(os.environ.get("BUZON_SIMULADO")),
    )
    nucleo.preparar_mensajeria()
    if os.environ.get("CLAVE_ADMIN"):
        from simuladores.admin import rutas_nucleo

        nucleo.app.router.routes.extend(rutas_nucleo(nucleo, os.environ["CLAVE_ADMIN"]))
    nucleo.iniciar_trabajadores()
    return nucleo
