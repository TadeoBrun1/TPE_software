"""Entrenamiento del modelo (ADR-0083): regresión logística con numpy, por región y por lotes.

* `entrenar`: pesos regionales a partir de los ejemplos del feedback (aceptada = 1, rechazada = 0), ponderados por
  posición para corregir el sesgo de lo que se mostraba arriba, con regularización L2 hacia los pesos de partida.
* `paso_viajero`: ajuste inmediato por viajero con un paso de descenso por gradiente (human-in-the-loop, QA-13).
* `perdida`: pérdida logarítmica, para comparar versiones con el feedback reservado para prueba.
"""
from __future__ import annotations

import numpy as np

TASA_VIAJERO = 0.5   # suposición
L2_VIAJERO = 0.02    # suposición


def peso_por_posicion(posicion: int) -> float:
    """Una sugerencia mostrada más abajo se vio menos: su feedback vale un poco más (suposición)."""
    return 1.0 + 0.5 * posicion


def entrenar(ejemplos: list[tuple[list[float], int, float]], iniciales: list[float], epocas: int = 400,
             tasa: float = 0.3, l2: float = 0.01) -> list[float]:
    x = np.array([e[0] for e in ejemplos], dtype=float)
    y = np.array([e[1] for e in ejemplos], dtype=float)
    p = np.array([e[2] for e in ejemplos], dtype=float)
    w0 = np.array(iniciales, dtype=float)
    w = w0.copy()
    for _ in range(epocas):
        prob = 1 / (1 + np.exp(-np.clip(x @ w, -30, 30)))
        gradiente = x.T @ ((prob - y) * p) / p.sum() + l2 * (w - w0)
        w -= tasa * gradiente
    return [round(float(v), 6) for v in w]


def perdida(ejemplos: list[tuple[list[float], int, float]], pesos: list[float]) -> float:
    if not ejemplos:
        return float("inf")
    x = np.array([e[0] for e in ejemplos], dtype=float)
    y = np.array([e[1] for e in ejemplos], dtype=float)
    prob = np.clip(1 / (1 + np.exp(-np.clip(x @ np.array(pesos), -30, 30))), 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(prob) + (1 - y) * np.log(1 - prob)))


def paso_viajero(ajuste: list[float], x: list[float], etiqueta: int, pesos: list[float]) -> list[float]:
    u = np.array(ajuste or [0.0] * len(x), dtype=float)
    xv, w = np.array(x, dtype=float), np.array(pesos, dtype=float)
    prob = 1 / (1 + np.exp(-np.clip(xv @ (w + u), -30, 30)))
    u = u + TASA_VIAJERO * ((etiqueta - prob) * xv - L2_VIAJERO * u)
    return [round(float(v), 6) for v in u]
