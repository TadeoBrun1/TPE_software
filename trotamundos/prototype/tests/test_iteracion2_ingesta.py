"""Iteración 2: ingesta idempotente de correos y APIs de proveedores hasta el panel.

Escenarios de `ingestion-validation.md` (V01–V09, V11 y V16) sobre el sistema en proceso. Los escenarios de capacidad,
quórum o fallas de nodos (V12–V15) necesitan la infraestructura real y no se cubren acá (ver README).
ADR-0020 a 0028, ADR-0044 y `specs/ingestion-contract.md`.
"""
from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from comun.observabilidad import trace_id
from contratos.esquemas import validar_evento
from contratos.topologia import EXCHANGE_INGESTA, topologia_region
from ingesta.avisos.receptor import firma_aviso
from nucleo.reservas import novedades
from simuladores.proveedores import ErrorAutorizacion, ErrorCuota, ErrorTemporal

REMITENTE = "reservas@hotel-granvia.example"
CORREO = """Gracias por reservar.
Hotel: Gran Vía Centro
Localizador: {ref}
Estado: {estado}
Entrada: 2026-11-10 15:00
Salida: 2026-11-14 11:00
Ciudad: Madrid
Zona: Europe/Madrid"""


def hotel(version: int, estado: str = "CONFIRMED", check_in: str = "2026-11-10", ref: str = "HS-77") -> dict:
    return {"reservationId": ref, "version": version, "status": estado, "checkIn": check_in,
            "checkOut": "2026-11-14", "city": "Madrid", "timeZone": "Europe/Madrid",
            "updatedAt": "2026-11-01T10:00:00Z"}


VUELO = {"pnr": "ABC123", "rev": 1, "state": "HK", "flightNumber": "AR1132",
         "from": {"airport": "EZE", "time": "2026-11-08T22:00", "tz": "America/Argentina/Buenos_Aires"},
         "to": {"airport": "MAD", "time": "2026-11-09T14:00", "tz": "Europe/Madrid"}}


def vincular(sistema, usuario, connection_id: str, provider_id: str, remitentes=None, secreto: str = ""):
    """RF-02 (vincular cuentas) no está en el alcance: la vinculación se carga en el núcleo (autoridad) y en la
    configuración técnica de la ingesta."""
    region = sistema.regiones[usuario.region]
    region.nucleo.registrar_vinculacion(connection_id, usuario.user_id, provider_id)
    region.ingesta.vinculaciones.registrar(connection_id, usuario.user_id, usuario.region, provider_id,
                                           "email" if provider_id == "correo-demo" else "provider",
                                           remitentes=remitentes, secreto_avisos=secreto)
    return region


def consultar(sistema, region, connection_id: str):
    """Trabajo por aviso para la vinculación y ejecución de todos los trabajadores hasta quedar sin pendientes."""
    region.ingesta.agendar(connection_id, "aviso")
    sistema.procesar()


def casos(region, usuario) -> list[tuple[str, str | None]]:
    with region.nucleo.ruteo.nodo(usuario.user_id).transaccion() as tx:
        filas = tx.todos("SELECT motivo, resuelto FROM casos_pendientes WHERE user_id = ?", (usuario.user_id,))
    return sorted((f["motivo"], f["resuelto"]) for f in filas)


def resultados_nucleo(region, usuario) -> list[str]:
    with region.nucleo.ruteo.nodo(usuario.user_id).transaccion() as tx:
        filas = tx.todos("SELECT resultado FROM novedades_procesadas WHERE user_id = ?", (usuario.user_id,))
    return sorted(f["resultado"] for f in filas)


def reservas(usuario) -> list[dict]:
    panel = usuario.get("/panel").json()
    return [r for viaje in panel["trips"] for r in viaje.get("bookings", [])] + panel["unassignedBookings"]


def novedades_publicadas(region) -> list:
    return [m for m in region.broker.publicados if m.exchange == EXCHANGE_INGESTA]


# ------------------------------------------------------------------------------------------ V01 y V02

def test_v01_correo_sin_version_crea_la_reserva(juan, sistema):
    region = vincular(sistema, juan, "con-correo", "correo-demo", remitentes=[REMITENTE])
    region.fuentes["buzon"].recibir("con-correo", REMITENTE, CORREO.format(ref="GV-1", estado="Confirmada"))
    region.fuentes["buzon"].recibir("con-correo", "ofertas@otro.example", CORREO.format(ref="GV-2", estado="Confirmada"))
    sistema.procesar()

    [reserva] = reservas(juan)
    assert reserva["origin"] == "email" and reserva["providerReference"] == "GV-1"
    assert reserva["status"] == "confirmed" and reserva["startsAt"] == "2026-11-10T15:00:00+01:00"
    assert casos(region, juan) == []  # no queda pendiente solo por no tener versión
    assert sorted(r["tipo"] for r in region.ingesta.registro.resultados("con-correo")) == ["descarte", "evento"]

    [novedad] = novedades_publicadas(region)
    validar_evento("booking.change.detected.v1", novedad.cuerpo)
    assert "sourceVersion" not in novedad.cuerpo and novedad.cuerpo["sourceMessageId"]
    # Evidencia por etapa: detección (detectedAt), confirmación en el núcleo (committedAt) y la misma traza.
    panel_cambiado = next(m for m in region.broker.publicados if m.routing_key == "panel.changed.v1")
    assert novedad.cuerpo["correlationId"] in panel_cambiado.cuerpo["correlationIds"]
    assert trace_id(novedad.encabezados["traceparent"]) == trace_id(panel_cambiado.encabezados["traceparent"])
    assert panel_cambiado.cuerpo["committedAt"] >= novedad.cuerpo["detectedAt"]


def test_v02_proveedores_con_formatos_distintos(juan, sistema):
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    vincular(sistema, juan, "con-vuelo", "aerolinea-sur")
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    region.fuentes["aerolinea"].publicar("con-vuelo", VUELO)
    sistema.procesar()

    for mensaje in novedades_publicadas(region):
        validar_evento("booking.change.detected.v1", mensaje.cuerpo)
        assert mensaje.cuerpo["sourceVersion"] == "1" and mensaje.cuerpo["externalReservationId"]
    panel = juan.get("/panel").json()
    [viaje] = panel["trips"]
    assert viaje["startDate"] == "2026-11-08" and viaje["endDate"] == "2026-11-14"
    vuelo, estadia = viaje["bookings"]
    assert vuelo["type"] == "flight" and vuelo["location"] == "EZE" and vuelo["arrivalLocation"] == "MAD"
    assert vuelo["startsAt"] == "2026-11-08T22:00:00-03:00" and vuelo["arrivalTimeZone"] == "Europe/Madrid"
    assert vuelo["details"] == {"schema": "flight.v1", "flightNumber": "AR1132"}
    assert estadia["type"] == "hotel" and estadia["providerReference"] == "HS-77" and estadia["status"] == "confirmed"


def test_novedad_sin_fechas_queda_sin_asignar(juan, sistema):
    """ADR-0048: una reserva sin fechas no se asigna a un viaje; se muestra aparte en el panel."""
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    sin_fechas = {k: v for k, v in hotel(1).items() if k not in ("checkIn", "checkOut")}
    region.fuentes["hotel"].publicar("con-hotel", sin_fechas)
    sistema.procesar()
    panel = juan.get("/panel").json()
    assert panel["trips"] == [] and [r["providerReference"] for r in panel["unassignedBookings"]] == ["HS-77"]


# ------------------------------------------------------------------------------------------ V03 y V04

def test_v03_reentrega_y_reconsulta_sin_duplicar(juan, sistema):
    region = vincular(sistema, juan, "con-correo", "correo-demo", remitentes=[REMITENTE])
    region.fuentes["buzon"].recibir("con-correo", REMITENTE, CORREO.format(ref="GV-1", estado="Confirmada"))
    sistema.procesar()
    version = juan.get("/panel").json()["panelVersion"]

    # Reentrega del mismo evento por el broker: el control de entrada lo reconoce.
    [novedad] = novedades_publicadas(region)
    region.broker.publicar(novedad.exchange, novedad.routing_key, novedad.cuerpo, novedad.encabezados)
    sistema.procesar()
    # Reconsulta del mismo correo (cursor perdido): la clave de negocio evita otra publicación.
    with region.ingesta.registro.base.transaccion() as tx:
        tx.ejecutar("UPDATE cursores SET valor = NULL WHERE connection_id = ?", ("con-correo",))
    consultar(sistema, region, "con-correo")

    assert len(reservas(juan)) == 1 and juan.get("/panel").json()["panelVersion"] == version
    assert len(novedades_publicadas(region)) == 2  # la original y la reentrega manual; ninguna nueva
    assert [r["tipo"] for r in region.ingesta.registro.resultados("con-correo")] == ["evento", "repetido"]
    assert resultados_nucleo(region, juan) == ["aplicada:creada"]  # ID procesado durable


def test_v04_cancelacion_antes_del_alta_por_correo_queda_para_conciliar(juan, sistema):
    region = vincular(sistema, juan, "con-correo", "correo-demo", remitentes=[REMITENTE])
    region.fuentes["buzon"].recibir("con-correo", REMITENTE, CORREO.format(ref="GV-9", estado="Cancelada"))
    sistema.procesar()
    assert casos(region, juan) == [("cancelacion_sin_alta", None)] and reservas(juan) == []
    # Llega la confirmación (sin versión): no hay orden confiable, no se reactiva la cancelación.
    region.fuentes["buzon"].recibir("con-correo", REMITENTE, CORREO.format(ref="GV-9", estado="Confirmada"))
    consultar(sistema, region, "con-correo")
    assert reservas(juan) == []
    assert casos(region, juan) == [("cancelacion_sin_alta", None), ("conflicto_sin_orden", None)]


def test_v04_confirmacion_vieja_no_reactiva_una_cancelacion(juan, sistema):
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    # a) la cancelación (versión 2) llega antes que el alta (versión 1)
    region.fuentes["hotel"].publicar("con-hotel", hotel(2, "CANCELLED", ref="HS-1"))
    sistema.procesar()
    assert casos(region, juan) == [("cancelacion_sin_alta", None)]
    region.fuentes["hotel"].publicar("con-hotel", hotel(1, ref="HS-1"))
    consultar(sistema, region, "con-hotel")
    assert [r["status"] for r in reservas(juan)] == ["cancelled"]
    assert casos(region, juan) == [("cancelacion_sin_alta", "asociada")]
    # b) reserva confirmada (v1), cancelada (v3) y una confirmación atrasada (v2)
    for version, estado in ((1, "CONFIRMED"), (3, "CANCELLED"), (2, "CONFIRMED")):
        region.fuentes["hotel"].publicar("con-hotel", hotel(version, estado, ref="HS-2"))
        consultar(sistema, region, "con-hotel")
    estados = {r["providerReference"]: r["status"] for r in reservas(juan)}
    assert estados == {"HS-1": "cancelled", "HS-2": "cancelled"}
    assert "atrasada" in resultados_nucleo(region, juan)


# ------------------------------------------------------------------------------------------ V05 a V08

def test_v05_caida_de_la_ingesta_antes_y_despues_de_confirmar(juan, sistema):
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))

    def caida(connection_id):
        raise RuntimeError("proceso detenido")

    region.ingesta.coordinador.fallar_antes_de_confirmar = caida
    with pytest.raises(RuntimeError):
        region.ingesta.ciclo()
    assert region.ingesta.registro.leer_cursor("con-hotel") == (None, 0)  # no avanzó sin resultados durables
    region.ingesta.coordinador.fallar_antes_de_confirmar = None
    # Después de confirmar y antes de publicar: el evento espera en la outbox.
    region.ingesta.coordinador.ejecutar_pendientes()
    assert region.ingesta.publicador.antiguedad_pendientes(region.ingesta.registro.base) == 1
    assert reservas(juan) == []
    sistema.procesar()
    assert len(reservas(juan)) == 1 and region.ingesta.registro.leer_cursor("con-hotel")[0] == "1"


def test_v06_corte_despues_de_la_confirmacion_del_broker(juan, sistema):
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    region.ingesta.agendar("con-hotel", "aviso")
    region.ingesta.coordinador.ejecutar_pendientes()

    def corte(event_id):
        region.ingesta.publicador.despues_de_confirmar = None
        raise ConnectionError("conexión perdida antes de marcar enviada")

    region.ingesta.publicador.despues_de_confirmar = corte
    with pytest.raises(ConnectionError):
        region.ingesta.publicador.publicar_pendientes()
    sistema.procesar()  # se republica la misma fila
    primera, segunda = novedades_publicadas(region)
    assert primera.cuerpo["eventId"] == segunda.cuerpo["eventId"]
    assert len(reservas(juan)) == 1 and resultados_nucleo(region, juan) == ["aplicada:creada"]


def test_v07_sin_ruta_la_outbox_no_se_marca_enviada(juan, sistema):
    from contratos.topologia import COLA_NUCLEO, RK_NOVEDAD, shard_de_usuario

    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    shard = shard_de_usuario(juan.region, juan.user_id)
    region.broker.borrar_enlace(COLA_NUCLEO.format(shard=shard), EXCHANGE_INGESTA, RK_NOVEDAD.format(shard=shard))
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    sistema.procesar()
    base = region.ingesta.registro.base
    with base.transaccion() as tx:
        fila = tx.uno("SELECT enviado, ultimo_error FROM outbox")
    assert fila["enviado"] is None and fila["ultimo_error"].startswith("sin ruta")
    assert any(r["evento"] == "outbox_mensaje_sin_ruta" for r in region.ingesta.logger.registros)
    assert reservas(juan) == []
    region.broker.declarar(topologia_region())  # se restaura la ruta
    sistema.procesar()
    assert len(reservas(juan)) == 1


def test_v08_caida_del_nucleo_antes_y_despues_del_commit(juan, sistema, monkeypatch):
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    original = novedades.aplicar
    fallas = {"antes_del_commit": 1}

    def aplicar_y_caer(*args, **kwargs):
        resultado = original(*args, **kwargs)
        if fallas["antes_del_commit"]:
            fallas["antes_del_commit"] -= 1
            raise RuntimeError("caída antes del commit")  # la transacción se revierte
        return resultado

    def caer_antes_del_ack(event_id):
        region.nucleo.consumidor.fallar_antes_del_ack = None
        raise RuntimeError("caída después del commit y antes del ACK")

    monkeypatch.setattr(novedades, "aplicar", aplicar_y_caer)
    region.nucleo.consumidor.fallar_antes_del_ack = caer_antes_del_ack
    sistema.procesar()
    # Tres entregas del mismo mensaje: revertida, confirmada sin ACK y reentregada (sin efecto).
    assert len(reservas(juan)) == 1 and resultados_nucleo(region, juan) == ["aplicada:creada"]
    assert juan.get("/panel").json()["panelVersion"] == 1
    hechos = [m for m in region.broker.publicados if m.routing_key == "booking.facts.v1"]
    assert len(hechos) == 1  # la outbox del núcleo quedó coherente con la transacción
    # Un cambio manual también deja su evento confirmado en la outbox.
    juan.reserva("manual")
    sistema.procesar()
    assert len([m for m in region.broker.publicados if m.routing_key == "booking.facts.v1"]) == 2


# ------------------------------------------------------------------------------------------ V09, V11 y V16

def test_v09_desvincular_durante_la_consulta(juan, sistema):
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    region.ingesta.coordinador.fallar_antes_de_confirmar = \
        lambda connection_id: region.ingesta.vinculaciones.marcar(connection_id, "revocada")
    sistema.procesar()
    assert novedades_publicadas(region) == [] and reservas(juan) == []
    region.ingesta.coordinador.fallar_antes_de_confirmar = None
    consultar(sistema, region, "con-hotel")  # revocada: no se inicia otra consulta
    assert region.fuentes["hotel"].consultas == 1


def test_v11_clasificacion_de_errores(juan, sistema, reloj):
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    api = region.fuentes["hotel"]
    api.publicar("con-hotel", hotel(1))
    base = region.ingesta.registro.base

    def trabajo():
        with base.transaccion() as tx:
            return tx.uno("SELECT intentos, reintentar_desde, estado FROM trabajos WHERE estado = 'pendiente'")

    api.fallar_proxima(ErrorTemporal("503 del proveedor"))
    sistema.procesar()
    assert trabajo()["intentos"] == 1 and reservas(juan) == []  # reintento con espera creciente
    reloj.adelantar(seconds=3)
    api.fallar_proxima(ErrorCuota(reintentar_en=120))
    sistema.procesar()
    assert trabajo()["reintentar_desde"] == "2026-11-01T12:02:03Z"  # respeta Retry-After
    reloj.adelantar(seconds=121)
    sistema.procesar()
    assert len(reservas(juan)) == 1

    # Datos inválidos: se aparcan de forma durable (resultado pendiente) y el cursor avanza.
    correo = vincular(sistema, juan, "con-correo", "correo-demo", remitentes=[REMITENTE])
    correo.fuentes["buzon"].recibir("con-correo", REMITENTE, CORREO.format(ref="GV-3", estado="Confirmada")
                                    .replace("Zona: Europe/Madrid", ""))
    sistema.procesar()
    [resultado] = region.ingesta.registro.resultados("con-correo")
    assert resultado["tipo"] == "pendiente" and resultado["motivo"].startswith("dato_invalido")

    # Falla de infraestructura propia: el ciclo se detiene sin avanzar; al volver, sigue.
    region.fuentes["hotel"].publicar("con-hotel", hotel(2, check_in="2026-11-11"))
    region.ingesta.agendar("con-hotel", "aviso")
    base.disponible = False
    with pytest.raises(ConnectionError):
        region.ingesta.ciclo()
    base.disponible = True
    sistema.procesar()
    assert reservas(juan)[0]["startsAt"].startswith("2026-11-11")

    # Autorización inválida: se detiene y pide revinculación (sin reintentos).
    api.fallar_proxima(ErrorAutorizacion("token revocado por el proveedor"))
    consultar(sistema, region, "con-hotel")
    assert region.ingesta.vinculaciones.obtener("con-hotel")["estado"] == "requiere_revinculacion"
    assert any(r["evento"] == "autorizacion_invalida" for r in region.ingesta.logger.registros)


def test_v16_aviso_perdido_se_recupera_por_reconciliacion(juan, sistema, reloj):
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    sistema.procesar()  # primera reconciliación, sin novedades
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))  # el aviso del proveedor se pierde
    sistema.procesar()
    assert reservas(juan) == []
    reloj.adelantar(minutes=15)
    sistema.procesar()
    juan.renovar()
    assert len(reservas(juan)) == 1


# ------------------------------------------------------------------------------------------ avisos y dueño por campo

def test_aviso_firmado_por_la_puerta_de_entrada(juan, sistema):
    region = vincular(sistema, juan, "con-hotel", "hotel-sol", secreto="secreto-de-suscripcion")
    puerta = TestClient(region.puerta.app)
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    cuerpo = json.dumps({"avisoId": "aviso-1", "connectionId": "con-hotel"}).encode()
    firma = firma_aviso("secreto-de-suscripcion", cuerpo)
    falsa = puerta.post("/avisos/hotel-sol", content=cuerpo, headers={"X-Provider-Signature": "0" * 64})
    assert falsa.status_code == 401
    for _ in range(2):  # el aviso repetido no origina otra consulta
        assert puerta.post("/avisos/hotel-sol", content=cuerpo, headers={"X-Provider-Signature": firma}).status_code == 202
    with region.ingesta.registro.base.transaccion() as tx:
        assert tx.uno("SELECT COUNT(*) AS n FROM trabajos WHERE tipo = 'aviso'")["n"] == 1
    sistema.procesar()
    assert len(reservas(juan)) == 1


def test_dueno_por_campo_aviso_importante_y_marca_de_borrado(juan, sistema):
    """ADR-0044: el proveedor gana en sus campos y se avisa si pisó una edición; lo borrado no se recrea."""
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    sistema.procesar()
    [reserva] = reservas(juan)
    editada = juan.patch(f"/bookings/{reserva['id']}", {"startsAt": "2026-11-10T18:00:00+01:00", "notes": "tarde"},
                         headers={"If-Match": f'"{reserva["version"]}"'})
    assert editada.status_code == 200
    region.fuentes["hotel"].publicar("con-hotel", hotel(2, check_in="2026-11-11"))
    consultar(sistema, region, "con-hotel")
    panel = juan.get("/panel").json()
    [reserva] = reservas(juan)
    assert reserva["startsAt"] == "2026-11-11T15:00:00+01:00" and reserva["notes"] == "tarde"
    assert reserva["userEditedFields"] == ["notes"]
    assert [(a["type"], a.get("field")) for a in panel["notices"]] == [("provider_overrode_user_edit", "startsAt")]
    # El aviso es importante: genera un push; una reentrega del mismo evento no lo repite.
    assert [p["reason"] for p in region.notificador.push.enviados] == ["provider_overrode_user_edit"]
    aviso = next(m for m in region.broker.publicados if m.cuerpo.get("reason") == "provider_overrode_user_edit")
    region.broker.publicar(aviso.exchange, aviso.routing_key, aviso.cuerpo, aviso.encabezados)
    sistema.procesar()
    assert len(region.notificador.push.enviados) == 1
    # Marca de borrado: el usuario borra la reserva importada y una novedad posterior no la recrea.
    assert juan.delete(f"/bookings/{reserva['id']}", headers={"If-Match": f'"{reserva["version"]}"'}).status_code == 204
    region.fuentes["hotel"].publicar("con-hotel", hotel(3, check_in="2026-11-12"))
    consultar(sistema, region, "con-hotel")
    assert reservas(juan) == [] and "descartada_por_usuario" in resultados_nucleo(region, juan)


# ------------------------------------------------------------------------------------------ procesos separados

def test_consultas_con_la_ingesta_detenida(juan, sistema):
    """ADR-0001: con la ingesta detenida, el panel sigue respondiendo; los avisos de proveedores esperan."""
    region = vincular(sistema, juan, "con-hotel", "hotel-sol", secreto="s")
    juan.reserva("manual")
    region.destinos["ingesta"].disponible = False
    assert juan.get("/panel").status_code == 200
    assert TestClient(region.puerta.app).post("/avisos/hotel-sol", content=b"{}").status_code == 503


def test_nucleo_detenido_la_ingesta_sigue_publicando(juan, sistema):
    """ADR-0002: sin consumidor del núcleo, las novedades esperan en su cola y se aplican al volver."""
    from contratos.topologia import COLA_NUCLEO, shard_de_usuario

    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    cola = COLA_NUCLEO.format(shard=shard_de_usuario(juan.region, juan.user_id))
    manejador = region.broker.manejadores.pop(cola)  # el núcleo está detenido
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    sistema.procesar()
    assert region.broker.pendientes(cola) == 1 and reservas(juan) == []
    region.broker.consumir(cola, manejador)  # el núcleo vuelve
    sistema.procesar()
    assert region.broker.pendientes(cola) == 0 and len(reservas(juan)) == 1
