"""Búsqueda de alternativas con caché corta, búsquedas agrupadas y límite por proveedor (ADR-0082).

* Caché por clave de búsqueda durante 5 minutos (o hasta el vencimiento más cercano de las ofertas).
* Las búsquedas pendientes con la misma clave se resuelven con una sola consulta (`Sugerencias.procesar_pendientes`
  agrupa por clave y llama a `buscar` una vez por clave).
* Cubeta de fichas por proveedor y región: capacidad de la mitad del límite por minuto publicado por el proveedor y
  recarga de la otra mitad por minuto, así ninguna ventana de un minuto supera el límite (capacidad + recarga de un
  minuto = límite). Sin fichas no se consulta.
* Circuit breaker: tras 3 fallas temporales seguidas, el proveedor no se consulta durante 1 minuto.
* Si un proveedor falla y otro responde, el resultado es parcial; si ninguno responde, la búsqueda queda pendiente.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from comun.infraestructura.reloj import Reloj, parsear
from comun.observabilidad import Logger, metricas
from recomendacion.busqueda.adaptadores import Consulta, PuertoBusqueda
from simuladores.proveedores import ErrorAutorizacion, ErrorCuota, ErrorTemporal

VIGENCIA_CACHE = timedelta(minutes=5)   # suposición (QA-12)
FALLAS_PARA_CORTE = 3                   # suposición
DURACION_CORTE = timedelta(minutes=1)   # suposición


@dataclass
class Resultado:
    ofertas: list[dict]
    parcial: bool = False
    pendiente: bool = False
    reintentar_en: timedelta | None = None
    desde_cache: bool = False


@dataclass
class _Cubeta:
    capacidad: float
    por_segundo: float
    fichas: float
    ultimo: datetime | None = None

    def tomar(self, ahora: datetime) -> bool:
        if self.ultimo is not None:
            self.fichas = min(self.capacidad, self.fichas + (ahora - self.ultimo).total_seconds() * self.por_segundo)
        self.ultimo = ahora
        if self.fichas < 1:
            return False
        self.fichas -= 1
        return True


@dataclass
class _Corte:
    fallas: int = 0
    hasta: datetime | None = None


@dataclass
class Buscador:
    adaptadores: list[PuertoBusqueda]
    reloj: Reloj
    logger: Logger
    _cache: dict = field(default_factory=dict)
    _cubetas: dict = field(default_factory=dict)
    _cortes: dict = field(default_factory=dict)
    consultas: dict = field(default_factory=dict)

    def _cubeta(self, adaptador: PuertoBusqueda) -> _Cubeta:
        if adaptador.proveedor not in self._cubetas:
            mitad = float(adaptador.limite_por_minuto) / 2
            self._cubetas[adaptador.proveedor] = _Cubeta(mitad, mitad / 60, mitad)
        return self._cubetas[adaptador.proveedor]

    def buscar(self, consulta: Consulta) -> Resultado:
        ahora = self.reloj.ahora()
        en_cache = self._cache.get(consulta.clave)
        if en_cache and en_cache[0] > ahora:
            metricas.incrementar("busqueda_cache_acierto")
            return Resultado([dict(o) for o in en_cache[1]], parcial=en_cache[2], desde_cache=True)
        ofertas, fallas_reintentables, respondieron, espera = [], 0, 0, None
        for adaptador in (a for a in self.adaptadores if consulta.type in a.tipos):
            corte = self._cortes.setdefault(adaptador.proveedor, _Corte())
            if corte.hasta and corte.hasta > ahora:
                fallas_reintentables += 1
                continue
            if not self._cubeta(adaptador).tomar(ahora):
                metricas.incrementar("busqueda_sin_fichas")
                fallas_reintentables += 1
                espera = min(espera or timedelta(seconds=10), timedelta(seconds=10))
                continue
            self.consultas[adaptador.proveedor] = self.consultas.get(adaptador.proveedor, 0) + 1
            try:
                ofertas.extend(adaptador.buscar(consulta))
                respondieron += 1
                corte.fallas, corte.hasta = 0, None
            except ErrorCuota as error:
                fallas_reintentables += 1
                espera = timedelta(seconds=error.reintentar_en)
            except ErrorTemporal:
                fallas_reintentables += 1
                corte.fallas += 1
                if corte.fallas >= FALLAS_PARA_CORTE:
                    corte.hasta = ahora + DURACION_CORTE
                    self.logger.alerta("proveedor_busqueda_cortado", proveedor=adaptador.proveedor)
            except ErrorAutorizacion:
                self.logger.alerta("proveedor_busqueda_sin_autorizacion", proveedor=adaptador.proveedor)
        if respondieron == 0 and fallas_reintentables:
            return Resultado([], pendiente=True, reintentar_en=espera)
        parcial = fallas_reintentables > 0
        vence = ahora + VIGENCIA_CACHE
        vencimientos = [parsear(o["expiresAt"]) for o in ofertas if o.get("expiresAt")]
        if vencimientos:
            vence = min(vence, min(vencimientos))
        self._cache[consulta.clave] = (vence, [dict(o) for o in ofertas], parcial)
        return Resultado(ofertas, parcial=parcial)
