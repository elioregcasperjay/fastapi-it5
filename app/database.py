import sqlite3
from contextlib import contextmanager
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    isbn TEXT NOT NULL UNIQUE,
    total_copies INTEGER NOT NULL CHECK (total_copies >= 0),
    available_copies INTEGER NOT NULL CHECK (available_copies >= 0),
    CHECK (available_copies <= total_copies)
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL REFERENCES students (student_id) ON DELETE RESTRICT,
    book_id INTEGER NOT NULL REFERENCES books (id) ON DELETE RESTRICT,
    borrowed_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    returned_date TEXT,
    fine INTEGER NOT NULL DEFAULT 0 CHECK (fine >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_one_active_loan_per_book
    ON loans (student_id, book_id) WHERE returned_date IS NULL;
"""


class Database:
    """Owns the SQLite file path, the schema, and per-request connections."""

    def __init__(self, path: str = "library.db") -> None:
        self._path = path

    def configure(self, path: str) -> None:
        self._path = path

    def create_schema(self) -> None:
        with self.connection() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


database = Database()
database_connection = database.connection