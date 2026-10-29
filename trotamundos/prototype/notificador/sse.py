"""Módulo `conexiones-sse` del notificador (ADR-0046): conexiones abiertas de los usuarios en esta instancia y
flujo de eventos `ready` y `panel-changed`."""
from __future__ import annotations

import asyncio
import json
import threading

LATIDO_S = 15


class ConexionesSSE:
    """Registro de conexiones abiertas en esta instancia: usuario → colas de eventos."""

    def __init__(self):
        self._lock = threading.Lock()
        self._conexiones: dict[str, set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = {}

    def abrir(self, usuario: str) -> tuple[asyncio.AbstractEventLoop, asyncio.Queue]:
        entrada = (asyncio.get_running_loop(), asyncio.Queue())
        with self._lock:
            self._conexiones.setdefault(usuario, set()).add(entrada)
        return entrada

    def cerrar(self, usuario: str, entrada):
        with self._lock:
            self._conexiones.get(usuario, set()).discard(entrada)

    def conectados(self, usuario: str) -> int:
        with self._lock:
            return len(self._conexiones.get(usuario, ()))

    def avisar(self, usuario: str, evento: dict) -> int:
        with self._lock:
            destinos = list(self._conexiones.get(usuario, ()))
        for bucle, cola in destinos:
            bucle.call_soon_threadsafe(cola.put_nowait, evento)
        return len(destinos)


async def flujo_eventos(conexiones: ConexionesSSE, usuario: str):
    """Envía `ready` al conectarse (recién entonces el cliente revalida con GET /panel) y luego cada aviso."""
    entrada = conexiones.abrir(usuario)
    _, cola = entrada
    try:
        yield b"event: ready\ndata: {}\n\n"
        while True:
            try:
                evento = await asyncio.wait_for(cola.get(), timeout=LATIDO_S)
            except asyncio.TimeoutError:
                yield b": latido\n\n"
                continue
            yield f"event: panel-changed\ndata: {json.dumps(evento)}\n\n".encode()
    finally:
        conexiones.cerrar(usuario, entrada)
