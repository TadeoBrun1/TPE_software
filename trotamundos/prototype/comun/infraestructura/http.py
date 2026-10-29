"""Puerto para reenviar solicitudes HTTP entre procesos (puerta de entrada → núcleo, notificador u otra región).

Dos adaptadores: `DestinoASGI` llama a la aplicación en el mismo proceso (pruebas y modo local) y `DestinoHTTP`
abre una conexión HTTP/1.1 real con la biblioteca estándar (docker compose). Ambos soportan respuestas en flujo
(SSE). Biblioteca técnica sin dominio.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator
from urllib.parse import urlsplit


@dataclass
class Respuesta:
    estado: int
    encabezados: list[tuple[str, str]]
    cuerpo: bytes

    def encabezado(self, nombre: str) -> str | None:
        for clave, valor in self.encabezados:
            if clave.lower() == nombre.lower():
                return valor
        return None


@dataclass
class Flujo:
    estado: int
    encabezados: list[tuple[str, str]]
    partes: AsyncIterator[bytes]
    cerrar: object  # callable async


class DestinoNoDisponible(ConnectionError):
    pass


class Destino:
    async def enviar(self, metodo: str, ruta: str, encabezados: dict[str, str], cuerpo: bytes = b"") -> Respuesta:
        raise NotImplementedError

    async def abrir_flujo(self, metodo: str, ruta: str, encabezados: dict[str, str]) -> Flujo:
        raise NotImplementedError


class DestinoASGI(Destino):
    def __init__(self, app, nombre: str = ""):
        self.app = app
        self.nombre = nombre
        self.disponible = True  # permite simular la caída de una región o de un proceso

    def _alcance(self, metodo: str, ruta: str, encabezados: dict[str, str]) -> dict:
        camino, _, consulta = ruta.partition("?")
        return {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": metodo.upper(),
            "scheme": "http", "path": camino, "raw_path": camino.encode(), "query_string": consulta.encode(),
            "root_path": "", "headers": [(k.lower().encode(), v.encode()) for k, v in encabezados.items()],
            "client": ("127.0.0.1", 0), "server": (self.nombre or "interno", 80),
        }

    async def enviar(self, metodo, ruta, encabezados, cuerpo=b""):
        flujo = await self.abrir_flujo(metodo, ruta, encabezados, cuerpo)
        partes = [p async for p in flujo.partes]
        return Respuesta(flujo.estado, flujo.encabezados, b"".join(partes))

    async def abrir_flujo(self, metodo, ruta, encabezados, cuerpo: bytes = b""):
        if not self.disponible:
            raise DestinoNoDisponible(self.nombre)
        desconectado = asyncio.Event()
        enviado_cuerpo = False
        cola: asyncio.Queue = asyncio.Queue()

        async def recibir():
            nonlocal enviado_cuerpo
            if not enviado_cuerpo:
                enviado_cuerpo = True
                return {"type": "http.request", "body": cuerpo, "more_body": False}
            await desconectado.wait()
            return {"type": "http.disconnect"}

        async def enviar(mensaje):
            await cola.put(mensaje)

        async def ejecutar():
            try:
                await self.app(self._alcance(metodo, ruta, encabezados), recibir, enviar)
            finally:
                await cola.put({"type": "fin"})

        tarea = asyncio.create_task(ejecutar())
        inicio = await cola.get()
        if inicio["type"] == "fin":
            raise RuntimeError("la aplicación no respondió")
        estado = inicio["status"]
        cabeceras = [(k.decode(), v.decode()) for k, v in inicio.get("headers", [])]

        async def partes():
            while True:
                mensaje = await cola.get()
                if mensaje["type"] == "fin":
                    return
                if mensaje.get("body"):
                    yield mensaje["body"]
                if not mensaje.get("more_body", False):
                    return

        async def cerrar():
            desconectado.set()
            try:
                await asyncio.wait_for(tarea, timeout=1)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                tarea.cancel()

        return Flujo(estado, cabeceras, partes(), cerrar)


class DestinoHTTP(Destino):  # pragma: no cover - se usa con docker compose
    def __init__(self, url_base: str, tiempo_maximo: float = 10.0):
        partes = urlsplit(url_base)
        self.host = partes.hostname
        self.puerto = partes.port or 80
        self.tiempo_maximo = tiempo_maximo
        self.disponible = True

    async def _abrir(self, metodo, ruta, encabezados, cuerpo: bytes):
        try:
            lector, escritor = await asyncio.wait_for(asyncio.open_connection(self.host, self.puerto),
                                                      self.tiempo_maximo)
        except (OSError, asyncio.TimeoutError) as error:
            raise DestinoNoDisponible(f"{self.host}:{self.puerto}") from error
        lineas = [f"{metodo.upper()} {ruta} HTTP/1.1", f"Host: {self.host}", "Connection: close",
                  f"Content-Length: {len(cuerpo)}"]
        lineas += [f"{k}: {v}" for k, v in encabezados.items() if k.lower() not in ("host", "content-length")]
        escritor.write(("\r\n".join(lineas) + "\r\n\r\n").encode() + cuerpo)
        await escritor.drain()
        estado_linea = await lector.readline()
        estado = int(estado_linea.split()[1])
        cabeceras = []
        while True:
            linea = await lector.readline()
            if linea in (b"\r\n", b"\n", b""):
                break
            clave, _, valor = linea.decode().partition(":")
            cabeceras.append((clave.strip(), valor.strip()))
        return lector, escritor, estado, cabeceras

    @staticmethod
    async def _cuerpo(lector, cabeceras):
        chunked = any(k.lower() == "transfer-encoding" and "chunked" in v.lower() for k, v in cabeceras)
        if chunked:
            while True:
                tamano = int((await lector.readline()).split(b";")[0].strip() or b"0", 16)
                if tamano == 0:
                    return
                yield await lector.readexactly(tamano)
                await lector.readline()
        else:
            while True:
                parte = await lector.read(65536)
                if not parte:
                    return
                yield parte

    async def enviar(self, metodo, ruta, encabezados, cuerpo=b""):
        lector, escritor, estado, cabeceras = await self._abrir(metodo, ruta, encabezados, cuerpo)
        datos = b"".join([p async for p in self._cuerpo(lector, cabeceras)])
        escritor.close()
        return Respuesta(estado, cabeceras, datos)

    async def abrir_flujo(self, metodo, ruta, encabezados, cuerpo: bytes = b""):
        lector, escritor, estado, cabeceras = await self._abrir(metodo, ruta, encabezados, cuerpo)

        async def cerrar():
            escritor.close()

        return Flujo(estado, cabeceras, self._cuerpo(lector, cabeceras), cerrar)


def abrir(url: str) -> Destino:
    return DestinoHTTP(url)
