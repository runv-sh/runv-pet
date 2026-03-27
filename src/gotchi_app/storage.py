from __future__ import annotations

import getpass
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from .config import data_dir, ensure_directories
from .models import Pet


SCHEMA_VERSION = 1


class StorageError(RuntimeError):
    pass


def _db_candidates(path: Path | None = None) -> list[Path]:
    if path is not None:
        return [path]
    ensure_directories()
    return [
        data_dir() / "gotchi.db",
        Path.cwd() / ".gotchi-data" / "gotchi.db",
    ]


def db_path() -> Path:
    return _db_candidates()[0]


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    errors = []
    for target in _db_candidates(path):
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(target)
            conn.row_factory = sqlite3.Row
            try:
                migrate(conn)
                yield conn
                conn.commit()
                return
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        except sqlite3.Error as exc:
            errors.append(f"{target}: {exc}")
            continue
    joined = "; ".join(errors) if errors else "sem candidatos"
    raise StorageError(f"Nao foi possivel abrir o banco de dados do gotchi: {joined}")


def migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version >= SCHEMA_VERSION:
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pets (
            username TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            species TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_interaction_at TEXT NOT NULL,
            last_update_at TEXT NOT NULL,
            age_hours REAL NOT NULL,
            hunger REAL NOT NULL,
            energy REAL NOT NULL,
            mood REAL NOT NULL,
            hygiene REAL NOT NULL,
            health REAL NOT NULL,
            is_sleeping INTEGER NOT NULL,
            sleeping_since TEXT,
            illness INTEGER NOT NULL,
            alive INTEGER NOT NULL,
            cause_of_death TEXT,
            last_message TEXT NOT NULL
        )
        """
    )
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def current_username() -> str:
    return getpass.getuser()


def load_pet(username: str | None = None, path: Path | None = None) -> Optional[Pet]:
    user = username or current_username()
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM pets WHERE username = ?", (user,)).fetchone()
    if row is None:
        return None
    return Pet.from_record(dict(row))


def save_pet(pet: Pet, path: Path | None = None) -> None:
    values = pet.to_record()
    columns = ", ".join(values.keys())
    placeholders = ", ".join(f":{key}" for key in values.keys())
    updates = ", ".join(f"{key}=excluded.{key}" for key in values.keys() if key != "username")
    with connect(path) as conn:
        conn.execute(
            f"""
            INSERT INTO pets ({columns})
            VALUES ({placeholders})
            ON CONFLICT(username) DO UPDATE SET
            {updates}
            """,
            values,
        )


def require_pet(username: str | None = None, path: Path | None = None) -> Pet:
    pet = load_pet(username=username, path=path)
    if pet is None:
        raise StorageError("Nenhum pet encontrado. Rode `gotchi init` primeiro.")
    return pet
