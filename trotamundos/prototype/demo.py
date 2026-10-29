"""Demo por terminal: recorre la API del prototipo con dos regiones en un solo proceso.

    python demo.py            (desde trotamundos/prototype)
    python demo.py --logs     (además muestra los logs JSON de cada proceso)

Usa la entrada global como lo haría la app y simula lo que el prototipo no implementa (vinculación de cuentas y
proveedores externos). No necesita Docker: las bases son SQLite en un directorio temporal y el broker es en memoria.
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile

from starlette.testclient import TestClient

from comun.infraestructura.http import DestinoASGI
from comun.observabilidad import metricas, trace_id
from contratos.esquemas import validar_api
from sistema import Sistema

CORREO = """Hotel: Gran Vía Centro
Localizador: GV-1
Estado: Confirmada
Entrada: 2026-12-10 15:00
Salida: 2026-12-14 11:00
Ciudad: Madrid
Zona: Europe/Madrid"""


def paso(numero: int, titulo: str):
    print(f"\n{numero}. {titulo}")


def ver(etiqueta: str, valor):
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)
    print(f"   {etiqueta}: {texto[:160]}{'…' if len(texto) > 160 else ''}")


class Usuario:
    def __init__(self, http: TestClient, email: str, pais: str):
        self.http, self.email = http, email
        self.region = http.post("/login/region", json={"email": email, "country": pais}).json()["region"]
        http.post(f"/id/{self.region}/accounts", json={"email": email, "password": "clave-segura", "country": pais})
        tokens = http.post(f"/id/{self.region}/token", json={"email": email, "password": "clave-segura"}).json()
        self.user_id, self.token = tokens["userId"], tokens["access_token"]

    def pedir(self, metodo: str, ruta: str, cuerpo=None, **encabezados):
        return self.http.request(metodo, ruta, json=cuerpo,
                                 headers={"Authorization": f"Bearer {self.token}", **encabezados})


def main(con_logs: bool):
    directorio = tempfile.mkdtemp(prefix="trotamundos-demo-")
    sistema = Sistema(directorio, salida_logs=sys.stdout if con_logs else None)
    http = TestClient(sistema.entrada.app)
    sa = sistema.regiones["sa-east"]

    paso(1, "Registro e inicio de sesión: la entrada global elige la región (ADR-0003, ADR-0060)")
    juan = Usuario(http, "juan@example.com", "AR")
    ana = Usuario(http, "ana@example.com", "ES")
    ver("Juan", f"región {juan.region}, usuario {juan.user_id}")
    ver("Ana", f"región {ana.region}, usuario {ana.user_id}")

    paso(2, "Juan carga una reserva manual: viaje por fechas, panel versión 1 y outbox (ADR-0040, ADR-0048)")
    reserva = juan.pedir("POST", "/bookings", {"type": "flight", "startsAt": "2026-12-09T22:00:00-03:00",
                                               "endsAt": "2026-12-10T14:00:00+01:00", "location": "EZE",
                                               "arrivalLocation": "MAD", "notes": "llevar adaptador",
                                               "details": {"schema": "flight.v1", "flightNumber": "AR1132"}},
                         **{"Idempotency-Key": "demo-1"}).json()
    panel = juan.pedir("GET", "/panel")
    validar_api("Panel", panel.json())
    ver("viaje", f"{panel.json()['trips'][0]['name']} ({panel.json()['trips'][0]['startDate']} → "
                 f"{panel.json()['trips'][0]['endDate']})")
    ver("ETag", panel.headers["etag"])
    ver("GET /panel con If-None-Match", juan.pedir("GET", "/panel", **{"If-None-Match": panel.headers["etag"]})
        .status_code)

    paso(3, "Ingesta: un correo de confirmación y la API de un hotel llegan al panel (iteración 2)")
    for connection_id, proveedor in (("con-correo", "correo-demo"), ("con-hotel", "hotel-sol")):
        sa.nucleo.registrar_vinculacion(connection_id, juan.user_id, proveedor)
        sa.ingesta.vinculaciones.registrar(connection_id, juan.user_id, "sa-east", proveedor,
                                           "email" if proveedor == "correo-demo" else "provider",
                                           remitentes=["reservas@hotel-granvia.example"])
    sa.fuentes["buzon"].recibir("con-correo", "reservas@hotel-granvia.example", CORREO)
    sa.fuentes["hotel"].publicar("con-hotel", {"reservationId": "HS-77", "version": 1, "status": "CONFIRMED",
                                               "checkIn": "2026-12-12", "checkOut": "2026-12-14", "city": "Toledo",
                                               "timeZone": "Europe/Madrid"})
    sistema.procesar()
    viaje = juan.pedir("GET", "/panel").json()["trips"][0]
    for r in viaje["bookings"]:
        ver(f"{r['type']:>6}", f"{r['startsAt']} {r.get('location', '')} origen={r['origin']} estado={r['status']}")
    novedad = next(m for m in sa.broker.publicados if m.exchange == "travel.ingestion")
    aviso = next(m for m in sa.broker.publicados if novedad.cuerpo["correlationId"] in m.cuerpo.get("correlationIds", []))
    ver("misma traza de punta a punta", trace_id(novedad.encabezados["traceparent"]) ==
        trace_id(aviso.encabezados["traceparent"]))

    paso(4, "Aviso en vivo por SSE: ready y después panel-changed (ADR-0046)")
    ticket = juan.pedir("POST", "/panel/events/ticket").json()["ticket"]

    async def escuchar():
        flujo = await DestinoASGI(sistema.entrada.app).abrir_flujo("GET", f"/panel/events?ticket={ticket}", {})
        partes = flujo.partes.__aiter__()
        ver("evento", (await partes.__anext__()).decode().strip().replace("\n", " "))
        sa.fuentes["hotel"].publicar("con-hotel", {"reservationId": "HS-77", "version": 2, "status": "CONFIRMED",
                                                   "checkIn": "2026-12-11", "checkOut": "2026-12-14",
                                                   "city": "Toledo", "timeZone": "Europe/Madrid"})
        sa.ingesta.agendar("con-hotel", "aviso")
        sistema.procesar()
        ver("evento", (await asyncio.wait_for(partes.__anext__(), 2)).decode().strip().replace("\n", " "))
        await flujo.cerrar()

    asyncio.run(escuchar())
    ver("push enviados (solo avisos importantes)", [p["reason"] for p in sa.notificador.push.enviados])

    paso(5, "Compartición entre regiones con auditoría (iteración 4, ADR-0061, ADR-0062)")
    viaje_id = reserva["tripId"]
    invitacion = juan.pedir("POST", f"/trips/{viaje_id}/shares", {"email": ana.email},
                            **{"Idempotency-Key": "demo-2"}).json()
    correo = sa.nucleo.correo.ultimo_para(ana.email)
    ver("invitación", f"{invitacion['id']} → correo simulado a {correo['to']}")
    aceptada = ana.pedir("POST", f"/shares/{invitacion['id']}/accept", {"secret": correo["secret"]}).json()
    ana.pedir("POST", "/shared/trips", aceptada)
    compartido = ana.pedir("GET", f"/shared/trips/{viaje_id}")
    ver("Ana lee el viaje", f"{compartido.status_code}, Cache-Control: {compartido.headers['cache-control']}")
    ver("campos de una reserva compartida", sorted(compartido.json()["bookings"][0]))
    ver("Ana usa el endpoint del dueño", ana.pedir("GET", f"/trips/{viaje_id}").status_code)
    ver("sin token", http.get(f"/shared/trips/{viaje_id}").status_code)
    sistema.regiones["eu-west"].puerta.otras_regiones["sa-east"].disponible = False
    ver("región del dueño caída", ana.pedir("GET", f"/shared/trips/{viaje_id}").status_code)
    sistema.regiones["eu-west"].puerta.otras_regiones["sa-east"].disponible = True
    for region in ("sa-east", "eu-west"):
        for r in sistema.regiones[region].nucleo.auditoria.consultar():
            ver(f"auditoría {region}", f"{r['action']} {r['result']} {r['reason'] or '-'} "
                                       f"actor={r['actor_region'] or '-'} entrada={r['entry_region']}")

    paso(6, "Métricas del proceso (ADR-0067)")
    for nombre, valor in sorted(metricas.resumen()["contadores"].items()):
        if nombre.startswith(("ingesta_publicados", "novedades_", "push_", "puerta_")):
            ver(nombre, valor)
    for nombre, valores in metricas.resumen()["duraciones"].items():
        ver(nombre, valores)
    print(f"\nDatos de la demo en {directorio}")


if __name__ == "__main__":
    main("--logs" in sys.argv)
