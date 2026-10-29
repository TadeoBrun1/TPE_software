"""Ciclo de vida de los viajes (ADR-0045): archivado diario, reactivación y eliminación al año."""
from __future__ import annotations

from datetime import date, timedelta

from comun.infraestructura.db import Transaccion, con_reintentos
from comun.infraestructura.reloj import Reloj
from nucleo.datos.ruteo import RuteoParticiones
from nucleo.panel.unidad import UnidadDeCambio

MARGEN_COMPLETO = timedelta(days=2)       # completo: última reserva + 2 días
DIAS_REACTIVACION = timedelta(days=7)     # reactivado a mano: no se archiva por 7 días (suposición)
RETENCION_ARCHIVADOS = timedelta(days=365)  # eliminación 1 año después de archivado (suposición)


def completo(viaje: dict, hoy: date) -> bool:
    if not viaje["fecha_fin"]:
        return False
    limite = date.fromisoformat(viaje["fecha_fin"]) + MARGEN_COMPLETO
    if viaje["reactivado_hasta"]:
        limite = max(limite, date.fromisoformat(viaje["reactivado_hasta"]))
    return hoy > limite


def archivar(tx: Transaccion, unidad: UnidadDeCambio, viaje: dict, hoy: date):
    tx.ejecutar("UPDATE viajes SET estado = 'archivado', archivado_en = ? WHERE trip_id = ?",
                (hoy.isoformat(), viaje["trip_id"]))
    unidad.viaje(viaje["trip_id"], "archived")
    unidad.motivo("trip_archived")


def reactivar(tx: Transaccion, unidad: UnidadDeCambio, viaje: dict, hoy: date, a_mano: bool):
    hasta = (hoy + DIAS_REACTIVACION).isoformat() if a_mano else viaje["reactivado_hasta"]
    tx.ejecutar("UPDATE viajes SET estado = 'activo', archivado_en = NULL, reactivado_hasta = ? WHERE trip_id = ?",
                (hasta, viaje["trip_id"]))
    unidad.viaje(viaje["trip_id"], "reactivated")
    unidad.motivo("trip_reactivated")


def eliminar(tx: Transaccion, unidad: UnidadDeCambio, viaje: dict):
    """Elimina el viaje con sus reservas, marcas de borrado e invitaciones (y el email de los invitados)."""
    trip_id = viaje["trip_id"]
    tx.ejecutar("DELETE FROM reservas WHERE trip_id = ?", (trip_id,))
    tx.ejecutar("DELETE FROM marcas_borrado WHERE trip_id = ?", (trip_id,))
    tx.ejecutar("DELETE FROM comparticiones WHERE trip_id = ?", (trip_id,))
    tx.ejecutar("DELETE FROM viajes WHERE trip_id = ?", (trip_id,))
    unidad.viaje(trip_id, "deleted")
    unidad.motivo("trip_deleted")


def tarea_diaria(ruteo: RuteoParticiones, reloj: Reloj, region: str, logger) -> dict:
    """Recorre cada partición, archiva los viajes completos y elimina los archivados vencidos.

    Cada viaje se procesa en su propia transacción; si la tarea se corta, la siguiente ejecución retoma
    (idempotente). Se programa en el horario de menor carga de la región.
    """
    hoy = reloj.hoy()
    resultado = {"archivados": 0, "eliminados": 0}
    for nodo in ruteo.nodos:
        for particion in ruteo.particiones_de(nodo):
            with nodo.transaccion() as tx:
                activos = tx.todos("SELECT trip_id, user_id FROM viajes WHERE particion = ? AND estado = 'activo' "
                                   "AND fecha_fin IS NOT NULL AND fecha_fin < ?",
                                   (particion, (hoy - MARGEN_COMPLETO).isoformat()))
                vencidos = tx.todos("SELECT trip_id, user_id FROM viajes WHERE particion = ? AND estado = 'archivado' "
                                    "AND archivado_en < ?", (particion, (hoy - RETENCION_ARCHIVADOS).isoformat()))
            for fila in activos:
                if con_reintentos(lambda: _procesar(nodo, ruteo, reloj, region, fila, "archivar")):
                    resultado["archivados"] += 1
            for fila in vencidos:
                if con_reintentos(lambda: _procesar(nodo, ruteo, reloj, region, fila, "eliminar")):
                    resultado["eliminados"] += 1
    logger.info("tarea_diaria_terminada", **resultado)
    return resultado


def _procesar(nodo, ruteo, reloj, region, fila, accion) -> bool:
    with nodo.transaccion() as tx:
        unidad = UnidadDeCambio(tx, region, fila["user_id"], reloj)
        viaje = tx.uno("SELECT * FROM viajes WHERE trip_id = ?", (fila["trip_id"],))  # se vuelve a leer con el bloqueo
        hoy = reloj.hoy()
        if viaje is None:
            return False
        if accion == "archivar" and viaje["estado"] == "activo" and completo(viaje, hoy):
            archivar(tx, unidad, viaje, hoy)
        elif accion == "eliminar" and viaje["estado"] == "archivado" and \
                date.fromisoformat(viaje["archivado_en"]) < hoy - RETENCION_ARCHIVADOS:
            eliminar(tx, unidad, viaje)
        else:
            return False
        unidad.confirmar()
        return True
