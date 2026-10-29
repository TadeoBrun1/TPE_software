"""Aplicación de novedades externas en el núcleo (ADR-0044, ADR-0048, `specs/ingestion-contract.md`).

Todo ocurre en una transacción local de la partición del usuario: control de entrada (*Idempotent Receiver*),
cambio, panel y outbox. Una novedad describe estado observado, no una orden: el núcleo decide si la aplica, la
descarta o la deja como caso pendiente de conciliación, sin inventar asociaciones.
"""
from __future__ import annotations

import json
import uuid

from comun.infraestructura.db import Transaccion
from nucleo.datos.ruteo import RuteoParticiones
from nucleo.esquemas.registro import DetallesInvalidos, RegistroEsquemas
from nucleo.panel.unidad import UnidadDeCambio
from nucleo.reservas.modelo import CAMPOS_HORARIO
from nucleo.viajes import asignacion
from nucleo.viajes.ciclo_vida import reactivar

ESTADOS = {"confirmed": "confirmed", "pending": "pending", "cancelled": "cancelled", "unknown": "pending"}

# Campo canónico de la novedad → campo de la API y columna. Todos son campos del proveedor (ADR-0044).
CAMPOS_NOVEDAD = {
    "startAt": ("startsAt", "inicio"), "endAt": ("endsAt", "fin"), "timeZone": ("timeZone", "zona"),
    "arrivalTimeZone": ("arrivalTimeZone", "zona_llegada"), "location": ("location", "lugar"),
    "arrivalLocation": ("arrivalLocation", "lugar_llegada"),
}


def comparar_versiones(actual: str | None, nueva: str | None) -> int | None:
    """Orden de `sourceVersion` según el contrato del proveedor: numérico si ambas lo son. None = sin orden."""
    if actual is None or nueva is None:
        return None
    if actual.isdigit() and nueva.isdigit():
        return (int(nueva) > int(actual)) - (int(nueva) < int(actual))
    return 0 if actual == nueva else None


def _pendiente(tx: Transaccion, user_id: str, novedad: dict, motivo: str, ahora: str) -> str:
    """Caso de resolución con contenido mínimo (sin cuerpos de correo ni datos personales)."""
    reserva = novedad.get("reservation", {})
    resumen = {"source": novedad.get("source"), "changeType": novedad.get("changeType"),
               "type": reserva.get("type"), "status": reserva.get("status"),
               "reservationKey": novedad.get("reservationKey")}
    tx.ejecutar("INSERT INTO casos_pendientes (caso_id, user_id, event_id, motivo, resumen, reservation_key, "
                "source_version, creado) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, novedad["eventId"], motivo, json.dumps(resumen),
                 novedad.get("reservationKey"), novedad.get("sourceVersion"), ahora))
    return f"pendiente:{motivo}"


def _resolver_casos(tx: Transaccion, caso_ids: list[str], resolucion: str):
    for caso_id in caso_ids:
        tx.ejecutar("UPDATE casos_pendientes SET resuelto = ? WHERE caso_id = ?", (resolucion, caso_id))


def _aviso(tx: Transaccion, user_id: str, tipo: str, booking_id: str, campo: str | None, ahora: str):
    tx.ejecutar("INSERT INTO avisos (notice_id, user_id, tipo, booking_id, campo, creado) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, tipo, booking_id, campo, ahora))


def _estado_normalizado(reserva_externa: dict) -> dict:
    estado = {api: reserva_externa.get(clave) for clave, (api, _) in CAMPOS_NOVEDAD.items()}
    estado["status"] = ESTADOS.get(reserva_externa.get("status"), "pending")
    estado["type"] = reserva_externa.get("type")
    estado["details"] = reserva_externa.get("details")
    return estado


def _estado_actual(fila: dict) -> dict:
    estado = {api: fila[col] for _, (api, col) in CAMPOS_NOVEDAD.items()}
    estado["status"] = fila["estado"]
    estado["type"] = fila["tipo"]
    estado["details"] = json.loads(fila["detalles"]) if fila["detalles"] else None
    return estado


def aplicar(tx: Transaccion, unidad: UnidadDeCambio, ruteo: RuteoParticiones, esquemas: RegistroEsquemas,
            region: str, novedad: dict) -> str:
    """Aplica una novedad ya validada contra su contrato. Devuelve el resultado registrado en el control de entrada."""
    user_id = novedad["userId"]
    ahora = unidad.ahora
    if tx.uno("SELECT resultado FROM novedades_procesadas WHERE event_id = ?", (novedad["eventId"],)):
        return "duplicada"  # reentrega o republicación: sin efecto (QA-6)
    resultado = _decidir(tx, unidad, ruteo, esquemas, region, novedad, ahora)
    tx.ejecutar("INSERT INTO novedades_procesadas (event_id, user_id, resultado, procesado) VALUES (?, ?, ?, ?)",
                (novedad["eventId"], user_id, resultado, ahora))
    return resultado


def _decidir(tx, unidad, ruteo, esquemas, region, novedad, ahora) -> str:
    user_id = novedad["userId"]
    if novedad["homeRegion"] != region:
        return _pendiente(tx, user_id, novedad, "region_incorrecta", ahora)
    vinculacion = tx.uno("SELECT * FROM vinculaciones WHERE connection_id = ?", (novedad["connectionId"],))
    if (vinculacion is None or vinculacion["user_id"] != user_id or vinculacion["estado"] != "activa"
            or vinculacion["provider_id"] != novedad["providerId"]):
        # El userId del mensaje es contexto declarado: el núcleo lo verifica contra la vinculación.
        return _pendiente(tx, user_id, novedad, "vinculacion_invalida", ahora)
    if novedad["requiresResolution"]:
        return _pendiente(tx, user_id, novedad, "requiere_resolucion", ahora)
    externa = novedad["reservation"]
    try:
        esquemas.validar(externa["type"], externa.get("details"))
    except DetallesInvalidos:
        return _pendiente(tx, user_id, novedad, "detalles_invalidos", ahora)
    clave = (novedad["connectionId"], novedad["providerId"], novedad["externalReservationId"])
    if tx.uno("SELECT 1 AS x FROM marcas_borrado WHERE connection_id = ? AND provider_id = ? "
              "AND external_reservation_id = ?", clave):
        return "descartada_por_usuario"  # el usuario la borró: no se recrea (ADR-0044)
    existente = tx.uno("SELECT * FROM reservas WHERE connection_id = ? AND provider_id = ? "
                       "AND external_reservation_id = ?", clave)
    if novedad["changeType"] == "cancel":
        return _cancelar(tx, unidad, novedad, existente, ahora)
    if existente is None:
        return _crear(tx, unidad, ruteo, novedad, ahora)
    return _actualizar(tx, unidad, ruteo, novedad, existente, ahora)


def _cancelar(tx, unidad, novedad, existente, ahora) -> str:
    if existente is None:
        return _pendiente(tx, novedad["userId"], novedad, "cancelacion_sin_alta", ahora)
    orden = comparar_versiones(existente["source_version"], novedad.get("sourceVersion"))
    if orden is not None and orden < 0:
        return "atrasada"
    if existente["estado"] == "cancelled":
        return "sin_cambios"
    tx.ejecutar("UPDATE reservas SET estado = 'cancelled', source_version = COALESCE(?, source_version), "
                "version = version + 1 WHERE booking_id = ?", (novedad.get("sourceVersion"), existente["booking_id"]))
    _aviso(tx, existente["user_id"], "booking_cancelled", existente["booking_id"], None, ahora)
    unidad.viaje(existente["trip_id"])
    unidad.motivo("booking_cancelled")
    unidad.reserva(tx.uno("SELECT * FROM reservas WHERE booking_id = ?", (existente["booking_id"],)), "cancelled")
    return "aplicada:cancelada"


def _crear(tx, unidad, ruteo, novedad, ahora) -> str:
    externa = novedad["reservation"]
    estado = _estado_normalizado(externa)
    version_fuente = novedad.get("sourceVersion")
    # Una cancelación que llegó antes del alta quedó pendiente; ahora se puede asociar (ingestion-contract.md).
    cancelaciones = tx.todos("SELECT caso_id, source_version FROM casos_pendientes WHERE user_id = ? "
                             "AND reservation_key = ? AND motivo = 'cancelacion_sin_alta' AND resuelto IS NULL",
                             (novedad["userId"], novedad.get("reservationKey")))
    if cancelaciones:
        ordenes = [comparar_versiones(c["source_version"], novedad.get("sourceVersion")) for c in cancelaciones]
        if any(orden is None for orden in ordenes):
            # Sin orden confiable entre la cancelación y esta confirmación: no se reactiva, se concilia.
            return _pendiente(tx, novedad["userId"], novedad, "conflicto_sin_orden", ahora)
        if all(orden > 0 for orden in ordenes):  # la confirmación es posterior a la cancelación
            _resolver_casos(tx, [c["caso_id"] for c in cancelaciones], "superada")
        else:  # confirmación vieja: el alta queda registrada ya cancelada
            estado["status"] = "cancelled"
            version_fuente = max((c["source_version"] for c in cancelaciones), key=int)
            _resolver_casos(tx, [c["caso_id"] for c in cancelaciones], "asociada")
    booking_id = ruteo.nuevo_id(novedad["userId"])
    tx.ejecutar(
        "INSERT INTO reservas (booking_id, user_id, trip_id, tipo, estado, origen, proveedor, referencia_proveedor, "
        "connection_id, provider_id, external_reservation_id, source_version, inicio, fin, zona, zona_llegada, "
        "lugar, lugar_llegada, detalles, campos_editados, version, creado) "
        "VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', 1, ?)",
        (booking_id, novedad["userId"], estado["type"], estado["status"], novedad["source"],
         novedad["providerId"], novedad["externalReservationId"], novedad["connectionId"], novedad["providerId"],
         novedad["externalReservationId"], version_fuente, estado["startsAt"], estado["endsAt"],
         estado["timeZone"], estado["arrivalTimeZone"], estado["location"], estado["arrivalLocation"],
         json.dumps(estado["details"]) if estado["details"] else None, ahora))
    asignacion.asignar(tx, unidad, ruteo, booking_id)
    unidad.motivo("booking_added")
    unidad.reserva(tx.uno("SELECT * FROM reservas WHERE booking_id = ?", (booking_id,)), "created")
    return "aplicada:creada_cancelada" if estado["status"] == "cancelled" else "aplicada:creada"


def _actualizar(tx, unidad, ruteo, novedad, existente, ahora) -> str:
    nuevo = _estado_normalizado(novedad["reservation"])
    actual = _estado_actual(existente)
    orden = comparar_versiones(existente["source_version"], novedad.get("sourceVersion"))
    if nuevo == actual:
        return "sin_cambios"  # estado equivalente: no se duplica el efecto
    if orden is not None and orden <= 0:
        return "atrasada"
    if orden is None:
        # Sin orden confiable y con estado contradictorio: se conserva para conciliación (ingestion-contract.md).
        # Una confirmación sin versión nunca reactiva una cancelación.
        return _pendiente(tx, existente["user_id"], novedad, "conflicto_sin_orden", ahora)
    editados = set(json.loads(existente["campos_editados"]))
    cambiados = [api for api in nuevo if nuevo[api] != actual[api]]
    asignaciones = {"estado": nuevo["status"], "tipo": nuevo["type"],
                    "detalles": json.dumps(nuevo["details"]) if nuevo["details"] else None,
                    "source_version": novedad.get("sourceVersion")}
    for _, (api, columna) in CAMPOS_NOVEDAD.items():
        asignaciones[columna] = nuevo[api]
    if nuevo["status"] == "confirmed" and existente["estado"] in ("confirmed", "modified") and \
            any(c in cambiados for c in CAMPOS_HORARIO):
        asignaciones["estado"] = "modified"
    pisados = sorted(c for c in cambiados if c in editados)
    for campo in pisados:  # el proveedor cambió un campo que el usuario había editado: se aplica y se avisa
        _aviso(tx, existente["user_id"], "provider_overrode_user_edit", existente["booking_id"], campo, ahora)
    editados -= set(pisados)
    columnas = ", ".join(f"{c} = ?" for c in asignaciones)
    tx.ejecutar(f"UPDATE reservas SET {columnas}, campos_editados = ?, version = version + 1 WHERE booking_id = ?",
                (*asignaciones.values(), json.dumps(sorted(editados)), existente["booking_id"]))
    horario = any(c in cambiados for c in CAMPOS_HORARIO)
    if horario and not pisados:
        _aviso(tx, existente["user_id"], "schedule_changed", existente["booking_id"], None, ahora)
    if "tripId" not in editados:
        viaje = tx.uno("SELECT * FROM viajes WHERE trip_id = ?", (existente["trip_id"],)) if existente["trip_id"] else None
        if viaje and viaje["estado"] == "archivado" and (nuevo["endsAt"] or nuevo["startsAt"] or "")[:10] >= \
                unidad.reloj.hoy().isoformat():
            reactivar(tx, unidad, viaje, unidad.reloj.hoy(), a_mano=False)  # novedad con fechas futuras
            unidad.viaje(viaje["trip_id"])
        elif viaje is None or viaje["estado"] == "activo":
            if horario or existente["trip_id"] is None:
                asignacion.asignar(tx, unidad, ruteo, existente["booking_id"])
    unidad.viaje(existente["trip_id"])
    unidad.motivo("provider_overrode_user_edit" if pisados else "schedule_changed" if horario else "booking_updated")
    unidad.reserva(tx.uno("SELECT * FROM reservas WHERE booking_id = ?", (existente["booking_id"],)), "updated")
    return "aplicada:actualizada"
