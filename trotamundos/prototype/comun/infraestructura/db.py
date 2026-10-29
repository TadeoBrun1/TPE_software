"""Puerto de base de datos con dos adaptadores: SQLite (local y pruebas) y PostgreSQL (docker compose).

Biblioteca técnica, sin lógica de dominio. Las consultas se escriben con `?` y el adaptador de PostgreSQL las
traduce. `bloqueo_fila` agrega `FOR UPDATE` en PostgreSQL (bloqueo por usuario de ADR-0040); en SQLite cada
transacción de escritura toma el bloqueo de la base con `BEGIN IMMEDIATE`, que también serializa los cambios.
La espera máxima por un bloqueo es de 2 s, como pide ADR-0040.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Callable, Iterator

ESPERA_BLOQUEO_S = 2.0


class ErrorBloqueo(Exception):
    """No se obtuvo el bloqueo en el tiempo máximo."""


class Transaccion:
    def __init__(self, cursor, dialecto: str):
        self._cursor = cursor
        self.dialecto = dialecto

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.dialecto == "postgres" else sql

    def ejecutar(self, sql: str, parametros: tuple | list = ()) -> int:
        self._cursor.execute(self._sql(sql), tuple(parametros))
        return self._cursor.rowcount

    def uno(self, sql: str, parametros: tuple | list = ()) -> dict | None:
        self._cursor.execute(self._sql(sql), tuple(parametros))
        fila = self._cursor.fetchone()
        return dict(fila) if fila is not None else None

    def todos(self, sql: str, parametros: tuple | list = ()) -> list[dict]:
        self._cursor.execute(self._sql(sql), tuple(parametros))
        return [dict(f) for f in self._cursor.fetchall()]

    def bloqueo_fila(self, sql: str, parametros: tuple | list = ()) -> dict | None:
        """SELECT que bloquea las filas leídas hasta el fin de la transacción."""
        if self.dialecto == "postgres":
            sql = sql + " FOR UPDATE"
        return self.uno(sql, parametros)


class BaseDatos:
    dialecto = "abstracta"
    nombre = ""

    @contextmanager
    def transaccion(self) -> Iterator[Transaccion]:  # pragma: no cover - interfaz
        raise NotImplementedError
        yield

    def crear_esquema(self, ddl: list[str]):
        with self.transaccion() as tx:
            for sentencia in ddl:
                tx.ejecutar(sentencia)


class SQLite(BaseDatos):
    dialecto = "sqlite"

    def __init__(self, ruta: str, nombre: str = ""):
        self.ruta = ruta
        self.nombre = nombre or ruta
        self.disponible = True  # permite simular la caída de un nodo o del registro de auditoría
        self._lock_mem = threading.Lock()
        if ruta == ":memory:":  # una conexión compartida para bases en memoria
            self._mem = sqlite3.connect(ruta, check_same_thread=False, isolation_level=None)
            self._mem.row_factory = sqlite3.Row
        else:
            self._mem = None

    @contextmanager
    def transaccion(self) -> Iterator[Transaccion]:
        if not self.disponible:
            raise ConnectionError(f"base {self.nombre} no disponible")
        if self._mem is not None:
            with self._lock_mem:
                yield from self._transaccion(self._mem)
            return
        conexion = sqlite3.connect(self.ruta, timeout=ESPERA_BLOQUEO_S, isolation_level=None)
        conexion.row_factory = sqlite3.Row
        try:
            yield from self._transaccion(conexion)
        finally:
            conexion.close()

    def _transaccion(self, conexion):
        cursor = conexion.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as error:
            raise ErrorBloqueo(str(error)) from error
        try:
            yield Transaccion(cursor, self.dialecto)
        except BaseException:
            conexion.rollback()
            raise
        else:
            try:
                conexion.commit()
            except sqlite3.OperationalError as error:
                conexion.rollback()
                raise ErrorBloqueo(str(error)) from error


class Postgres(BaseDatos):  # pragma: no cover - se usa con docker compose, no en las pruebas locales
    dialecto = "postgres"

    def __init__(self, dsn: str, nombre: str = ""):
        import psycopg  # noqa: F401 - dependencia solo del despliegue con docker compose

        self.dsn = dsn
        self.nombre = nombre or dsn.rsplit("/", 1)[-1]
        self.disponible = True

    @contextmanager
    def transaccion(self) -> Iterator[Transaccion]:
        import psycopg
        from psycopg.rows import dict_row

        if not self.disponible:
            raise ConnectionError(f"base {self.nombre} no disponible")
        try:
            conexion = psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=5)
        except psycopg.OperationalError as error:  # nodo caído: mismo trato que en SQLite (503 en la API)
            raise ConnectionError(f"base {self.nombre} no disponible: {error}") from error
        with conexion:
            try:
                with conexion.transaction():
                    with conexion.cursor() as cursor:
                        cursor.execute(f"SET LOCAL lock_timeout = '{int(ESPERA_BLOQUEO_S * 1000)}ms'")
                        yield Transaccion(cursor, self.dialecto)
            except psycopg.errors.LockNotAvailable as error:
                raise ErrorBloqueo(str(error)) from error


def abrir(url: str, nombre: str = "") -> BaseDatos:
    """`sqlite:///ruta.db`, `sqlite:///:memory:` o `postgresql://...`."""
    if url.startswith("sqlite:///"):
        return SQLite(url[len("sqlite:///"):], nombre)
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return Postgres(url, nombre)
    raise ValueError(f"URL de base no soportada: {url}")


def con_reintentos(funcion: Callable[[], Any], intentos: int = 3) -> Any:
    """Reintenta ante un bloqueo que no se obtuvo en 2 s (hasta 3 veces, ADR-0040)."""
    ultimo: Exception | None = None
    for _ in range(intentos):
        try:
            return funcion()
        except ErrorBloqueo as error:
            ultimo = error
    raise ultimo  # type: ignore[misc]
