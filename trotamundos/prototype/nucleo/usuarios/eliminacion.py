"""Eliminación de la cuenta (iteración 5, ADR-0085): borrado inmediato de los datos del usuario en el núcleo.

En una sola transacción de la partición del usuario se borran sus viajes, reservas, panel, avisos, invitaciones
que hizo, marcadores de viajes compartidos con él, vinculaciones, claves de idempotencia y controles de entrada; se
deja la marca de cuenta eliminada y se escribe `account.deleted.v1` en la outbox. Los demás procesos de la región
borran lo suyo al recibir el evento.

Lo que está fuera de esa partición (los permisos del usuario sobre viajes de otros usuarios de la región y el actor en
los registros de auditoría) lo hace `completar`, que el núcleo ejecuta al consumir su propio `account.deleted.v1` en
la cola `core.accounts`: si el proceso cae o la auditoría falla, el mensaje se reentrega y se repite (idempotente).

La marca de cuenta eliminada dura 30 días (suposición): mientras tanto, un token de acceso que siga vigente recibe
401 y se descartan las novedades o sugerencias atrasadas de ese usuario.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import timedelta

from comun.infraestructura.db import Transaccion, con_reintentos
from comun.infraestructura.reloj import iso
from nucleo.mensajeria import eventos

VIGENCIA_MARCA = timedelta(days=30)  # suposición: más que la vida de los mensajes en las colas

# Tablas de la partición del usuario con su columna de usuario.
TABLAS_DEL_USUARIO = (("reservas", "user_id"), ("viajes", "user_id"), ("marcas_borrado", "user_id"),
                      ("avisos", "user_id"), ("panel_por_usuario", "user_id"), ("novedades_procesadas", "user_id"),
                      ("casos_pendientes", "user_id"), ("sugerencias_aplicadas", "user_id"),
                      ("idempotencia", "user_id"), ("comparticiones", "owner_user_id"),
                      ("referencias_compartidas", "user_id"), ("vinculaciones", "user_id"), ("usuarios", "user_id"))


def eliminada(tx: Transaccion, user_id: str) -> bool:
    return tx.uno("SELECT 1 AS x FROM cuentas_eliminadas WHERE user_id = ?", (user_id,)) is not None


def codigo_actor(clave: bytes, region: str, user_id: str) -> str:
    """Seudónimo estable del actor eliminado: el equipo de seguridad puede seguir agrupando sus intentos."""
    return "eliminada:" + hmac.new(clave, f"{region}:{user_id}".encode(), hashlib.sha256).hexdigest()[:24]


def eliminar_cuenta(nucleo, user_id: str) -> dict:
    region, ahora = nucleo.region, iso(nucleo.reloj.ahora())

    def transaccion() -> dict:
        borrados = {}
        with nucleo.ruteo.nodo(user_id).transaccion() as tx:
            if eliminada(tx, user_id):
                return {"resultado": "ya_eliminada"}
            for tabla, columna in TABLAS_DEL_USUARIO:
                borrados[tabla] = tx.ejecutar(f"DELETE FROM {tabla} WHERE {columna} = ?", (user_id,))
            borrados["telemetria_panel"] = tx.ejecutar("DELETE FROM telemetria_panel WHERE principal = ?",
                                                       (f"{region}:{user_id}",))
            borrados["outbox"] = borrar_de_outbox(tx, user_id)
            tx.ejecutar("INSERT INTO cuentas_eliminadas (user_id, home_region, eliminada) VALUES (?, ?, ?)",
                        (user_id, region, ahora))
            eventos.cuenta_eliminada(tx, region, user_id, ahora)
        return {"resultado": "eliminada", "borrados": borrados}

    resultado = con_reintentos(transaccion)
    nucleo.logger.info("cuenta_eliminada", resultado=resultado["resultado"])
    return resultado


def completar(nucleo, mensaje) -> None:
    """Consumidor de `account.deleted.v1` en `core.accounts`: quita permisos y seudonimiza la auditoría. Si algo
    falla, la excepción hace que el mensaje se reentregue."""
    from contratos.esquemas import validar_evento

    validar_evento("account.deleted.v1", mensaje.cuerpo)
    if mensaje.cuerpo["homeRegion"] != nucleo.region:
        return
    user_id = mensaje.cuerpo["userId"]
    permisos = quitar_permisos(nucleo, user_id)
    registros = nucleo.auditoria.seudonimizar_actor(nucleo.region, user_id,
                                                    codigo_actor(nucleo.clave_seudonimos, nucleo.region, user_id))
    nucleo.logger.info("cuenta_eliminada_completada", permisos=permisos, registros_auditoria=registros)


def borrar_de_outbox(tx: Transaccion, user_id: str) -> int:
    """Eventos del usuario en la outbox, enviados o no: los enviados ya no hacen falta y los pendientes ya no tienen
    sentido (sus consumidores reciben `account.deleted.v1`). En operación la outbox enviada solo guarda el contenido
    24 h (`ingestion-operations.md`); el prototipo la recorre entera."""
    total = 0
    for fila in tx.todos("SELECT event_id, cuerpo FROM outbox"):
        if json.loads(fila["cuerpo"]).get("userId") == user_id:
            total += tx.ejecutar("DELETE FROM outbox WHERE event_id = ?", (fila["event_id"],))
    return total


def quitar_permisos(nucleo, user_id: str) -> int:
    """Invitaciones aceptadas por el usuario en viajes de otros usuarios de la región (en cualquier partición)."""
    total = 0
    for nodo in nucleo.ruteo.nodos:
        with nodo.transaccion() as tx:
            total += tx.ejecutar("DELETE FROM comparticiones WHERE aceptada_region = ? AND aceptada_usuario = ?",
                                 (nucleo.region, user_id))
    return total


def purgar_marcas(ruteo, reloj) -> int:
    """Tarea diaria: borra las marcas de cuenta eliminada vencidas."""
    limite = iso(reloj.ahora() - VIGENCIA_MARCA)
    total = 0
    for nodo in ruteo.nodos:
        with nodo.transaccion() as tx:
            total += tx.ejecutar("DELETE FROM cuentas_eliminadas WHERE eliminada < ?", (limite,))
    return total
