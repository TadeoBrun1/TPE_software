"""Iteración 5: recomendación de alternativas con human-in-the-loop (opción A, RF-09).

ADR-0081 a ADR-0084, QA-11 a QA-17, `specs/recommendation.md` y `specs/offer-search.md`. Dos grupos de pruebas:

* De punta a punta sobre el sistema de dos regiones: cancelación del proveedor → sugerencias → push y SSE →
  aceptar, rechazar o ajustar → reserva propuesta en el panel → conciliación con la reserva real.
* Sobre un proceso de recomendación aislado, alimentado con `booking.facts.v1`: disrupción masiva con límites de
  consulta (QA-12), proveedores caídos (QA-17), canario y vuelta atrás (QA-15) y aprendizaje con viajeros
  sintéticos (ADR-0083).

Lo que no demuestran: latencias reales, carga de 15.000 viajeros ni la calidad del modelo con datos reales.
"""
from __future__ import annotations

import asyncio
import json
import random
import statistics
import uuid
from datetime import timedelta

import pytest

from comun.infraestructura.broker import BrokerEnMemoria, Mensaje
from comun.infraestructura.db import SQLite
from comun.infraestructura.http import DestinoASGI
from comun.infraestructura.reloj import RelojFijo, iso
from comun.observabilidad import Logger
from contratos.esquemas import validar_api, validar_evento
from contratos.topologia import EXCHANGE_DOMINIO, RK_ACEPTADA, RK_HECHOS, RK_SUGERENCIAS
from recomendacion.app import Recomendacion, adaptadores_para
from recomendacion.modelo import caracteristicas, ranking
from simuladores.busqueda import BusquedaAerolineaSimulada
from simuladores.datos_sinteticos import generar_viajeros, vuelo_cancelado
from simuladores.proveedores import ErrorTemporal
from conftest import INICIO
from test_iteracion2_ingesta import consultar, hotel, reservas, vincular


def oferta_hotel(i: int, por_noche: float, check_in_hora: str = "15:00", proveedor: str = "hotel-sol") -> dict:
    return {"hotelOfferId": f"of-{i}", "checkIn": "2026-11-10", "checkInTime": check_in_hora, "nights": 4,
            "city": "Madrid", "timeZone": "Europe/Madrid", "total": {"value": por_noche * 4, "currencyCode": "EUR"},
            "bookingLink": f"https://{proveedor}.example/ofertas/{i}"}


def fijar_ofertas(region):
    """Ofertas conocidas: hotel-sol (el proveedor de la reserva cancelada) y hotel-luna, con precios distintos."""
    busqueda = region.fuentes["busqueda"]
    busqueda["hotel-sol"].fijar("Madrid", "2026-11-10", 4, [oferta_hotel(1, 100), oferta_hotel(2, 160),
                                                            oferta_hotel(3, 240)])
    busqueda["hotel-luna"].fijar("Madrid", "2026-11-10", 4, [oferta_hotel(4, 90, proveedor="hotel-luna"),
                                                             oferta_hotel(5, 130, proveedor="hotel-luna"),
                                                             oferta_hotel(6, 300, proveedor="hotel-luna")])


def cancelar_hotel(sistema, usuario):
    """El viajero tiene una reserva de hotel-sol que el proveedor cancela (versión 2)."""
    region = vincular(sistema, usuario, "con-hotel", "hotel-sol")
    fijar_ofertas(region)
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    consultar(sistema, region, "con-hotel")
    region.fuentes["hotel"].publicar("con-hotel", hotel(2, "CANCELLED"))
    consultar(sistema, region, "con-hotel")
    cancelada = reservas(usuario)[0]
    assert cancelada["status"] == "cancelled"
    return region, cancelada


def sugerencias(usuario, trip_id: str) -> dict:
    respuesta = usuario.get(f"/trips/{trip_id}/suggestions")
    assert respuesta.status_code == 200, respuesta.text
    validar_api("SuggestionList", respuesta.json())
    return respuesta.json()


def disponibles(lista: dict) -> list[dict]:
    return [s for s in lista["suggestions"] if s["status"] == "available"]


# ------------------------------------------------------------------------------------------ de punta a punta

def test_cancelacion_del_proveedor_genera_sugerencias_y_una_manual_no(juan, sistema):
    """ADR-0081: solo una cancelación de proveedor o correo dispara la búsqueda (QA-11)."""
    region, cancelada = cancelar_hotel(sistema, juan)
    lista = sugerencias(juan, cancelada["tripId"])
    assert lista["searchStatus"] == "ready"
    mostradas = disponibles(lista)
    assert [s["rank"] for s in mostradas] == [1, 2, 3]
    assert all(s["cancelledBookingId"] == cancelada["id"] and s["type"] == "hotel" for s in mostradas)
    assert len({s["provider"] for s in mostradas}) >= 1 and all(s["offerUrl"].startswith("https://") for s in mostradas)
    # Una reserva manual borrada por el viajero no dispara sugerencias.
    manual = juan.reserva("manual", location="Roma", startsAt="2026-12-10T15:00:00+01:00",
                          endsAt="2026-12-12T11:00:00+01:00")
    assert juan.delete(f"/bookings/{manual['id']}", headers={"If-Match": '"1"'}).status_code in (200, 204)
    sistema.procesar()
    assert sugerencias(juan, manual["tripId"])["searchStatus"] == "none"
    with region.recomendacion.base.transaccion() as tx:
        assert tx.uno("SELECT COUNT(*) AS n FROM busquedas")["n"] == 1


def test_hecho_reentregado_no_duplica(juan, sistema):
    """Idempotent Receiver: el mismo eventId no crea otra búsqueda ni otras sugerencias."""
    region, cancelada = cancelar_hotel(sistema, juan)
    hecho = next(m for m in region.broker.publicados if m.routing_key == RK_HECHOS
                 and m.cuerpo["changeType"] == "cancelled")
    region.recomendacion.hechos.procesar(Mensaje(EXCHANGE_DOMINIO, RK_HECHOS, hecho.cuerpo, hecho.encabezados, True))
    sistema.procesar()
    with region.recomendacion.base.transaccion() as tx:
        assert tx.uno("SELECT COUNT(*) AS n FROM busquedas")["n"] == 1
    assert len(disponibles(sugerencias(juan, cancelada["tripId"]))) == 3


def test_push_de_alternativas_reemplaza_al_de_la_cancelacion(juan, sistema):
    """ADR-0084: los dos push comparten collapseKey, así que en el teléfono el segundo reemplaza al primero."""
    region, cancelada = cancelar_hotel(sistema, juan)
    push = [p for p in region.notificador.push.enviados if p["reason"] in ("booking_cancelled",
                                                                           "alternatives_available")]
    assert [p["reason"] for p in push] == ["booking_cancelled", "alternatives_available"]
    assert {p["collapseKey"] for p in push} == {f"booking-cancel:{cancelada['id']}"}
    assert push[1]["suggestionCount"] == 3 and push[1]["tripId"] == cancelada["tripId"]
    # QA-11 de punta a punta: el notificador mide desde la cancelación confirmada hasta el push (reloj simulado).
    from comun.observabilidad import metricas

    assert metricas.resumen()["duraciones"]["qa11_cancelacion_a_aviso_s"]["max"] <= 120


def test_aviso_sse_de_sugerencias(juan, sistema):
    """Con la app abierta, la sección de sugerencias se entera por SSE (evento suggestions-available)."""
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    fijar_ofertas(region)
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    consultar(sistema, region, "con-hotel")
    ticket = juan.post("/panel/events/ticket").json()["ticket"]

    async def escenario():
        entrada = DestinoASGI(sistema.entrada.app)
        flujo = await entrada.abrir_flujo("GET", f"/panel/events?ticket={ticket}", {})
        partes = flujo.partes.__aiter__()
        assert (await partes.__anext__()).startswith(b"event: ready")
        region.fuentes["hotel"].publicar("con-hotel", hotel(2, "CANCELLED"))
        await asyncio.to_thread(consultar, sistema, region, "con-hotel")
        eventos = []
        while not any(e.startswith(b"event: suggestions-available") for e in eventos):
            eventos.append(await asyncio.wait_for(partes.__anext__(), timeout=2))
        await flujo.cerrar()
        return eventos

    eventos = asyncio.run(escenario())
    assert eventos[0].startswith(b"event: panel-changed")
    datos = json.loads(eventos[-1].split(b"data: ", 1)[1])
    assert datos["suggestionCount"] == 3 and datos["tripId"].startswith("sa-east:")


def test_aceptar_crea_reserva_propuesta_y_la_real_la_concilia(juan, sistema):
    """RF-09.2: aceptar deja una reserva propuesta en el viaje y devuelve el enlace; la reserva real la reemplaza."""
    region, cancelada = cancelar_hotel(sistema, juan)
    elegida = next(s for s in disponibles(sugerencias(juan, cancelada["tripId"])) if s["provider"] == "hotel-sol")
    aceptada = juan.post(f"/suggestions/{elegida['id']}/feedback", {"action": "accept"})
    assert aceptada.status_code == 202
    validar_api("SuggestionAccepted", aceptada.json())
    assert aceptada.json()["offerUrl"] == elegida["offerUrl"]
    assert juan.post(f"/suggestions/{elegida['id']}/feedback", {"action": "accept"}).status_code == 409
    sistema.procesar()
    propuesta = next(r for r in reservas(juan) if r["status"] == "proposed")
    assert propuesta["origin"] == "suggestion" and propuesta["offerUrl"] == elegida["offerUrl"]
    assert propuesta["tripId"] == cancelada["tripId"]
    # Las demás sugerencias del grupo vencen; la aceptada queda registrada.
    estados = {s["id"]: s["status"] for s in sugerencias(juan, cancelada["tripId"])["suggestions"]}
    assert estados[elegida["id"]] == "accepted" and set(estados.values()) <= {"accepted", "expired"}
    # Reentrega del evento: el núcleo no crea otra propuesta.
    evento = next(m for m in region.broker.publicados if m.routing_key == RK_ACEPTADA)
    region.nucleo.consumidor_sugerencias.procesar(Mensaje(EXCHANGE_DOMINIO, RK_ACEPTADA, evento.cuerpo, {}, True))
    assert sum(r["status"] == "proposed" for r in reservas(juan)) == 1
    # El viajero reserva en el proveedor: llega la reserva real por la ingesta y la propuesta desaparece.
    region.fuentes["hotel"].publicar("con-hotel", hotel(1, ref="HS-NUEVA"))
    consultar(sistema, region, "con-hotel")
    estados_panel = sorted(r["status"] for r in reservas(juan))
    assert estados_panel == ["cancelled", "confirmed"]


def test_propuesta_no_mueve_el_viaje_y_vence_con_la_tarea_diaria(juan, sistema, reloj):
    region, cancelada = cancelar_hotel(sistema, juan)
    viaje_antes = juan.get(f"/trips/{cancelada['tripId']}").json()
    elegida = disponibles(sugerencias(juan, cancelada["tripId"]))[0]
    juan.post(f"/suggestions/{elegida['id']}/feedback", {"action": "accept"})
    sistema.procesar()
    viaje = juan.get(f"/trips/{cancelada['tripId']}").json()
    assert (viaje["startDate"], viaje["endDate"]) == (viaje_antes["startDate"], viaje_antes["endDate"])
    reloj.adelantar(days=10)  # pasó la fecha de inicio sin que llegara la reserva real
    assert region.nucleo.tarea_diaria()["propuestas_vencidas"] == 1
    juan.ingresar()
    assert not any(r["status"] == "proposed" for r in reservas(juan))


def test_limites_explicitos_y_rechazo_reordenan(juan, sistema):
    """QA-13: ninguna sugerencia viola un límite explícito; rechazar o ajustar responde con la lista reordenada."""
    region, cancelada = cancelar_hotel(sistema, juan)
    primeras = disponibles(sugerencias(juan, cancelada["tripId"]))
    rechazo = juan.post(f"/suggestions/{primeras[0]['id']}/feedback", {"action": "reject", "reason": "too_expensive"})
    assert rechazo.status_code == 200
    despues = disponibles(rechazo.json())
    assert primeras[0]["id"] not in {s["id"] for s in despues} and len(despues) == 3
    # Ajustar: precio máximo de 700 EUR por la estadía y sin hotel-luna.
    ajuste = {"action": "adjust", "preferences": {"maxPrice": {"amount": 700, "currency": "EUR"},
                                                   "excludedProviders": ["hotel-luna"]}}
    respuesta = juan.post(f"/suggestions/{despues[0]['id']}/feedback", ajuste)
    assert respuesta.status_code == 200
    validas = disponibles(respuesta.json())
    assert validas and all(s["price"]["amount"] <= 700 and s["provider"] != "hotel-luna" for s in validas)
    assert all(s["price"]["amount"] <= 700 for s in disponibles(sugerencias(juan, cancelada["tripId"])))
    preferencias = juan.get("/recommendations/preferences").json()
    assert preferencias["excludedProviders"] == ["hotel-luna"] and preferencias["enabled"] is True
    # Ajustar también refina el modelo: cada sugerencia mostrada que el ajuste excluye es un rechazo débil.
    with region.recomendacion.base.transaccion() as tx:
        feedback = tx.todos("SELECT f.accion, f.motivo, s.oferta FROM feedback f JOIN sugerencias s "
                            "ON s.suggestion_id = f.suggestion_id ORDER BY f.creado, f.accion DESC")
    assert feedback[0]["accion"] == "reject" and feedback[0]["motivo"] == "too_expensive"
    excluidas = [json.loads(f["oferta"]) for f in feedback if f["accion"] == "adjust"]
    assert excluidas and all(o["provider"] == "hotel-luna" or o["price"]["amount"] > 700 for o in excluidas)


def test_opt_out_y_borrado_del_perfil(juan, sistema):
    """QA-14: desactivada no genera sugerencias; borrar el perfil elimina perfil, feedback y sugerencias."""
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    fijar_ofertas(region)
    assert juan.get("/recommendations/preferences").json() == {"enabled": True}  # opt-out: activada por defecto
    apagada = juan.cliente.http.put("/recommendations/preferences", json={"enabled": False}, headers=juan.h)
    assert apagada.status_code == 200 and apagada.json()["enabled"] is False
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    consultar(sistema, region, "con-hotel")
    region.fuentes["hotel"].publicar("con-hotel", hotel(2, "CANCELLED"))
    consultar(sistema, region, "con-hotel")
    trip_id = reservas(juan)[0]["tripId"]
    assert sugerencias(juan, trip_id) == {"tripId": trip_id, "searchStatus": "none", "suggestions": []}
    assert not [p for p in region.notificador.push.enviados if p["reason"] == "alternatives_available"]
    # Borrar el perfil no reactiva la recomendación.
    assert juan.delete("/recommendations/profile").status_code == 204
    with region.recomendacion.base.transaccion() as tx:
        fila = tx.uno("SELECT activada, metricas FROM perfiles WHERE user_id = ?", (juan.user_id,))
        assert tx.uno("SELECT COUNT(*) AS n FROM hechos_recibidos WHERE user_id = ?", (juan.user_id,))["n"] == 0
    assert fila["activada"] == 0 and json.loads(fila["metricas"])["proveedores"] == {}
    assert juan.get("/recommendations/preferences").json()["enabled"] is False


def test_desactivada_no_perfila_ni_recrea_el_perfil(juan, sistema):
    """ADR-0081: con la recomendación desactivada, un hecho nuevo solo se descarta; leer no crea perfiles."""
    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    assert juan.get("/recommendations/preferences").json() == {"enabled": True}
    with region.recomendacion.base.transaccion() as tx:
        assert tx.uno("SELECT COUNT(*) AS n FROM perfiles")["n"] == 0  # leer no creó el perfil
    juan.cliente.http.put("/recommendations/preferences", json={"enabled": False}, headers=juan.h)
    juan.delete("/recommendations/profile")
    region.fuentes["hotel"].publicar("con-hotel", hotel(1, ref="HS-NUEVA"))
    consultar(sistema, region, "con-hotel")
    with region.recomendacion.base.transaccion() as tx:
        fila = tx.uno("SELECT activada, metricas FROM perfiles WHERE user_id = ?", (juan.user_id,))
    assert fila["activada"] == 0 and json.loads(fila["metricas"])["proveedores"] == {}


def test_oferta_vencida_responde_409(juan, sistema, reloj):
    region, cancelada = cancelar_hotel(sistema, juan)
    primera = disponibles(sugerencias(juan, cancelada["tripId"]))[0]
    with region.recomendacion.base.transaccion() as tx:
        fila = tx.uno("SELECT oferta FROM sugerencias WHERE suggestion_id = ?", (primera["id"],))
        oferta = {**json.loads(fila["oferta"]), "expiresAt": iso(reloj.ahora() + timedelta(minutes=10))}
        tx.ejecutar("UPDATE sugerencias SET oferta = ? WHERE suggestion_id = ?", (json.dumps(oferta), primera["id"]))
    reloj.adelantar(minutes=11)
    juan.renovar()
    respuesta = juan.post(f"/suggestions/{primera['id']}/feedback", {"action": "accept"})
    assert respuesta.status_code == 409


def test_borrado_del_perfil_elimina_feedback_y_sugerencias(juan, sistema):
    region, cancelada = cancelar_hotel(sistema, juan)
    primera = disponibles(sugerencias(juan, cancelada["tripId"]))[0]
    juan.post(f"/suggestions/{primera['id']}/feedback", {"action": "reject"})
    assert juan.delete("/recommendations/profile").status_code == 204
    assert juan.delete("/recommendations/profile").status_code == 204  # idempotente
    with region.recomendacion.base.transaccion() as tx:
        for tabla in ("feedback", "sugerencias", "busquedas"):
            assert tx.uno(f"SELECT COUNT(*) AS n FROM {tabla} WHERE user_id = ?", (juan.user_id,))["n"] == 0
    assert sugerencias(juan, cancelada["tripId"])["searchStatus"] == "none"


def test_solo_el_dueno_ve_sus_sugerencias(juan, ana, cliente, sistema):
    """Táctica autorizar actores: otro usuario no ve ni responde sugerencias ajenas; otra región da 404."""
    _, cancelada = cancelar_hotel(sistema, juan)
    primera = disponibles(sugerencias(juan, cancelada["tripId"]))[0]
    pedro = cliente.registrar("pedro@example.com", "AR")  # misma región que juan
    assert sugerencias(pedro, cancelada["tripId"]) == {"tripId": cancelada["tripId"], "searchStatus": "none",
                                                      "suggestions": []}
    assert pedro.post(f"/suggestions/{primera['id']}/feedback", {"action": "accept"}).status_code == 404
    assert ana.get(f"/trips/{cancelada['tripId']}/suggestions").status_code == 404  # no se reenvía entre regiones
    assert juan.get("/trips/xx-yy:123/suggestions").status_code == 404
    assert juan.post(f"/suggestions/{primera['id']}/feedback", {"action": "adjust"}).status_code == 400


def test_prioridad_baja_y_proceso_de_recomendacion_detenido(juan, sistema):
    """QA-16 y ADR-0047: con sobrecarga o con la recomendación caída, el panel sigue y los hechos esperan."""
    from contratos.topologia import COLA_RECOMENDACION

    region = vincular(sistema, juan, "con-hotel", "hotel-sol")
    fijar_ofertas(region)
    region.fuentes["hotel"].publicar("con-hotel", hotel(1))
    consultar(sistema, region, "con-hotel")
    trip_id = reservas(juan)[0]["tripId"]
    region.puerta.sobrecarga.forzada = 0.6
    assert juan.get(f"/trips/{trip_id}/suggestions").status_code == 503
    assert juan.get("/panel").status_code == 200
    region.puerta.sobrecarga.forzada = None
    # La recomendación se detiene: no responde ni consume su cola.
    region.destinos["recomendacion"].disponible = False
    manejador = region.broker.manejadores.pop(COLA_RECOMENDACION)
    region.fuentes["hotel"].publicar("con-hotel", hotel(2, "CANCELLED"))
    consultar(sistema, region, "con-hotel")
    assert juan.get(f"/trips/{trip_id}/suggestions").status_code == 503
    assert juan.get("/panel").status_code == 200 and reservas(juan)[0]["status"] == "cancelled"
    assert region.broker.pendientes(COLA_RECOMENDACION) >= 1
    # Vuelve: procesa lo que esperaba en la cola.
    region.destinos["recomendacion"].disponible = True
    region.broker.consumir(COLA_RECOMENDACION, manejador)
    sistema.procesar()
    assert len(disponibles(sugerencias(juan, trip_id))) == 3


def test_lo_publicado_cumple_los_contratos_nuevos(juan, sistema):
    region, cancelada = cancelar_hotel(sistema, juan)
    elegida = disponibles(sugerencias(juan, cancelada["tripId"]))[0]
    juan.post(f"/suggestions/{elegida['id']}/feedback", {"action": "accept"})
    sistema.procesar()
    publicados = {m.routing_key: m for m in region.broker.publicados}
    validar_evento("suggestions.available.v1", publicados[RK_SUGERENCIAS].cuerpo)
    validar_evento("suggestion.accepted.v1", publicados[RK_ACEPTADA].cuerpo)
    hechos = [m.cuerpo for m in region.broker.publicados if m.routing_key == RK_HECHOS]
    assert all("startsAt" in h for h in hechos)  # booking.facts.v1 0.2.0
    assert all(h["status"] != "proposed" for h in hechos)  # las propuestas no generan hechos
    assert "booking.changed.v1" not in {m.routing_key for m in region.broker.publicados}  # retirado


# ------------------------------------------------------------------------------------------ proceso aislado

REGION = "sa-east"


def hecho_cancelacion(user_id: str, cancelada: dict, trip_id: str | None = None) -> dict:
    return {"eventId": str(uuid.uuid4()), "schemaVersion": "1", "correlationId": str(uuid.uuid4()),
            "homeRegion": REGION, "userId": user_id, "tripId": trip_id or f"{REGION}:viaje-{user_id}",
            "bookingId": f"{REGION}:reserva-{uuid.uuid4().hex[:8]}", "changeType": "cancelled",
            "type": cancelada["type"], "status": "cancelled", "source": "provider",
            "committedAt": iso(INICIO), "createdDate": "2026-10-01", "provider": cancelada["provider"],
            "startDate": cancelada["startDate"], "startsAt": cancelada["startsAt"],
            "locationCity": cancelada["location"], "arrivalCity": cancelada.get("arrivalLocation")}


@pytest.fixture
def proceso(tmp_path):
    reloj = RelojFijo(INICIO)
    apis = {"aerolinea-sur": BusquedaAerolineaSimulada("aerolinea-sur", 40, reloj),
            "aerolinea-norte": BusquedaAerolineaSimulada("aerolinea-norte", 40, reloj)}
    recomendacion = Recomendacion(REGION, SQLite(str(tmp_path / "recomendacion.db")), BrokerEnMemoria(),
                                  adaptadores_para(apis), "clave", reloj=reloj,
                                  logger=Logger("recomendacion", REGION, salida=None), semilla=3)
    recomendacion.preparar_mensajeria()
    recomendacion.apis = apis
    return recomendacion


def recibir(proceso, hecho: dict):
    validar_evento("booking.facts.v1", {k: v for k, v in hecho.items() if v is not None})
    proceso.hechos.procesar(Mensaje(EXCHANGE_DOMINIO, RK_HECHOS, {k: v for k, v in hecho.items() if v is not None}, {}))


def busquedas(proceso) -> list[dict]:
    with proceso.base.transaccion() as tx:
        return tx.todos("SELECT * FROM busquedas")


def test_disrupcion_masiva_respeta_los_limites_de_los_proveedores(proceso):
    """QA-12 (a escala 1/10): 50 vuelos cancelados con 30 viajeros cada uno. Las búsquedas iguales se agrupan, la
    cubeta por proveedor nunca excede su límite y el 95 % tiene sugerencias generadas dentro de los 2 minutos desde la
    cancelación (con reloj simulado: no mide tiempos reales de proveedores)."""
    azar = random.Random(11)
    vuelos = []
    while len(vuelos) < 50:
        vuelo = vuelo_cancelado(azar)
        if all((vuelo["startDate"], vuelo["location"], vuelo["arrivalLocation"]) !=
               (v["startDate"], v["location"], v["arrivalLocation"]) for v in vuelos):
            vuelos.append(vuelo)
    for n, vuelo in enumerate(vuelos):
        for k in range(30):
            recibir(proceso, hecho_cancelacion(f"viajero-{n}-{k}", vuelo))
    while any(b["estado"] == "pendiente" for b in busquedas(proceso)):
        proceso.ciclo()
        proceso.reloj.adelantar(seconds=10)
        assert proceso.reloj.ahora() - INICIO < timedelta(minutes=10)
    for api in proceso.apis.values():
        assert api.cuota_excedida == 0              # 100 % de los límites respetados
        assert api.consultas == 50                  # una consulta por clave y proveedor (búsquedas agrupadas)
    # Desde la cancelación confirmada en el núcleo hasta las sugerencias generadas; el tramo outbox → notificador →
    # push no está en este proceso aislado (se mide en la prueba de punta a punta).
    demoras = sorted((iso_a(b["terminada"]) - iso_a(b["cancelacion_confirmada"])).total_seconds()
                     for b in busquedas(proceso))
    assert len(demoras) == 1500 and demoras[int(len(demoras) * 0.95) - 1] <= 120


def iso_a(texto: str):
    from comun.infraestructura.reloj import parsear

    return parsear(texto)


def test_proveedores_caidos_la_busqueda_espera_y_se_completa(proceso):
    """QA-17: sin respuesta de ningún proveedor la búsqueda queda pendiente y se completa al recuperarse."""
    vuelo = vuelo_cancelado(random.Random(1))
    for api in proceso.apis.values():
        for _ in range(4):
            api.fallar_proxima(ErrorTemporal("caído"))
    recibir(proceso, hecho_cancelacion("viajero-1", vuelo))
    proceso.ciclo()
    assert busquedas(proceso)[0]["estado"] == "pendiente"
    recuperado = None
    for _ in range(60):
        proceso.reloj.adelantar(seconds=10)
        proceso.ciclo()
        if recuperado is None and not any(api.fallas for api in proceso.apis.values()):
            recuperado = proceso.reloj.ahora()
        if busquedas(proceso)[0]["estado"] == "lista":
            break
    assert busquedas(proceso)[0]["estado"] == "lista"
    assert proceso.reloj.ahora() - recuperado <= timedelta(minutes=10)


def test_un_proveedor_caido_da_resultado_parcial(proceso):
    vuelo = vuelo_cancelado(random.Random(2))
    proceso.apis["aerolinea-norte"].fallar_proxima(ErrorTemporal("caído"))
    recibir(proceso, hecho_cancelacion("viajero-1", vuelo))
    proceso.ciclo()
    lista = proceso.sugerencias.listar("viajero-1", f"{REGION}:viaje-viajero-1")
    validar_api("SuggestionList", lista)
    assert lista["searchStatus"] == "partial"
    assert {s["provider"] for s in lista["suggestions"]} == {"aerolinea-sur"}


def test_canario_que_baja_la_aceptacion_se_retira(proceso):
    """QA-15: una versión nueva entra como canario; si su aceptación cae más de un 10 % relativo, vuelve atrás sola,
    sin desplegar código (es un cambio de datos en el registro)."""
    registro = proceso.registro
    registro.muestra_minima = 20
    inicial = registro.activa()["version_id"]
    canario = registro.publicar_canario([0.0, 2.0, 1.0, 1.0, 1.0, -1.0, -1.0, -1.0], 100, {"prueba": True})
    with proceso.base.transaccion() as tx:
        for version, aceptadas in ((inicial, 10), (canario, 3)):
            for i in range(20):
                tx.ejecutar("INSERT INTO sugerencias (suggestion_id, busqueda_id, user_id, trip_id, "
                            "cancelled_booking_id, posicion, oferta, caracteristicas, version_modelo, exploracion, "
                            "motivos, estado, mostrada, creada) VALUES (?, 'b', 'u', 't', 'c', 1, '{}', '[]', ?, 0, "
                            "'[]', ?, 1, ?)", (f"{version}-{i}", version, "accepted" if i < aceptadas else "rejected",
                                               iso(INICIO)))
    assert registro.evaluar_canario() == "retirado"
    assert registro.activa()["version_id"] == inicial and registro.canario() is None


def test_version_para_cada_viajero_y_vuelta_atras_manual(proceso):
    from recomendacion.modelo.registro import en_canario

    registro = proceso.registro
    canario = registro.publicar_canario(caracteristicas.PESOS_INICIALES, 0, {})
    usuarios = [f"u-{i}" for i in range(2000)]
    en = [u for u in usuarios if en_canario(u)]
    assert 0.03 < len(en) / len(usuarios) < 0.07                        # alrededor del 5 %
    assert registro.version_para(en[0])["version_id"] == canario
    assert registro.version_para(next(u for u in usuarios if not en_canario(u)))["version_id"] == "v0-inicial"
    assert registro.volver_atras() == canario and registro.canario() is None


def test_el_modelo_aprende_del_feedback_de_viajeros_sinteticos(proceso):
    """ADR-0083: tras una ronda de feedback y el entrenamiento diario, el orden aprendido pone en primer lugar
    ofertas más útiles para los viajeros que el orden por precio, y los pesos se mueven hacia sus preferencias
    ocultas."""
    proceso.registro.muestra_minima = 10
    for api in proceso.apis.values():
        api.limite_por_minuto = 10_000
    for adaptador in proceso.buscador.adaptadores:
        adaptador.limite_por_minuto = 10_000
    azar = random.Random(5)
    viajeros = generar_viajeros(80, semilla=9)

    def ronda(cantidad: int):
        for i in range(cantidad):
            viajero = viajeros[i % len(viajeros)]
            vuelo = vuelo_cancelado(azar)
            trip_id = f"{REGION}:viaje-{uuid.uuid4().hex[:6]}"
            recibir(proceso, hecho_cancelacion(viajero.user_id, vuelo, trip_id))
            proceso.ciclo()
            lista = proceso.sugerencias.listar(viajero.user_id, trip_id)
            with proceso.base.transaccion() as tx:
                candidatas = [json.loads(f["oferta"]) for f in tx.todos(
                    "SELECT oferta FROM sugerencias WHERE trip_id = ?", (trip_id,))]
            mostradas = disponibles(lista)
            for posicion, accion in viajero.decidir(mostradas, vuelo, candidatas, azar):
                proceso.sugerencias.feedback(viajero.user_id, mostradas[posicion]["id"], accion)
                if accion == "reject":
                    break  # el viajero mira la lista reordenada en la próxima cancelación

    ronda(400)
    resultado = proceso.entrenar()
    assert resultado["entrenamiento"]["resultado"] == "canario"
    aprendidos = proceso.registro.canario()["pesos"]

    def utilidad_media(orden) -> float:
        prueba, valores = random.Random(99), []
        for _ in range(300):
            viajero, vuelo = prueba.choice(viajeros), vuelo_cancelado(prueba)
            ofertas = [o for a in proceso.buscador.adaptadores
                       for o in a.buscar(_consulta(vuelo))]
            mediana = statistics.median(o["price"]["amount"] for o in ofertas)
            primera = orden(ofertas, vuelo)
            sin_ruido = random.Random(0)
            viajero_sin_ruido = type(viajero)(viajero.user_id, viajero.pesos, viajero.sesgo, 0.0)
            valores.append(viajero_sin_ruido.utilidad(primera, vuelo, mediana, sin_ruido))
        return statistics.mean(valores)

    def por_pesos(pesos):
        def orden(ofertas, vuelo):
            ctx = caracteristicas.contexto(ofertas)
            perfil = {"metricas": {"proveedores": {}}, "preferencias": {}}
            candidatas = [(o, caracteristicas.vector(o, vuelo, perfil, ctx)) for o in ofertas]
            return ranking.ordenar(candidatas, pesos)[0][0]
        return orden

    # 1) Con el feedback reservado (1 de cada 5), la versión nueva predice mejor que la activa.
    evaluacion = resultado["entrenamiento"]
    assert evaluacion["perdida_nueva"] < evaluacion["perdida_activa"]
    # 2) Los pesos de lo que los viajeros valoran se alejan de los iniciales en la dirección de sus preferencias ocultas
    #    (MEDIA en datos_sinteticos.py: escalas -1,2, horario -2,5, mismo proveedor 0,8): cada uno pasa un umbral que
    #    los pesos iniciales (-0,3, -0,5 y 0,3) no alcanzan.
    escalas, desvio, proveedor = aprendidos[3], aprendidos[4], aprendidos[5]
    assert escalas < -0.6 and desvio < -1.0 and proveedor > 0.6
    # 3) La primera sugerencia del orden aprendido es más útil que la más barata.
    assert utilidad_media(por_pesos(aprendidos)) > utilidad_media(
        lambda ofertas, vuelo: min(ofertas, key=lambda o: o["price"]["amount"]))


def _consulta(vuelo: dict):
    from recomendacion.busqueda.adaptadores import Consulta

    return Consulta("flight", vuelo["location"], vuelo["startDate"], arrivalLocation=vuelo["arrivalLocation"])


def test_enlace_de_oferta_no_permitido_se_descarta():
    """B5 de la auditoría: solo https y dominios permitidos del proveedor (offer-search.md)."""
    from recomendacion.busqueda.adaptadores import enlace_permitido

    dominios = ("hotel-sol.example",)
    assert enlace_permitido("https://hotel-sol.example/ofertas/1", dominios)
    assert enlace_permitido("https://reservas.hotel-sol.example/x", dominios)
    assert not enlace_permitido("http://hotel-sol.example/ofertas/1", dominios)
    assert not enlace_permitido("https://hotel-sol.example.atacante.com/x", dominios)
    assert not enlace_permitido("javascript:alert(1)", dominios)

