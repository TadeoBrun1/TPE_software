"""Baja de cuentas en la ingesta (iteración 5, ADR-0085): consume `account.deleted.v1` en `ingestion.accounts`.

Borra las vinculaciones del usuario con su configuración técnica (remitentes, secreto de avisos), los cursores, el
trabajo pendiente, los avisos recibidos, los resultados y sus novedades en la outbox. En el sistema real
también revoca las autorizaciones delegadas en el proveedor de correo o de reservas (ADR-0021); en el prototipo la
autorización está simulada. Idempotente: borrar lo que ya no existe no es un error.
"""
from __future__ import annotations

import json

from comun.infraestructura.broker import Mensaje
from comun.infraestructura.db import con_reintentos
from comun.observabilidad import contexto_traza, continuar_traza, metricas
from contratos.esquemas import ContratoInvalido, validar_evento

TABLAS_POR_VINCULACION = ("cursores", "trabajos", "avisos_recibidos", "resultados", "claves_publicadas")


class BajasDeCuentas:
    def __init__(self, ingesta):
        self.ingesta = ingesta

    def procesar(self, mensaje: Mensaje):
        ingesta = self.ingesta
        contexto_traza.set(continuar_traza(mensaje.encabezados.get("traceparent")))
        try:
            validar_evento("account.deleted.v1", mensaje.cuerpo)
        except ContratoInvalido as error:
            ingesta.logger.alerta("baja_invalida_apartada", errores=error.errores)
            return
        user_id = mensaje.cuerpo["userId"]

        def transaccion() -> int:
            with ingesta.registro.base.transaccion() as tx:
                conexiones = [f["connection_id"] for f in tx.todos(
                    "SELECT connection_id FROM vinculaciones WHERE user_id = ?", (user_id,))]
                for connection_id in conexiones:
                    for tabla in TABLAS_POR_VINCULACION:
                        tx.ejecutar(f"DELETE FROM {tabla} WHERE connection_id = ?", (connection_id,))
                tx.ejecutar("DELETE FROM vinculaciones WHERE user_id = ?", (user_id,))
                # Novedades del usuario en la outbox: las enviadas ya no hacen falta y las pendientes, ya no tienen
                # destino.
                for fila in tx.todos("SELECT event_id, cuerpo FROM outbox"):
                    if json.loads(fila["cuerpo"]).get("userId") == user_id:
                        tx.ejecutar("DELETE FROM outbox WHERE event_id = ?", (fila["event_id"],))
                return len(conexiones)

        vinculaciones = con_reintentos(transaccion)
        metricas.incrementar("ingesta_cuentas_eliminadas")
        ingesta.logger.info("cuenta_eliminada_en_ingesta", vinculaciones=vinculaciones)
