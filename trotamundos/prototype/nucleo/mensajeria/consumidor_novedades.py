"""Suscriptor de novedades (`booking.change.detected.v1`): un consumidor activo por cada uno de los 8 shards.

El consumo no escala con las instancias del núcleo (ADR-0043): conserva el orden por usuario de la iteración 2.
El ACK se da después del commit de la transacción local (control de entrada + cambio + panel + outbox); si algo
falla antes, el broker reentrega y el control de entrada evita duplicar el efecto (ADR-0027, QA-6).
"""
from __future__ import annotations

from comun.infraestructura.broker import Broker, Mensaje
from comun.infraestructura.db import con_reintentos
from comun.infraestructura.reloj import parsear
from comun.observabilidad import contexto_correlacion, contexto_traza, continuar_traza, metricas
from contratos.esquemas import ContratoInvalido, validar_evento
from contratos.topologia import COLA_NUCLEO, SHARDS
from nucleo.panel.unidad import UnidadDeCambio
from nucleo.reservas import novedades


class ConsumidorNovedades:
    def __init__(self, nucleo):
        self.nucleo = nucleo
        self.fallar_antes_del_ack = None  # punto de inyección de fallas para las pruebas (V08)

    def suscribir(self, broker: Broker):
        for shard in range(SHARDS):
            broker.consumir(COLA_NUCLEO.format(shard=shard), self.procesar, prefetch=20)

    def procesar(self, mensaje: Mensaje):
        nucleo = self.nucleo
        contexto_traza.set(continuar_traza(mensaje.encabezados.get("traceparent")))
        novedad = mensaje.cuerpo
        contexto_correlacion.set(novedad.get("correlationId"))
        try:
            validar_evento("booking.change.detected.v1", novedad)
        except ContratoInvalido as error:
            # Mensaje inválido: se aparta con causa y se confirma; no se reintenta sin fin (ingestion-contract.md).
            nucleo.logger.alerta("novedad_invalida_apartada", eventId=novedad.get("eventId"), errores=error.errores)
            metricas.incrementar("novedades_invalidas")
            return

        def transaccion():
            with nucleo.ruteo.nodo(novedad["userId"]).transaccion() as tx:
                unidad = UnidadDeCambio(tx, nucleo.region, novedad["userId"], nucleo.reloj,
                                        correlation_ids=[novedad["correlationId"]])
                resultado = novedades.aplicar(tx, unidad, nucleo.ruteo, nucleo.esquemas, nucleo.region, novedad)
                version = unidad.confirmar()
                return resultado, version

        resultado, version = con_reintentos(transaccion)
        if self.fallar_antes_del_ack:
            self.fallar_antes_del_ack(novedad["eventId"])  # caída después del commit y antes del ACK
        metricas.incrementar(f"novedades_{resultado.split(':')[0]}")
        espera = (nucleo.reloj.ahora() - parsear(novedad["detectedAt"])).total_seconds()
        metricas.observar("qa1_deteccion_a_aplicacion_s", max(espera, 0.0))
        nucleo.logger.info("novedad_procesada", eventId=novedad["eventId"], resultado=resultado,
                           panelVersion=version, reentregada=mensaje.reentregado)
