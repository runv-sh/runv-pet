from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Optional

from .config import PathInfo, legacy_db_candidates, permissions_report, resolve_paths
from .filelock import LockError, file_lock
from .identity import UserIdentity, resolve_identity
from .models import Pet


SCHEMA_VERSION = 2
SQLITE_TIMEOUT_SECONDS = 5.0


class StorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class MigrationReport:
    migrated: bool
    source_path: Path | None
    backup_path: Path | None
    message: str


@dataclass(frozen=True)
class StorageDoctorReport:
    ok: bool
    save_path: Path
    lock_path: Path
    checks: list[str]


def db_path(identity: UserIdentity | None = None) -> Path:
    return resolve_paths(identity).save_path


def current_identity() -> UserIdentity:
    return resolve_identity()


def current_username() -> str:
    return current_identity().username


def _connect(target: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(target, timeout=SQLITE_TIMEOUT_SECONDS, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version >= SCHEMA_VERSION:
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pet (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            owner_uid INTEGER NOT NULL,
            username TEXT NOT NULL,
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


@contextmanager
def locked_connection(identity: UserIdentity | None = None, timeout: float = SQLITE_TIMEOUT_SECONDS) -> Iterator[tuple[sqlite3.Connection, PathInfo]]:
    user = identity or resolve_identity()
    paths = resolve_paths(user)
    try:
        with file_lock(paths.lock_path, timeout=timeout):
            conn = _connect(paths.save_path)
            try:
                conn.execute("BEGIN IMMEDIATE")
                migrate(conn)
                yield conn, paths
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    except LockError as exc:
        raise StorageError(str(exc)) from exc
    except sqlite3.Error as exc:
        raise StorageError(f"Nao foi possivel abrir o banco de dados do gotchi: {exc}") from exc


def _row_to_pet(row: sqlite3.Row) -> Pet:
    return Pet.from_record(dict(row))


def _fetch_pet(conn: sqlite3.Connection) -> Optional[Pet]:
    row = conn.execute("SELECT * FROM pet WHERE id = 1").fetchone()
    return None if row is None else _row_to_pet(row)


def _save_pet(conn: sqlite3.Connection, pet: Pet) -> None:
    values = pet.to_record()
    values["id"] = 1
    columns = ", ".join(values.keys())
    placeholders = ", ".join(f":{key}" for key in values)
    updates = ", ".join(f"{key}=excluded.{key}" for key in values if key != "id")
    conn.execute(
        f"""
        INSERT INTO pet ({columns})
        VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET
        {updates}
        """,
        values,
    )


def _read_legacy_pet(path: Path, username: str) -> Pet | None:
    if not path.exists():
        return None
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM pets WHERE username = ?", (username,)).fetchone()
        if row is None:
            return None
        return Pet.from_record(dict(row))
    except sqlite3.Error:
        return None
    finally:
        if conn is not None:
            conn.close()


def _write_migration_marker(paths: PathInfo, report: MigrationReport) -> None:
    payload = {
        "migrated": report.migrated,
        "source_path": str(report.source_path) if report.source_path else None,
        "backup_path": str(report.backup_path) if report.backup_path else None,
        "message": report.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    paths.migration_marker.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        paths.migration_marker.chmod(0o600)
    except OSError:
        pass


def migrate_legacy_save(identity: UserIdentity | None = None) -> MigrationReport:
    user = identity or resolve_identity()
    with locked_connection(user) as (conn, paths):
        current = _fetch_pet(conn)
        if current is not None:
            report = MigrationReport(False, None, None, "Save atual ja existe; migracao legada nao foi necessaria.")
            _write_migration_marker(paths, report)
            return report

        for legacy_path in legacy_db_candidates(user):
            legacy_pet = _read_legacy_pet(legacy_path, user.username)
            if legacy_pet is None:
                continue

            migrated = legacy_pet.evolve(owner_uid=user.uid, username=user.username)
            backup_path = paths.backup_dir / f"legacy-{user.uid}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
            backup_path.write_text(json.dumps(migrated.to_record(), indent=2) + "\n", encoding="utf-8")
            try:
                backup_path.chmod(0o600)
            except OSError:
                pass
            _save_pet(conn, migrated)
            report = MigrationReport(True, legacy_path, backup_path, f"Migracao concluida a partir de {legacy_path}.")
            conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("legacy_source", str(legacy_path)),
            )
            _write_migration_marker(paths, report)
            return report

        report = MigrationReport(False, None, None, "Nenhum save legado elegivel foi encontrado.")
        _write_migration_marker(paths, report)
        return report


def load_pet(identity: UserIdentity | None = None, path: Path | None = None) -> Optional[Pet]:
    if path is not None:
        conn = _connect(path)
        try:
            migrate(conn)
            return _fetch_pet(conn)
        finally:
            conn.close()

    user = identity or resolve_identity()
    with locked_connection(user) as (conn, _paths):
        pet = _fetch_pet(conn)
        if pet is not None:
            return pet
    migrate_legacy_save(user)
    with locked_connection(user) as (conn, _paths):
        return _fetch_pet(conn)


def save_pet(pet: Pet, identity: UserIdentity | None = None, path: Path | None = None) -> None:
    if path is not None:
        conn = _connect(path)
        try:
            migrate(conn)
            _save_pet(conn, pet)
            conn.commit()
            return
        finally:
            conn.close()

    user = identity or resolve_identity()
    with locked_connection(user) as (conn, _paths):
        if pet.owner_uid != user.uid:
            raise StorageError("O save nao pertence ao UID atual.")
        _save_pet(conn, pet)


def require_pet(identity: UserIdentity | None = None, path: Path | None = None) -> Pet:
    pet = load_pet(identity=identity, path=path)
    if pet is None:
        raise StorageError("Nenhum pet encontrado. Rode `gotchi init` primeiro.")
    return pet


def update_pet(identity: UserIdentity, mutate: Callable[[Pet | None], Pet | None]) -> Pet | None:
    with locked_connection(identity) as (conn, _paths):
        pet = _fetch_pet(conn)
        updated = mutate(pet)
        if updated is None:
            return None
        if updated.owner_uid != identity.uid:
            raise StorageError("Tentativa de salvar pet com UID divergente.")
        _save_pet(conn, updated)
        return updated


def export_pet(identity: UserIdentity | None = None) -> dict:
    user = identity or resolve_identity()
    pet = require_pet(user)
    return {
        "format": 1,
        "owner_uid": user.uid,
        "username": user.username,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "pet": pet.to_record(),
    }


def import_pet(payload: dict, identity: UserIdentity | None = None) -> Pet:
    user = identity or resolve_identity()
    pet_payload = payload.get("pet")
    if not isinstance(pet_payload, dict):
        raise StorageError("Arquivo de import invalido: campo `pet` ausente.")
    owner_uid = payload.get("owner_uid", pet_payload.get("owner_uid", user.uid))
    if int(owner_uid) != user.uid:
        raise StorageError("O backup pertence a outro UID e nao pode ser importado aqui.")
    pet_payload["owner_uid"] = user.uid
    pet_payload["username"] = user.username
    pet = Pet.from_record(pet_payload)
    save_pet(pet, identity=user)
    return pet


def path_report(identity: UserIdentity | None = None) -> dict[str, str]:
    paths = resolve_paths(identity)
    report = {
        "uid": str(paths.identity.uid),
        "username": paths.identity.username,
        "home": str(paths.identity.home),
        "state_dir": str(paths.state_dir),
        "config_dir": str(paths.config_dir),
        "data_dir": str(paths.data_dir),
        "save_path": str(paths.save_path),
        "lock_path": str(paths.lock_path),
        "config_path": str(paths.config_path),
    }
    if paths.global_config_path is not None:
        report["global_config_path"] = str(paths.global_config_path)
    return report


def doctor_storage(identity: UserIdentity | None = None) -> StorageDoctorReport:
    user = identity or resolve_identity()
    paths = resolve_paths(user)
    checks: list[str] = []
    checks.append(f"uid={user.uid} username={user.username}")
    checks.append(f"state_dir={paths.state_dir}")
    checks.append(f"save_path={paths.save_path}")
    checks.append(f"permissions={permissions_report(paths)}")
    with locked_connection(user) as (conn, _locked_paths):
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        checks.append(f"integrity={result}")
        checks.append("save=ok" if _fetch_pet(conn) is not None else "save=ausente")
    legacy_found = [str(path) for path in legacy_db_candidates(user) if path.exists()]
    if legacy_found:
        checks.append(f"legacy_candidates={legacy_found}")
    return StorageDoctorReport(
        ok=all("not ok" not in item for item in checks) and any("integrity=ok" in item for item in checks),
        save_path=paths.save_path,
        lock_path=paths.lock_path,
        checks=checks,
    )
