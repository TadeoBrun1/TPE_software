"""Suscriptor de sugerencias aceptadas (`suggestion.accepted.v1`, iteración 5, ADR-0084).

Cola quorum `core.suggestions`. Crea la reserva propuesta en la transacción de la partición del usuario, con control
de entrada por `suggestionId` (Idempotent Receiver), y confirma el mensaje después del commit.
"""
from __future__ import annotations

from comun.infraestructura.broker import Broker, Mensaje
from comun.infraestructura.db import con_reintentos
from comun.observabilidad import contexto_correlacion, contexto_traza, continuar_traza, metricas
from contratos.esquemas import ContratoInvalido, validar_evento
from contratos.topologia import COLA_NUCLEO_SUGERENCIAS
from nucleo.panel.unidad import UnidadDeCambio
from nucleo.reservas import propuestas
from nucleo.usuarios import eliminacion


class ConsumidorSugerencias:
    def __init__(self, nucleo):
        self.nucleo = nucleo

    def suscribir(self, broker: Broker):
        broker.consumir(COLA_NUCLEO_SUGERENCIAS, self.procesar, prefetch=20)

    def procesar(self, mensaje: Mensaje):
        nucleo = self.nucleo
        contexto_traza.set(continuar_traza(mensaje.encabezados.get("traceparent")))
        evento = mensaje.cuerpo
        contexto_correlacion.set(evento.get("correlationId"))
        try:
            validar_evento("suggestion.accepted.v1", evento)
        except ContratoInvalido as error:
            nucleo.logger.alerta("sugerencia_invalida_apartada", eventId=evento.get("eventId"), errores=error.errores)
            return
        if evento["homeRegion"] != nucleo.region:
            nucleo.logger.alerta("sugerencia_de_otra_region", eventId=evento["eventId"])
            return

        def transaccion():
            with nucleo.ruteo.nodo(evento["userId"]).transaccion() as tx:
                if eliminacion.eliminada(tx, evento["userId"]):
                    return "descartada:cuenta_eliminada"  # aceptación atrasada de una cuenta eliminada (ADR-0085)
                correlacion = [evento["correlationId"]] if evento.get("correlationId") else []
                unidad = UnidadDeCambio(tx, nucleo.region, evento["userId"], nucleo.reloj, correlation_ids=correlacion)
                resultado = propuestas.aplicar_aceptacion(tx, unidad, nucleo.ruteo, evento)
                unidad.confirmar()
                return resultado

        resultado = con_reintentos(transaccion)
        metricas.incrementar(f"sugerencias_{resultado.split(':')[0]}")
        nucleo.logger.info("sugerencia_aceptada_aplicada", suggestionId=evento["suggestionId"], resultado=resultado)
