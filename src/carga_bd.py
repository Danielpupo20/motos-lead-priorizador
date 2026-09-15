"""
Persiste leads, extracciones y scores en la base de datos SQLite (db/schema.sql).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "priorizador.db"


def persistir(leads_limpios, extracciones, scores, crudos):
    raise NotImplementedError("Pendiente: escritura a SQLite")
