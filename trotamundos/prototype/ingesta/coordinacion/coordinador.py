"""Coordinador de la ingesta (ADR-0020, ADR-0024): ejecuta el trabajo pendiente con exclusión por vinculación.

Agrupa los trabajos (avisos y reconciliaciones) de una misma vinculación, comprueba la vigencia antes de consultar,
consulta desde el cursor confirmado, procesa cada elemento y confirma resultados, outbox y avance juntos. Los
errores se clasifican: temporal (reintento con espera creciente), cuota (respeta Retry-After) y autorización
(se detiene y pide revinculación).
"""
from __future__ import annotations

import random
from datetime import timedelta

from comun.infraestructura.reloj import iso, parsear
from comun.observabilidad import contexto_correlacion, contexto_traza, continuar_traza, metricas, nuevo_correlation_id
from ingesta.persistencia.registro import LeasePerdido
from simuladores.proveedores import ErrorAutorizacion, ErrorCuota, ErrorTemporal


class Coordinador:
    def __init__(self, ingesta):
        self.ingesta = ingesta
        self.fallar_antes_de_confirmar = None  # punto de inyección de fallas para las pruebas (V05)

    def ejecutar_pendientes(self) -> int:
        ingesta = self.ingesta
        ahora = iso(ingesta.reloj.ahora())
        with ingesta.registro.base.transaccion() as tx:
            trabajos = tx.todos("SELECT * FROM trabajos WHERE estado = 'pendiente' AND "
                                "(reintentar_desde IS NULL OR reintentar_desde <= ?) ORDER BY creado", (ahora,))
        por_vinculacion: dict[str, list[dict]] = {}
        for trabajo in trabajos:
            por_vinculacion.setdefault(trabajo["connection_id"], []).append(trabajo)
        procesadas = 0
        for connection_id, grupo in por_vinculacion.items():
            if self._ejecutar(connection_id, grupo):
                procesadas += 1
        return procesadas

    def _ejecutar(self, connection_id: str, trabajos: list[dict]) -> bool:
        ingesta = self.ingesta
        contexto_traza.set(continuar_traza(trabajos[0]["traceparent"]))
        vinculacion = ingesta.vinculaciones.vigente(connection_id)
        if vinculacion is None:  # revocada o inexistente: no se inician consultas nuevas
            self._marcar(trabajos, "cancelado")
            return False
        adaptador = ingesta.adaptadores[vinculacion["provider_id"]]
        cursor, version = ingesta.registro.leer_cursor(connection_id)
        try:
            pagina = adaptador.consultar(vinculacion, cursor)
        except ErrorTemporal:
            self._reintentar(trabajos, segundos=None)
            return False
        except ErrorCuota as error:
            self._reintentar(trabajos, segundos=error.reintentar_en)
            return False
        except ErrorAutorizacion:
            ingesta.vinculaciones.marcar(connection_id, "requiere_revinculacion")
            self._marcar(trabajos, "cancelado")
            ingesta.logger.alerta("autorizacion_invalida", connectionId=connection_id)
            return False
        resultados = []
        for elemento in pagina.elementos:
            correlation_id = nuevo_correlation_id()  # se genera cuando la ingesta detecta el cambio (ADR-0067)
            contexto_correlacion.set(correlation_id)
            resultados.append((elemento.item_id, ingesta.tuberia.procesar(vinculacion, adaptador.fuente, elemento,
                                                                         correlation_id)))
        if self.fallar_antes_de_confirmar:
            self.fallar_antes_de_confirmar(connection_id)  # caída antes de guardar cursor y outbox
        # Revocación coordinada: se vuelve a comprobar la vigencia antes de dejar trabajo publicable.
        if ingesta.vinculaciones.vigente(connection_id) is None:
            self._marcar(trabajos, "cancelado")
            return False
        try:
            resumen = ingesta.registro.confirmar_pagina(connection_id, version, pagina.cursor, resultados,
                                                       [t["trabajo_id"] for t in trabajos],
                                                       iso(ingesta.reloj.ahora()), contexto_traza.get())
        except LeasePerdido:
            metricas.incrementar("ingesta_lease_perdido")
            return False
        if len(pagina.elementos) == 10:  # página completa: puede haber más; se agenda otra consulta
            ingesta.agendar(connection_id, "continuacion")
        for clave, valor in resumen.items():
            metricas.incrementar(f"ingesta_{clave}", valor)
        ingesta.logger.info("pagina_confirmada", connectionId=connection_id, cursor=pagina.cursor, **resumen)
        return True

    def _marcar(self, trabajos, estado):
        with self.ingesta.registro.base.transaccion() as tx:
            for trabajo in trabajos:
                tx.ejecutar("UPDATE trabajos SET estado = ? WHERE trabajo_id = ?", (estado, trabajo["trabajo_id"]))

    def _reintentar(self, trabajos, segundos):
        ahora = self.ingesta.reloj.ahora()
        with self.ingesta.registro.base.transaccion() as tx:
            for trabajo in trabajos:
                espera = segundos if segundos is not None else min(300, 2 ** trabajo["intentos"]) * random.uniform(0.8, 1.2)
                tx.ejecutar("UPDATE trabajos SET intentos = intentos + 1, reintentar_desde = ? WHERE trabajo_id = ?",
                            (iso(ahora + timedelta(seconds=espera)), trabajo["trabajo_id"]))
        metricas.incrementar("ingesta_reintentos")

    @staticmethod
    def vencido(texto: str | None, ahora) -> bool:
        return texto is None or parsear(texto) <= ahora
