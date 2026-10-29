"""Compartición de viajes con personas designadas con cuenta (ADR-0061) y control de acceso a viajes ajenos.

* Solo una cuenta cuyo email verificado coincide con el invitado puede aceptar: se compara `emailHmac` (HMAC con la
  clave común de ADR-0060), sin mover emails entre regiones.
* El permiso es del principal `(homeRegion, userId)` que aceptó, de solo lectura, y se verifica en cada lectura.
* Todo pedido sobre un viaje ajeno pasa por este módulo y se audita antes de responder; si la auditoría no se puede
  escribir, se rechaza con 503 (AuditoriaNoDisponible).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta

from comun.infraestructura.reloj import Reloj, iso, parsear
from nucleo.auditoria.registro import Actor, RegistroAuditoria
from nucleo.datos.ruteo import IdentificadorInvalido, RuteoParticiones
from nucleo.reservas.manuales import ErrorDominio
from nucleo.reservas.modelo import viaje_compartido

VIGENCIA_INVITACION = timedelta(days=7)  # suposición (ADR-0061)


@dataclass
class Principal:
    region: str
    user_id: str
    issuer: str | None
    email_hmac: str | None
    entry_region: str

    @property
    def actor(self) -> Actor:
        return Actor(self.user_id, self.region, self.issuer)


def email_hmac(clave: bytes, email: str) -> str:
    return hmac.new(clave, email.strip().lower().encode(), hashlib.sha256).hexdigest()


def _hash_secreto(secreto: str) -> str:
    return hashlib.sha256(secreto.encode()).hexdigest()


class Comparticion:
    def __init__(self, region: str, ruteo: RuteoParticiones, auditoria: RegistroAuditoria, reloj: Reloj,
                 clave_email: bytes, correo):
        self.region = region
        self.ruteo = ruteo
        self.auditoria = auditoria
        self.reloj = reloj
        self.clave_email = clave_email
        self.correo = correo  # puerto de envío de correo (simulado en el prototipo)

    # ---------------------------------------------------------------- control de viajes ajenos

    def _nodo(self, identificador: str):
        try:
            return self.ruteo.nodo_de_id(identificador)
        except IdentificadorInvalido:
            return None

    def es_dueno(self, principal: Principal, viaje: dict | None) -> bool:
        return viaje is not None and principal.region == self.region and viaje["user_id"] == principal.user_id

    def rechazar_ajeno(self, principal: Principal, metodo: str, ruta: str, trip_id=None, booking_id=None,
                       existe: bool = True):
        """Pedido sobre un viaje o reserva ajenos por un endpoint del dueño: se audita y se responde 404."""
        self.auditoria.registrar("share.read", "denied", principal.actor, metodo, ruta, principal.entry_region,
                                 motivo="owner_endpoint" if existe else "not_found", trip_id=trip_id,
                                 booking_id=booking_id)
        raise ErrorDominio(404, "not_found", "No existe o no pertenece al usuario")

    def viaje_del_dueno(self, principal: Principal, trip_id: str, metodo: str, ruta: str) -> dict:
        nodo = self._nodo(trip_id)
        viaje = None
        if nodo is not None:
            with nodo.transaccion() as tx:
                viaje = tx.uno("SELECT * FROM viajes WHERE trip_id = ?", (trip_id,))
        if not self.es_dueno(principal, viaje):
            self.rechazar_ajeno(principal, metodo, ruta, trip_id=trip_id, existe=viaje is not None)
        return viaje

    # ---------------------------------------------------------------- invitaciones

    def invitar(self, principal: Principal, trip_id: str, email: str, metodo: str, ruta: str) -> dict:
        viaje = self.viaje_del_dueno(principal, trip_id, metodo, ruta)
        share_id = self.ruteo.nuevo_id_con_region(viaje["user_id"])
        secreto = secrets.token_urlsafe(24)
        ahora = self.reloj.ahora()
        with self.ruteo.nodo_de_id(trip_id).transaccion() as tx:
            tx.ejecutar("INSERT INTO comparticiones (share_id, trip_id, owner_user_id, email, email_hmac, "
                        "secreto_hash, estado, creado, vence) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
                        (share_id, trip_id, viaje["user_id"], email, email_hmac(self.clave_email, email),
                         _hash_secreto(secreto), iso(ahora), iso(ahora + VIGENCIA_INVITACION)))
            fila = tx.uno("SELECT * FROM comparticiones WHERE share_id = ?", (share_id,))
            # Se audita antes de confirmar: si la auditoría falla, la invitación no se crea y el cliente reintenta.
            self.auditoria.registrar("share.invite", "allowed", principal.actor, metodo, ruta,
                                     principal.entry_region, trip_id=trip_id, share_id=share_id)
        self.correo.enviar(email, "invitacion", {"shareId": share_id, "secret": secreto, "tripId": trip_id})
        return self._share_a_api(fila)

    def listar(self, principal: Principal, trip_id: str, metodo: str, ruta: str) -> list[dict]:
        self.viaje_del_dueno(principal, trip_id, metodo, ruta)
        with self.ruteo.nodo_de_id(trip_id).transaccion() as tx:
            filas = tx.todos("SELECT * FROM comparticiones WHERE trip_id = ? AND estado != 'removed' "
                             "ORDER BY creado", (trip_id,))
        return [self._share_a_api(f) for f in filas]

    def quitar(self, principal: Principal, trip_id: str, share_id: str, metodo: str, ruta: str):
        self.viaje_del_dueno(principal, trip_id, metodo, ruta)
        with self.ruteo.nodo_de_id(trip_id).transaccion() as tx:
            fila = tx.uno("SELECT * FROM comparticiones WHERE share_id = ? AND trip_id = ? AND estado != 'removed'",
                          (share_id, trip_id))
            if fila is None:
                raise ErrorDominio(404, "not_found", "La invitación no existe")
            # Se audita antes de confirmar: si la auditoría falla, el permiso no se quita y el cliente reintenta.
            self.auditoria.registrar("share.remove", "allowed", principal.actor, metodo, ruta,
                                     principal.entry_region, trip_id=trip_id, share_id=share_id)
            tx.ejecutar("UPDATE comparticiones SET estado = 'removed', email = NULL WHERE share_id = ?", (share_id,))

    def aceptar(self, principal: Principal, share_id: str, secreto: str, metodo: str, ruta: str) -> dict:
        nodo = self._nodo(share_id)
        fila = None
        if nodo is not None:
            with nodo.transaccion() as tx:
                fila = tx.uno("SELECT * FROM comparticiones WHERE share_id = ?", (share_id,))
        motivo = self._motivo_rechazo_aceptacion(principal, fila, secreto)
        trip_id = fila["trip_id"] if fila else None
        if motivo:
            self.auditoria.registrar("share.accept", "denied", principal.actor, metodo, ruta, principal.entry_region,
                                     motivo=motivo, trip_id=trip_id, share_id=share_id)
            raise ErrorDominio(404, "not_found", "La invitación no existe o no se puede aceptar con esta cuenta")
        aceptada_en = fila["aceptada_en"] or iso(self.reloj.ahora())
        self.auditoria.registrar("share.accept", "allowed", principal.actor, metodo, ruta, principal.entry_region,
                                 trip_id=trip_id, share_id=share_id)
        if fila["estado"] == "pending":
            with nodo.transaccion() as tx:
                tx.ejecutar("UPDATE comparticiones SET estado = 'accepted', aceptada_region = ?, aceptada_usuario = ?, "
                            "aceptada_en = ? WHERE share_id = ? AND estado = 'pending'",
                            (principal.region, principal.user_id, aceptada_en, share_id))
        return {"tripId": trip_id, "acceptedAt": aceptada_en}

    def _motivo_rechazo_aceptacion(self, principal: Principal, fila: dict | None, secreto: str) -> str | None:
        if fila is None:
            return "not_found"
        if fila["estado"] == "removed":
            return "removed"
        if not hmac.compare_digest(fila["secreto_hash"], _hash_secreto(secreto or "")):
            return "secret_mismatch"
        if not principal.email_hmac or not hmac.compare_digest(fila["email_hmac"], principal.email_hmac):
            return "email_mismatch"
        if fila["estado"] == "accepted":
            mismo = (fila["aceptada_region"], fila["aceptada_usuario"]) == (principal.region, principal.user_id)
            return None if mismo else "no_permission"  # aceptar dos veces con la misma cuenta no tiene efecto
        if parsear(fila["vence"]) < self.reloj.ahora():
            return "expired"
        return None

    # ---------------------------------------------------------------- lectura compartida

    def leer(self, principal: Principal, trip_id: str, metodo: str, ruta: str) -> dict:
        nodo = self._nodo(trip_id)
        viaje, reservas, permiso, quitado = None, [], None, False
        if nodo is not None:
            with nodo.transaccion() as tx:
                viaje = tx.uno("SELECT * FROM viajes WHERE trip_id = ?", (trip_id,))
                if viaje:
                    permiso = tx.uno("SELECT * FROM comparticiones WHERE trip_id = ? AND estado = 'accepted' "
                                     "AND aceptada_region = ? AND aceptada_usuario = ?",
                                     (trip_id, principal.region, principal.user_id))
                    quitado = permiso is None and tx.uno(
                        "SELECT 1 AS x FROM comparticiones WHERE trip_id = ? AND estado = 'removed' "
                        "AND aceptada_region = ? AND aceptada_usuario = ?",
                        (trip_id, principal.region, principal.user_id)) is not None
                    reservas = tx.todos("SELECT * FROM reservas WHERE trip_id = ? ORDER BY inicio", (trip_id,))
        if viaje is None or permiso is None:
            motivo = "not_found" if viaje is None else "removed" if quitado else "no_permission"
            self.auditoria.registrar("share.read", "denied", principal.actor, metodo, ruta, principal.entry_region,
                                     motivo=motivo, trip_id=trip_id)
            raise ErrorDominio(404, "not_found", "No existe o no pertenece al usuario")
        self.auditoria.registrar("share.read", "allowed", principal.actor, metodo, ruta, principal.entry_region,
                                 trip_id=trip_id)
        return viaje_compartido(viaje, reservas)

    def _share_a_api(self, fila: dict) -> dict:
        estado = self.estado_visible(fila)
        datos = {"id": fila["share_id"], "tripId": fila["trip_id"], "status": estado, "createdAt": fila["creado"]}
        if fila.get("email"):
            datos["email"] = fila["email"]
        if fila.get("aceptada_en"):
            datos["acceptedAt"] = fila["aceptada_en"]
        return datos

    def estado_visible(self, fila: dict) -> str:
        if fila["estado"] == "pending" and parsear(fila["vence"]) < self.reloj.ahora():
            return "expired"
        return fila["estado"]
