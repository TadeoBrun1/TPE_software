"""Iteración 5: eliminación de la cuenta (ADR-0085, `account-deleted.v1.yaml`, DELETE /account).

El núcleo borra en el momento lo suyo y publica `account.deleted.v1`; identidad, directorio global, ingesta,
notificador y recomendación borran lo suyo al recibirlo. Las pruebas recorren todas las bases de la región y buscan
el identificador del usuario: no tiene que quedar en ninguna, salvo en la marca de cuenta eliminada.
"""
from __future__ import annotations

import asyncio
import json

from comun.infraestructura.broker import Mensaje
from comun.infraestructura.http import DestinoASGI
from contratos.esquemas import validar_evento
from contratos.topologia import EXCHANGE_DOMINIO, EXCHANGE_INGESTA, RK_CUENTA, RK_HECHOS
from test_iteracion5_recomendacion import cancelar_hotel, disponibles, sugerencias

MARCAS = {"cuentas_eliminadas"}


def compartir(sistema, dueno, invitado, clave: str) -> str:
    """El dueño comparte un viaje con el invitado y este acepta (ADR-0061)."""
    viaje = dueno.reserva(f"viaje-{clave}", location="Roma", startsAt="2026-12-20T10:00:00+01:00",
                          endsAt="2026-12-22T10:00:00+01:00")["tripId"]
    invitacion = dueno.post(f"/trips/{viaje}/shares", {"email": invitado.email},
                            headers={"Idempotency-Key": f"inv-{clave}"}).json()
    correo = sistema.regiones[dueno.region].nucleo.correo.ultimo_para(invitado.email)
    aceptada = invitado.post(f"/shares/{invitacion['id']}/accept", {"secret": correo["secret"]})
    assert aceptada.status_code == 200, aceptada.text
    assert invitado.post("/shared/trips", aceptada.json()).status_code == 200
    return viaje


def bases_de_la_region(region) -> dict:
    return {**{f"nodo{i}": n for i, n in enumerate(region.nucleo.ruteo.nodos)},
            "auditoria": region.auditoria, "ingesta": region.ingesta.registro.base,
            "identidad": region.identidad.base, "recomendacion": region.recomendacion.base,
            "push": region.notificador.push.base}


def restos(region, user_id: str) -> list[tuple[str, str]]:
    """(base, tabla) donde todavía aparece el identificador del usuario, fuera de las marcas de cuenta eliminada.

    Antes, como pasaría con la tarea diaria a las 24 h, se vacía el contenido de los eventos ya enviados de la outbox
    del núcleo: el propio `account.deleted.v1` lleva el identificador hasta entonces."""
    region.nucleo.reloj.adelantar(hours=25)
    region.nucleo.publicador.limpiar_enviados()
    encontrados = []
    for nombre, base in bases_de_la_region(region).items():
        with base.transaccion() as tx:
            tablas = [f["name"] for f in tx.todos("SELECT name FROM sqlite_master WHERE type = 'table'")]
            for tabla in tablas:
                if tabla in MARCAS:
                    continue
                if any(user_id in json.dumps(fila, default=str) for fila in tx.todos(f"SELECT * FROM {tabla}")):
                    encontrados.append((nombre, tabla))
    return encontrados


def test_eliminar_la_cuenta_borra_al_usuario_de_toda_la_region(juan, cliente, sistema):
    region, cancelada = cancelar_hotel(sistema, juan)            # vinculación, reservas, sugerencias y push
    primera = disponibles(sugerencias(juan, cancelada["tripId"]))[0]
    juan.post(f"/suggestions/{primera['id']}/feedback", {"action": "reject"})
    pedro = cliente.registrar("pedro@example.com", "AR")
    compartir(sistema, juan, pedro, "a")                        # juan es dueño de un viaje compartido
    viaje_de_pedro = compartir(sistema, pedro, juan, "b")       # juan tiene permiso sobre un viaje de pedro
    juan.get(f"/shared/trips/{viaje_de_pedro}")                 # deja un registro de auditoría con juan de actor
    juan.post("/telemetry/panel-shown", {"panelVersion": 1, "shownAt": "2026-11-01T12:00:00Z"})
    sistema.procesar()
    assert len(restos(region, juan.user_id)) > 5                # antes, el usuario está en varias bases

    juan.ingresar()                                             # inicio de sesión reciente
    respuesta = juan.delete("/account")
    assert respuesta.status_code == 204
    assert juan.get("/panel").json()["code"] == "account_deleted"   # token todavía vigente: 401
    sistema.procesar()

    # El token sigue vigente también para la recomendación: no vuelve a crear el perfil.
    preferencias = juan.get("/recommendations/preferences")
    assert preferencias.status_code == 401 and preferencias.json()["code"] == "account_deleted"
    assert restos(region, juan.user_id) == []
    evento = next(m for m in region.broker.publicados if m.routing_key == RK_CUENTA)
    validar_evento("account.deleted.v1", evento.cuerpo)
    # Login y directorio: la cuenta no existe más; la región se elige como para un email desconocido.
    assert cliente.http.post("/id/sa-east/token", json={"email": juan.email, "password": "clave-segura"}) \
        .status_code == 401
    with sistema.entrada_base.transaccion() as tx:
        assert tx.uno("SELECT COUNT(*) AS n FROM directorio")["n"] == 1   # solo queda pedro
    # Pedro ya no ve a juan entre las personas con acceso a su viaje.
    pedro.ingresar()
    assert pedro.get(f"/trips/{viaje_de_pedro}/shares").json()["shares"] == []
    # La auditoría conserva el registro con un seudónimo del actor.
    registros = region.nucleo.auditoria.consultar(trip_id=viaje_de_pedro, action="share.read")
    assert registros and all(r["actor_user_id"].startswith("eliminada:") for r in registros)


def test_exige_un_inicio_de_sesion_reciente(juan, sistema, reloj):
    reloj.adelantar(minutes=6)
    juan.renovar()  # el token renovado conserva el momento del login original
    respuesta = juan.delete("/account")
    assert respuesta.status_code == 401 and respuesta.json()["code"] == "reauthentication_required"
    juan.ingresar()
    assert juan.delete("/account").status_code == 204
    assert juan.delete("/account").status_code == 401  # ya eliminada


def test_mensajes_atrasados_y_reentregas(juan, sistema):
    """Una novedad o un hecho atrasados de la cuenta eliminada se descartan; el evento reentregado no falla."""
    region, cancelada = cancelar_hotel(sistema, juan)
    novedad = next(m for m in region.broker.publicados if m.exchange == EXCHANGE_INGESTA)
    hecho = next(m for m in region.broker.publicados if m.routing_key == RK_HECHOS)
    juan.ingresar()
    assert juan.delete("/account").status_code == 204
    sistema.procesar()
    atrasada = {**novedad.cuerpo, "eventId": "atrasada-1"}
    region.nucleo.consumidor.procesar(Mensaje(EXCHANGE_INGESTA, novedad.routing_key, atrasada, {}))
    region.recomendacion.hechos.procesar(Mensaje(EXCHANGE_DOMINIO, RK_HECHOS,
                                                 {**hecho.cuerpo, "eventId": "atrasado-1"}, {}))
    evento = next(m for m in region.broker.publicados if m.routing_key == RK_CUENTA)
    from nucleo.usuarios import eliminacion

    for consumidor in (lambda m: eliminacion.completar(region.nucleo, m), region.identidad.procesar_baja,
                       region.ingesta.bajas.procesar,
                       region.recomendacion.hechos.procesar, region.notificador.push.procesar):
        consumidor(Mensaje(EXCHANGE_DOMINIO, RK_CUENTA, evento.cuerpo, {}, True))
    assert restos(region, juan.user_id) == []


def test_la_marca_de_cuenta_eliminada_vence(juan, sistema, reloj):
    region = sistema.regiones["sa-east"]
    juan.ingresar()
    juan.delete("/account")
    sistema.procesar()
    reloj.adelantar(days=31)
    assert region.nucleo.tarea_diaria()["marcas_de_cuenta_purgadas"] == 1
    region.recomendacion.entrenar()
    for base in (region.nucleo.ruteo.nodos + [region.recomendacion.base]):
        with base.transaccion() as tx:
            assert tx.uno("SELECT COUNT(*) AS n FROM cuentas_eliminadas")["n"] == 0


def test_la_conexion_sse_se_cierra(juan, sistema):
    region = sistema.regiones["sa-east"]
    ticket = juan.post("/panel/events/ticket").json()["ticket"]
    juan.ingresar()

    async def escenario():
        flujo = await DestinoASGI(sistema.entrada.app).abrir_flujo("GET", f"/panel/events?ticket={ticket}", {})
        partes = flujo.partes.__aiter__()
        assert (await partes.__anext__()).startswith(b"event: ready")
        borrado = await DestinoASGI(region.puerta.app).enviar("DELETE", "/account", juan.h, b"")
        assert borrado.estado == 204
        await asyncio.to_thread(sistema.procesar)
        recibidos = [parte async for parte in partes]  # el flujo termina solo
        await flujo.cerrar()
        return recibidos

    recibidos = asyncio.run(asyncio.wait_for(escenario(), timeout=5))
    assert recibidos[-1].startswith(b"event: account-deleted")


def test_el_barrido_quita_lo_que_un_hecho_en_paralelo_dejo(juan, sistema):
    """Varias instancias consumen la cola sin orden por usuario: si un hecho se procesó en paralelo con la baja y dejó
    filas, el barrido periódico de la recomendación las quita (ADR-0085)."""
    region = sistema.regiones["sa-east"]
    juan.ingresar()
    juan.delete("/account")
    sistema.procesar()
    with region.recomendacion.base.transaccion() as tx:  # lo que habría dejado el hecho procesado en paralelo
        tx.ejecutar("INSERT INTO perfiles (user_id, home_region, activada, preferencias, metricas, ajuste, "
                    "actualizado) "
                    "VALUES (?, 'sa-east', 1, '{}', '{}', '[]', '2026-11-01')", (juan.user_id,))
    region.recomendacion.ciclo()
    with region.recomendacion.base.transaccion() as tx:
        assert tx.uno("SELECT COUNT(*) AS n FROM perfiles WHERE user_id = ?", (juan.user_id,))["n"] == 0

