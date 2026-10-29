"""Ensamble local del prototipo: dos regiones completas en un solo proceso, sin Docker.

Cada región tiene su base particionada (dos nodos SQLite), registro de auditoría, broker (en memoria), núcleo,
notificador, ingesta con proveedores simulados, proveedor de identidad y puerta de entrada. Las regiones se
comunican solo por el canal entre puertas. La entrada global elige la región. Lo usan las pruebas, la demo y
`python -m sistema` (que sirve la entrada global en http://localhost:8080).

Con docker compose, los mismos procesos corren por separado con PostgreSQL y RabbitMQ (ver README).
"""
from __future__ import annotations

import os
import secrets
import sys
import threading
import time
from dataclasses import dataclass, field

from comun.infraestructura.broker import BrokerEnMemoria
from comun.infraestructura.db import SQLite
from comun.infraestructura.http import DestinoASGI
from comun.infraestructura.reloj import Reloj
from comun.observabilidad import Logger
from entrada.app import EntradaGlobal
from identidad.app import ProveedorIdentidad
from ingesta.app import Ingesta, proveedores_simulados
from notificador.app import Notificador
from nucleo.app import Nucleo
from puerta.app import Puerta
from puerta.autenticacion import Emisores

REGIONES = ("sa-east", "eu-west")


@dataclass
class Region:
    nombre: str
    broker: BrokerEnMemoria
    nucleo: Nucleo
    notificador: Notificador
    ingesta: Ingesta
    identidad: ProveedorIdentidad
    fuentes: dict
    puerta: Puerta | None = None
    destinos: dict = field(default_factory=dict)


class Sistema:
    def __init__(self, directorio: str, reloj: Reloj | None = None, regiones=REGIONES, salida_logs=sys.stdout):
        os.makedirs(directorio, exist_ok=True)
        self.reloj = reloj or Reloj()
        self.claves = {"email": secrets.token_bytes(32), "canal": secrets.token_hex(16),
                       "directorio": secrets.token_bytes(32), "interna": secrets.token_hex(16)}
        self.entrada_base = SQLite(os.path.join(directorio, "directorio.db"))
        self.regiones: dict[str, Region] = {}
        self.emisores = Emisores()
        destinos_puertas: dict[str, DestinoASGI] = {}
        for nombre in regiones:
            ruta = lambda archivo, n=nombre: os.path.join(directorio, f"{n}-{archivo}.db")  # noqa: E731
            logger = lambda proceso, n=nombre: Logger(proceso, n, salida=salida_logs)  # noqa: E731
            broker = BrokerEnMemoria()
            clave_puerta = secrets.token_hex(16)
            auditoria = SQLite(ruta("auditoria"))
            nucleo = Nucleo(nombre, [SQLite(ruta("nodo0")), SQLite(ruta("nodo1"))], auditoria, broker, clave_puerta,
                            self.claves["email"], reloj=self.reloj, logger=logger("nucleo"))
            nucleo.preparar_mensajeria()
            notificador = Notificador(nombre, broker, SQLite(ruta("push")), clave_puerta, reloj=self.reloj,
                                      logger=logger("notificador"))
            notificador.preparar_mensajeria()
            adaptadores, fuentes = proveedores_simulados()
            ingesta = Ingesta(nombre, SQLite(ruta("ingesta")), broker, adaptadores, reloj=self.reloj,
                              logger=logger("ingesta"))
            identidad = ProveedorIdentidad(nombre, SQLite(ruta("identidad")), self.claves["email"],
                                           registrar_en_directorio=self._registrar_en_directorio, reloj=self.reloj,
                                           logger=logger("identidad"))
            self.emisores.registrar(identidad.emisor, nombre, identidad.jwks())
            region = Region(nombre, broker, nucleo, notificador, ingesta, identidad, fuentes)
            region.destinos = {"nucleo": DestinoASGI(nucleo.app, f"nucleo-{nombre}"),
                               "notificador": DestinoASGI(notificador.app, f"notificador-{nombre}"),
                               "ingesta": DestinoASGI(ingesta.app, f"ingesta-{nombre}")}
            region.clave_puerta = clave_puerta
            region.auditoria = auditoria
            self.regiones[nombre] = region
        for nombre, region in self.regiones.items():
            region.puerta = Puerta(nombre, region.destinos["nucleo"], region.destinos["notificador"],
                                   region.destinos["ingesta"], {}, self.emisores, region.auditoria,
                                   region.clave_puerta, self.claves["canal"], secrets.token_hex(16), reloj=self.reloj,
                                   logger=Logger("puerta", nombre, salida=salida_logs))
            destinos_puertas[nombre] = DestinoASGI(region.puerta.app, f"puerta-{nombre}")
            region.destinos["puerta"] = destinos_puertas[nombre]
        for nombre, region in self.regiones.items():
            region.puerta.otras_regiones.update({n: d for n, d in destinos_puertas.items() if n != nombre})
        self.entrada = EntradaGlobal(self.entrada_base, self.claves["directorio"], self.claves["interna"],
                                     destinos_puertas, {n: f"/id/{n}" for n in regiones},
                                     {n: DestinoASGI(r.identidad.app, f"identidad-{n}") for n, r in self.regiones.items()})
        self._activo = False

    def _registrar_en_directorio(self, email: str, region: str):
        self.entrada.registrar_email(email, region)

    def procesar(self, rondas: int = 20) -> int:
        """Ejecuta trabajadores de forma sincrónica hasta que no queda nada pendiente (pruebas y demo)."""
        total = 0
        for _ in range(rondas):
            hecho = 0
            for region in self.regiones.values():
                resumen = region.ingesta.ciclo()
                hecho += resumen["vinculaciones"] + resumen["publicados"]
                hecho += region.nucleo.publicador.publicar_pendientes()
                hecho += region.broker.bombear()
            total += hecho
            reentregas = sum(r.broker.pendientes_con_consumidor() for r in self.regiones.values())
            if hecho == 0 and reentregas == 0:
                break
        return total

    def iniciar(self, intervalo: float = 0.1):
        """Trabajadores en segundo plano (modo servidor local)."""
        self._activo = True

        def ciclo():
            while self._activo:
                try:
                    if self.procesar(rondas=1) == 0:
                        time.sleep(intervalo)
                except Exception as error:  # el ciclo no debe morir
                    print("error en el ciclo de trabajadores:", error)
                    time.sleep(1)

        threading.Thread(target=ciclo, daemon=True, name="trabajadores").start()

    def detener(self):
        self._activo = False


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    puerto = int(os.environ.get("PUERTO", "8080"))
    sistema = Sistema(os.environ.get("DATOS", "datos-locales"))
    sistema.iniciar()
    print(f"Entrada global en http://localhost:{puerto} (regiones: {', '.join(sistema.regiones)})")
    uvicorn.run(sistema.entrada.app, host="127.0.0.1", port=puerto, log_level="warning")
