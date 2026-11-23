"""Ranking en dos etapas (ADR-0083): filtro por límites explícitos y orden por probabilidad de aceptación.

Puntaje: σ(w_región · x + u_viajero · x). Se muestran 3; con probabilidad 0,1 una de las tres sale de fuera de las
tres mejores (exploración epsilon-greedy), para no aprender solo de lo que ya se mostraba.
"""
from __future__ import annotations

import math
import random

MOSTRAR = 3        # suposición
EXPLORACION = 0.1  # suposición


def puntaje(x: list[float], pesos: list[float], ajuste: list[float] | None = None) -> float:
    z = sum(xi * wi for xi, wi in zip(x, pesos))
    if ajuste:
        z += sum(xi * ui for xi, ui in zip(x, ajuste))
    return 1 / (1 + math.exp(-max(min(z, 30), -30)))


def ordenar(candidatas: list[tuple[dict, list[float]]], pesos, ajuste=None) -> list[tuple[dict, list[float], float]]:
    """Devuelve (oferta, x, puntaje) de mayor a menor puntaje; empata por precio y por identificador."""
    puntuadas = [(oferta, x, puntaje(x, pesos, ajuste)) for oferta, x in candidatas]
    return sorted(puntuadas, key=lambda t: (-t[2], t[0]["price"]["amount"], t[0]["offerId"]))


def elegir(ordenadas: list, azar: random.Random, mostrar: int = MOSTRAR,
           exploracion: float = EXPLORACION) -> list[tuple[int, bool]]:
    """Índices de `ordenadas` a mostrar, en orden, y si cada uno es de exploración."""
    elegidos = [(i, False) for i in range(min(mostrar, len(ordenadas)))]
    if len(ordenadas) > mostrar and azar.random() < exploracion:
        elegidos[-1] = (azar.randrange(mostrar, len(ordenadas)), True)
    return elegidos
