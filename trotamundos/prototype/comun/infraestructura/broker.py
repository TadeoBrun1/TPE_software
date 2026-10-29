"""Puerto de mensajería con dos adaptadores: broker en memoria (local y pruebas) y RabbitMQ (docker compose).

Biblioteca técnica sin lógica de dominio. Reproduce las reglas de ADR-0028 e `ingestion-operations.md`:
exchanges `topic` durables, publicación con `mandatory` (un mensaje sin ruta es un fallo, aunque el broker lo
confirme), confirmaciones de publicación, ACK manual después de procesar y reentrega si el consumidor falla.
"""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable


class MensajeNoEnrutado(Exception):
    """El broker devolvió el mensaje por falta de ruta (`mandatory`)."""


class PublicacionNoConfirmada(Exception):
    """El broker no confirmó la publicación."""


@dataclass
class Cola:
    nombre: str
    tipo: str = "quorum"  # quorum | classic
    durable: bool = True
    exclusiva: bool = False
    auto_borrar: bool = False
    argumentos: dict = field(default_factory=dict)
    enlaces: list[tuple[str, str]] = field(default_factory=list)  # (exchange, routing key o patrón)


@dataclass
class Topologia:
    exchanges: list[str]
    colas: list[Cola]


@dataclass
class Mensaje:
    exchange: str
    routing_key: str
    cuerpo: dict
    encabezados: dict
    reentregado: bool = False
    entregas: int = 0


Manejador = Callable[[Mensaje], None]


def coincide(patron: str, clave: str) -> bool:
    """Coincidencia de routing keys de un exchange topic (`*` = una palabra, `#` = cero o más)."""
    def emparejar(p: list[str], c: list[str]) -> bool:
        if not p:
            return not c
        if p[0] == "#":
            return any(emparejar(p[1:], c[i:]) for i in range(len(c) + 1))
        if not c:
            return False
        return (p[0] == "*" or p[0] == c[0]) and emparejar(p[1:], c[1:])

    return emparejar(patron.split("."), clave.split("."))


class Broker:
    def declarar(self, topologia: Topologia): ...
    def declarar_cola(self, cola: Cola): ...
    def borrar_enlace(self, cola: str, exchange: str, clave: str): ...
    def publicar(self, exchange: str, routing_key: str, cuerpo: dict, encabezados: dict | None = None): ...
    def consumir(self, cola: str, manejador: Manejador, prefetch: int = 20): ...
    def bombear(self, maximo: int = 10_000) -> int: return 0
    def iniciar(self): ...
    def detener(self): ...


class BrokerEnMemoria(Broker):
    """Broker en proceso con la misma semántica que se espera de RabbitMQ para el prototipo."""

    def __init__(self):
        self._lock = threading.RLock()
        self.exchanges: set[str] = set()
        self.colas: dict[str, Cola] = {}
        self.mensajes: dict[str, deque[Mensaje]] = {}
        self.manejadores: dict[str, Manejador] = {}
        self.publicados: list[Mensaje] = []
        self._hilo: threading.Thread | None = None
        self._activo = False
        self.disponible = True

    def declarar(self, topologia: Topologia):
        with self._lock:
            self.exchanges.update(topologia.exchanges)
            for cola in topologia.colas:
                self.declarar_cola(cola)

    def declarar_cola(self, cola: Cola):
        with self._lock:
            if cola.nombre in self.colas:
                existentes = set(self.colas[cola.nombre].enlaces)
                self.colas[cola.nombre].enlaces.extend(e for e in cola.enlaces if e not in existentes)
            else:
                self.colas[cola.nombre] = Cola(**{**cola.__dict__, "enlaces": list(cola.enlaces)})
                self.mensajes[cola.nombre] = deque()

    def borrar_enlace(self, cola: str, exchange: str, clave: str):
        with self._lock:
            self.colas[cola].enlaces = [e for e in self.colas[cola].enlaces if e != (exchange, clave)]

    def borrar_cola(self, nombre: str):
        with self._lock:
            self.colas.pop(nombre, None)
            self.mensajes.pop(nombre, None)
            self.manejadores.pop(nombre, None)

    def publicar(self, exchange: str, routing_key: str, cuerpo: dict, encabezados: dict | None = None):
        if not self.disponible:
            raise PublicacionNoConfirmada("broker no disponible")
        cuerpo = json.loads(json.dumps(cuerpo))  # copia, como si viajara por la red
        with self._lock:
            if exchange not in self.exchanges:
                raise PublicacionNoConfirmada(f"exchange inexistente: {exchange}")
            destinos = [c for c in self.colas.values()
                        if any(ex == exchange and coincide(patron, routing_key) for ex, patron in c.enlaces)]
            if not destinos:
                raise MensajeNoEnrutado(f"{exchange}/{routing_key}")
            mensaje = Mensaje(exchange, routing_key, cuerpo, dict(encabezados or {}))
            self.publicados.append(mensaje)
            for cola in destinos:
                self.mensajes[cola.nombre].append(Mensaje(exchange, routing_key, cuerpo, dict(encabezados or {})))

    def consumir(self, cola: str, manejador: Manejador, prefetch: int = 20):
        with self._lock:
            if cola not in self.colas:
                raise KeyError(f"cola inexistente: {cola}")
            self.manejadores[cola] = manejador  # un consumidor activo por cola (Single Active Consumer)

    def pendientes(self, cola: str) -> int:
        with self._lock:
            return len(self.mensajes.get(cola, ()))

    def pendientes_con_consumidor(self) -> int:
        """Mensajes esperando en colas con consumidor (por ejemplo, reentregas después de una falla)."""
        with self._lock:
            return sum(len(self.mensajes.get(cola, ())) for cola in self.manejadores)

    def bombear(self, maximo: int = 10_000) -> int:
        """Entrega los mensajes pendientes a sus consumidores. ACK al volver; si el manejador falla, reentrega."""
        procesados = 0
        progreso = True
        while progreso and procesados < maximo:
            progreso = False
            with self._lock:
                colas = [c for c in self.manejadores if self.mensajes.get(c)]
            for nombre in colas:
                with self._lock:
                    if not self.mensajes.get(nombre) or nombre not in self.manejadores:
                        continue
                    mensaje = self.mensajes[nombre].popleft()
                    manejador = self.manejadores[nombre]
                mensaje.entregas += 1
                try:
                    manejador(mensaje)
                except Exception:
                    mensaje.reentregado = True
                    with self._lock:
                        if nombre in self.mensajes:
                            self.mensajes[nombre].appendleft(mensaje)
                    continue
                procesados += 1
                progreso = True
        return procesados

    def iniciar(self, intervalo: float = 0.05):
        """Entrega en segundo plano (modo de ejecución local, fuera de las pruebas)."""
        if self._hilo:
            return
        self._activo = True

        def ciclo():
            while self._activo:
                if self.bombear() == 0:
                    time.sleep(intervalo)

        self._hilo = threading.Thread(target=ciclo, daemon=True, name="broker-memoria")
        self._hilo.start()

    def detener(self):
        self._activo = False


class BrokerRabbitMQ(Broker):  # pragma: no cover - se ejecuta con docker compose, no en las pruebas locales
    """Adaptador AMQP 0-9-1 con pika: publisher confirms, `mandatory`, colas quorum y ACK manual."""

    def __init__(self, url: str):
        import pika  # noqa: F401 - dependencia solo del despliegue con docker compose

        self.url = url
        self._local = threading.local()
        self._hilos: list[threading.Thread] = []
        self._consumidores: list[tuple[str, Manejador, int]] = []
        self._colas_declaradas: list[Cola] = []
        self._activo = False

    def _canal_publicacion(self):
        import pika

        canal = getattr(self._local, "canal", None)
        if canal is None or canal.is_closed:
            conexion = pika.BlockingConnection(pika.URLParameters(self.url))
            canal = conexion.channel()
            canal.confirm_delivery()
            self._local.canal = canal
        return canal

    def _declarar_en(self, canal, topologia: Topologia):
        for exchange in topologia.exchanges:
            canal.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
        for cola in topologia.colas:
            self._declarar_cola_en(canal, cola)

    @staticmethod
    def _declarar_cola_en(canal, cola: Cola):
        argumentos = dict(cola.argumentos)
        if cola.tipo == "quorum":
            argumentos["x-queue-type"] = "quorum"
        canal.queue_declare(queue=cola.nombre, durable=cola.durable, exclusive=cola.exclusiva,
                            auto_delete=cola.auto_borrar, arguments=argumentos)
        for exchange, clave in cola.enlaces:
            canal.queue_bind(queue=cola.nombre, exchange=exchange, routing_key=clave)

    def declarar(self, topologia: Topologia):
        self._declarar_en(self._canal_publicacion(), topologia)

    def declarar_cola(self, cola: Cola):
        if cola.exclusiva:  # una cola exclusiva pertenece a la conexión de su consumidor
            self._colas_declaradas.append(cola)
        else:
            self._declarar_cola_en(self._canal_publicacion(), cola)

    def borrar_enlace(self, cola: str, exchange: str, clave: str):
        self._canal_publicacion().queue_unbind(queue=cola, exchange=exchange, routing_key=clave)

    def publicar(self, exchange: str, routing_key: str, cuerpo: dict, encabezados: dict | None = None):
        import pika

        propiedades = pika.BasicProperties(content_type="application/json", delivery_mode=2,
                                           message_id=cuerpo.get("eventId"), headers=dict(encabezados or {}))
        try:
            self._canal_publicacion().basic_publish(exchange=exchange, routing_key=routing_key,
                                                    body=json.dumps(cuerpo).encode(), properties=propiedades,
                                                    mandatory=True)
        except pika.exceptions.UnroutableError as error:
            raise MensajeNoEnrutado(f"{exchange}/{routing_key}") from error
        except pika.exceptions.NackError as error:
            raise PublicacionNoConfirmada(str(error)) from error

    def consumir(self, cola: str, manejador: Manejador, prefetch: int = 20):
        self._consumidores.append((cola, manejador, prefetch))

    def iniciar(self):
        import pika

        self._activo = True
        for nombre, manejador, prefetch in self._consumidores:
            def ciclo(nombre=nombre, manejador=manejador, prefetch=prefetch):
                while self._activo:
                    try:
                        conexion = pika.BlockingConnection(pika.URLParameters(self.url))
                        canal = conexion.channel()
                        for cola in self._colas_declaradas:
                            if cola.nombre == nombre:
                                self._declarar_cola_en(canal, cola)
                        canal.basic_qos(prefetch_count=prefetch)

                        def al_recibir(ch, metodo, propiedades, cuerpo):
                            mensaje = Mensaje(metodo.exchange, metodo.routing_key, json.loads(cuerpo),
                                              dict(propiedades.headers or {}), reentregado=metodo.redelivered)
                            try:
                                manejador(mensaje)
                            except Exception:
                                ch.basic_nack(delivery_tag=metodo.delivery_tag, requeue=True)
                                time.sleep(1)
                            else:
                                ch.basic_ack(delivery_tag=metodo.delivery_tag)

                        canal.basic_consume(queue=nombre, on_message_callback=al_recibir, auto_ack=False)
                        canal.start_consuming()
                    except Exception:
                        time.sleep(2)  # reconexión con espera

            hilo = threading.Thread(target=ciclo, daemon=True, name=f"consumidor-{nombre}")
            hilo.start()
            self._hilos.append(hilo)

    def detener(self):
        self._activo = False


def abrir(url: str) -> Broker:
    if url == "memoria":
        return BrokerEnMemoria()
    if url.startswith("amqp://") or url.startswith("amqps://"):
        return BrokerRabbitMQ(url)
    raise ValueError(f"URL de broker no soportada: {url}")
