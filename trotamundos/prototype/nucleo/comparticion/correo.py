"""Puerto de envío de correo para las invitaciones. En el prototipo es un buzón simulado: guarda los correos en
memoria y, si se configura, en un archivo JSON Lines que representa la casilla del destinatario (no es un log)."""
from __future__ import annotations

import json
import threading


class CorreoSimulado:
    def __init__(self, archivo: str | None = None):
        self.archivo = archivo
        self.enviados: list[dict] = []
        self._lock = threading.Lock()

    def enviar(self, destinatario: str, plantilla: str, datos: dict):
        correo = {"to": destinatario, "template": plantilla, **datos}
        with self._lock:
            self.enviados.append(correo)
            if self.archivo:
                with open(self.archivo, "a", encoding="utf-8") as salida:
                    salida.write(json.dumps(correo) + "\n")

    def ultimo_para(self, destinatario: str) -> dict:
        return next(c for c in reversed(self.enviados) if c["to"] == destinatario)
