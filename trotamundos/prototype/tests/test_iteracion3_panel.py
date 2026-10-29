"""Iteración 3: panel por lectura por clave, versión y caché, cambios manuales, ciclo de vida y sobrecarga.

ADR-0040, 0041, 0044, 0045, 0046, 0047 y 0048.
"""
from __future__ import annotations

import asyncio
import threading

from starlette.testclient import TestClient

from comun.infraestructura.http import DestinoASGI
from contratos.esquemas import validar_api


def test_reserva_manual_crea_viaje_y_versiona_el_panel(juan, sistema):
    """QA-2 / ADR-0040: un cambio actualiza tablas, panel (versión + 1) y outbox en la misma transacción."""
    assert juan.get("/panel").json()["panelVersion"] == 0
    reserva = juan.reserva("r1", notes="llevar adaptador")
    validar_api("Booking", reserva)
    panel = juan.get("/panel")
    validar_api("Panel", panel.json())
    assert panel.json()["panelVersion"] == 1
    assert panel.headers["etag"] == '"1"'
    viaje = panel.json()["trips"][0]
    assert viaje["name"] == "Madrid 2026-11" and viaje["startDate"] == "2026-11-10"
    assert viaje["bookings"][0]["id"] == reserva["id"]
    # ADR-0041: revalidación por versión
    assert juan.get("/panel", headers={"If-None-Match": '"1"'}).status_code == 304
    # La outbox del núcleo publica panel.changed.v1, trip.changed.v1 y booking.facts.v1
    assert sistema.regiones["sa-east"].nucleo.publicador.publicar_pendientes() == 3


def test_idempotency_key_no_crea_dos_veces(juan):
    primera = juan.reserva("misma-clave")
    segunda = juan.reserva("misma-clave")
    assert primera == segunda
    assert len(juan.get("/panel").json()["trips"][0]["bookings"]) == 1


def test_asignacion_por_fechas(juan):
    """ADR-0048: dentro del viaje o a menos de 2 días se agrega; si no, viaje nuevo. (Las reservas sin fechas, que
    solo llegan por la ingesta, quedan sin asignar: ver test_novedad_sin_fechas_queda_sin_asignar.)"""
    hotel = juan.reserva("a")
    vuelo = juan.reserva("b", type="flight", startsAt="2026-11-08T22:00:00-03:00",
                         endsAt="2026-11-09T14:00:00+01:00", location="EZE", arrivalLocation="MAD")
    assert vuelo["tripId"] == hotel["tripId"]
    otro = juan.reserva("c", startsAt="2026-12-20T15:00:00+01:00", endsAt="2026-12-22T11:00:00+01:00",
                        location="Roma")
    assert otro["tripId"] != hotel["tripId"]
    respuesta = juan.post("/bookings", {"type": "car", "startsAt": "2026-11-11T10:00:00+01:00"},
                          headers={"Idempotency-Key": "d"})
    assert respuesta.status_code == 201
    panel = juan.get("/panel").json()
    assert [v["name"] for v in panel["trips"]] == ["Madrid 2026-11", "Roma 2026-12"]


def test_panel_grande_guarda_15_viajes_completos(juan):
    """ADR-0040: más de 15 viajes activos → los 15 más próximos completos y el resto en resumen."""
    for mes in range(17):
        anio, m = 2027 + mes // 12, mes % 12 + 1
        juan.reserva(f"v{mes}", startsAt=f"{anio}-{m:02d}-10T15:00:00+01:00",
                     endsAt=f"{anio}-{m:02d}-12T11:00:00+01:00", location=f"Ciudad{mes}")
    viajes = juan.get("/panel").json()["trips"]
    assert len(viajes) == 17
    assert all("bookings" in v for v in viajes[:15])
    assert all(v["summaryOnly"] and v["bookingCount"] == 1 and "bookings" not in v for v in viajes[15:])
    detalle = juan.get(f"/trips/{viajes[16]['id']}")
    assert detalle.status_code == 200 and len(detalle.json()["bookings"]) == 1


def test_cambios_concurrentes_del_mismo_usuario(juan, sistema):
    """ADR-0040: bloqueo por usuario; los dos cambios quedan y la versión sube de a uno."""
    juan.reserva("base")
    version = juan.get("/panel").json()["panelVersion"]
    errores = []

    def crear(clave, dia):
        cliente = TestClient(sistema.entrada.app)
        r = cliente.post("/bookings", json={"type": "hotel", "startsAt": f"2026-11-{dia}T15:00:00+01:00",
                                            "location": "Madrid"},
                         headers={**juan.h, "Idempotency-Key": clave})
        if r.status_code != 201:
            errores.append(r.text)

    hilos = [threading.Thread(target=crear, args=(f"c{i}", 11 + i)) for i in range(2)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert not errores
    panel = juan.get("/panel").json()
    assert panel["panelVersion"] == version + 2
    assert len(panel["trips"][0]["bookings"]) == 3


def test_edicion_con_if_match_y_campos_del_usuario(juan):
    """RF-04: If-Match evita pisar un cambio concurrente; los campos editados quedan marcados."""
    reserva = juan.reserva("e")
    sin_version = juan.patch(f"/bookings/{reserva['id']}", {"notes": "x"})
    assert sin_version.status_code == 400
    ok = juan.patch(f"/bookings/{reserva['id']}", {"displayName": "Hotel del centro", "notes": "check-in tarde"},
                    headers={"If-Match": '"1"'})
    assert ok.status_code == 200
    assert ok.json()["userEditedFields"] == ["displayName", "notes"] and ok.json()["version"] == 2
    vieja = juan.patch(f"/bookings/{reserva['id']}", {"notes": "y"}, headers={"If-Match": '"1"'})
    assert vieja.status_code == 412


def test_detalles_por_tipo_se_validan_con_su_esquema(juan):
    """ADR-0066: `details` se valida contra specs/schemas; un esquema no registrado se rechaza."""
    ok = juan.reserva("t1", type="train", startsAt="2026-11-11T09:00:00+01:00",
                      details={"schema": "train.v1", "trainNumber": "AVE 3172", "coach": "5"})
    assert ok["details"]["trainNumber"] == "AVE 3172"
    desconocido = juan.post("/bookings", {"type": "ferry", "startsAt": "2026-11-11T09:00:00+01:00",
                                          "details": {"schema": "ferry.v1", "deck": "3"}},
                            headers={"Idempotency-Key": "t2"})
    assert desconocido.status_code == 400
    invalido = juan.post("/bookings", {"type": "train", "startsAt": "2026-11-11T09:00:00+01:00",
                                       "details": {"schema": "train.v1", "pasajero": "Juan"}},
                         headers={"Idempotency-Key": "t3"})
    assert invalido.status_code == 400


def test_archivado_diario_reactivacion_y_eliminacion(juan, sistema, reloj):
    """ADR-0045: completo = última reserva + 2 días; reactivado a mano no se archiva por 7 días; eliminación al año."""
    nucleo = sistema.regiones["sa-east"].nucleo
    viaje_id = juan.reserva("arch")["tripId"]
    reloj.adelantar(days=16)  # 17/11: ya pasó 14/11 + 2 días
    assert nucleo.tarea_diaria()["archivados"] == 1
    assert juan.get("/panel").status_code == 401  # el token de acceso venció (15 minutos)
    juan.ingresar()
    assert juan.get("/panel").json()["trips"] == []
    archivados = juan.get("/trips/archived").json()["trips"]
    assert archivados[0]["id"] == viaje_id and archivados[0]["status"] == "archived"
    assert nucleo.tarea_diaria()["archivados"] == 0  # idempotente
    reactivado = juan.post(f"/trips/{viaje_id}/reactivate")
    assert reactivado.status_code == 200 and reactivado.json()["reactivatedUntil"] == "2026-11-24"
    assert juan.post(f"/trips/{viaje_id}/reactivate").status_code == 409
    reloj.adelantar(days=5)
    assert nucleo.tarea_diaria()["archivados"] == 0  # todavía dentro de los 7 días
    reloj.adelantar(days=3)
    assert nucleo.tarea_diaria()["archivados"] == 1
    reloj.adelantar(days=366)
    assert nucleo.tarea_diaria()["eliminados"] == 1
    juan.ingresar()
    assert juan.get(f"/trips/{viaje_id}").status_code == 404


def test_prioridades_ante_sobrecarga(juan, sistema):
    """ADR-0047: en sobrecarga se atiende el panel y se rechazan primero las operaciones de prioridad baja y media."""
    puerta = sistema.regiones["sa-east"].puerta
    puerta.sobrecarga.forzada = 0.6
    assert juan.get("/trips/archived").status_code == 503
    assert juan.reserva("med")["id"]
    puerta.sobrecarga.forzada = 0.9
    respuesta = juan.post("/bookings", {"type": "hotel", "startsAt": "2026-11-11T10:00:00+01:00"},
                          headers={"Idempotency-Key": "med2"})
    assert respuesta.status_code == 503 and respuesta.headers["retry-after"]
    assert juan.get("/panel").status_code == 200


def test_limite_por_cliente_responde_429_y_audita_en_rutas_de_recurso(juan, sistema):
    puerta = sistema.regiones["sa-east"].puerta
    puerta.limite.capacidad, puerta.limite.por_segundo = 2, 0.0001
    puerta.limite._cubetas.clear()
    assert juan.get("/panel").status_code == 200
    assert juan.get("/panel").status_code == 200
    respuesta = juan.delete("/bookings/000-" + "0" * 32, headers={"If-Match": '"1"'})
    assert respuesta.status_code == 429
    registros = sistema.regiones["sa-east"].nucleo.auditoria.consultar(reason="rate_limited")
    assert registros and registros[0]["actor_user_id"] == juan.user_id


def test_aviso_sse_ready_y_cambio(juan, sistema):
    """ADR-0046: ready al conectar; después, panel-changed con la versión nueva (y correlationIds)."""
    region = sistema.regiones["sa-east"]
    ticket = juan.post("/panel/events/ticket")
    assert ticket.status_code == 201

    async def escenario():
        puerta = DestinoASGI(region.puerta.app)
        entrada = DestinoASGI(sistema.entrada.app)  # la entrada global reenvía el flujo a medida que llega
        flujo = await entrada.abrir_flujo("GET", f"/panel/events?ticket={ticket.json()['ticket']}", {})
        assert flujo.estado == 200
        partes = flujo.partes.__aiter__()
        assert (await partes.__anext__()).startswith(b"event: ready")
        cambio = await puerta.enviar("POST", "/bookings", {**juan.h, "Idempotency-Key": "sse",
                                                           "content-type": "application/json"},
                                     b'{"type": "hotel", "startsAt": "2026-11-10T15:00:00+01:00"}')
        assert cambio.estado == 201
        region.nucleo.publicador.publicar_pendientes()
        region.broker.bombear()
        aviso = await asyncio.wait_for(partes.__anext__(), timeout=2)
        await flujo.cerrar()
        return aviso

    aviso = asyncio.run(escenario())
    assert aviso.startswith(b"event: panel-changed") and b'"panelVersion": 1' in aviso


def test_ticket_sse_vencido_o_usado_como_token(juan, sistema, reloj):
    ticket = juan.post("/panel/events/ticket").json()["ticket"]
    como_token = juan.cliente.http.get("/panel", headers={"Authorization": f"Bearer {ticket.split(':', 1)[1]}"})
    assert como_token.status_code == 401
    reloj.adelantar(seconds=31)
    vencido = juan.cliente.http.get(f"/panel/events?ticket={ticket}")
    assert vencido.status_code == 401


def test_panel_regenerado_desde_las_tablas_es_igual(juan, sistema):
    """ADR-0040: el documento guardado coincide con el que se arma desde las tablas (fuente de verdad)."""
    from nucleo.panel import proyector

    juan.reserva("a")
    juan.reserva("b", type="car", startsAt="2026-12-20T10:00:00+01:00", endsAt="2026-12-21T10:00:00+01:00")
    nucleo = sistema.regiones["sa-east"].nucleo
    with nucleo.ruteo.nodo(juan.user_id).transaccion() as tx:
        guardado = proyector.leer(tx, juan.user_id)
        regenerado = proyector.construir(tx, juan.user_id, guardado["panelVersion"], nucleo.reloj)
    assert regenerado == guardado and len(guardado["trips"]) == 2


def test_telemetria_del_panel_mostrado(juan, sistema):
    """ADR-0067: la app informa qué versión mostró; los reportes repetidos se deduplican."""
    reporte = {"panelVersion": 1, "shownAt": "2026-11-01T12:00:01Z", "correlationIds": ["c-1"]}
    assert juan.post("/telemetry/panel-shown", reporte).status_code == 202
    assert juan.post("/telemetry/panel-shown", reporte).status_code == 202
    nucleo = sistema.regiones["sa-east"].nucleo
    with nucleo.ruteo.nodo(juan.user_id).transaccion() as tx:
        assert tx.uno("SELECT COUNT(*) AS n FROM telemetria_panel")["n"] == 1
    assert juan.post("/telemetry/panel-shown", {"panelVersion": 1}).status_code == 400


def test_dos_instancias_del_notificador(juan, sistema, tmp_path):
    """ADR-0046: cada instancia recibe el aviso en su cola; solo la que tiene la conexión lo envía."""
    from comun.infraestructura.db import SQLite
    from comun.observabilidad import Logger, metricas
    from contratos.topologia import cola_instancia_notificador
    from notificador.app import Notificador

    region = sistema.regiones["sa-east"]
    otra = Notificador("sa-east", region.broker, SQLite(str(tmp_path / "push2.db")), region.clave_puerta,
                       reloj=sistema.reloj, logger=Logger("notificador", "sa-east", salida=None))
    otra.preparar_mensajeria()
    ticket = juan.post("/panel/events/ticket").json()["ticket"]
    enviados_antes = metricas.resumen()["contadores"].get("sse_aviso_enviado", 0)

    async def escenario():
        flujo = await DestinoASGI(sistema.entrada.app).abrir_flujo("GET", f"/panel/events?ticket={ticket}", {})
        partes = flujo.partes.__aiter__()
        await partes.__anext__()  # ready
        juan.reserva("dos-instancias")
        sistema.procesar()
        aviso = await asyncio.wait_for(partes.__anext__(), timeout=2)
        await flujo.cerrar()
        return aviso

    assert asyncio.run(escenario()).startswith(b"event: panel-changed")
    assert region.broker.pendientes(cola_instancia_notificador(otra.instancia).nombre) == 0  # la otra lo descartó
    assert metricas.resumen()["contadores"]["sse_aviso_enviado"] == enviados_antes + 1
