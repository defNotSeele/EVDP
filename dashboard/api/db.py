"""Read-only access to the telemetry database, shared by the whole app."""

import sqlite3
import threading


class Database:
    """One read-only SQLite connection per server thread.

    SQLite connections can't be shared between threads, and waitress serves
    requests on several, so each thread lazily opens its own and reuses it.
    `mode=ro` means the dashboard can never write to or lock the ingesters' DB.
    """

    _instance = None

    def __new__(cls, path=None):
        if cls._instance is None:
            if path is None:
                raise RuntimeError("Database() needs a path the first time it is created")
            cls._instance = super().__new__(cls)
            cls._instance._path = path
            cls._instance._local = threading.local()
        return cls._instance

    def _connection(self):
        con = getattr(self._local, "con", None)
        if con is None:
            con = sqlite3.connect(f"file:{self._path}?mode=ro", uri=True, timeout=10)
            con.row_factory = sqlite3.Row
            self._local.con = con
        return con

    def query(self, sql, params=()):
        return self._connection().execute(sql, params).fetchall()
