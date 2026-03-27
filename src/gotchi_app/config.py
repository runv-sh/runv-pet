from __future__ import annotations

import json
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path

from .identity import UserIdentity, resolve_identity


APP_DIR_NAME = "gotchi"
LEGACY_APP_DIR_NAMES = ("runv-pet", "runv-pet-data")
CONFIG_FILE_NAME = "gotchi.json"


@dataclass(frozen=True)
class Tuning:
    hunger_per_hour: float = 6.0
    energy_loss_per_hour: float = 4.5
    hygiene_loss_per_hour: float = 3.0
    sleep_energy_gain_per_hour: float = 11.0
    sleep_hunger_per_hour: float = 4.0
    mood_recovery_per_hour: float = 1.5
    mood_penalty_per_hour: float = 2.0
    health_penalty_per_hour: float = 3.0
    health_recovery_per_hour: float = 0.8
    illness_threshold: float = 35.0
    death_threshold_hours: float = 36.0
    max_stat: float = 100.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


@dataclass(frozen=True)
class PathInfo:
    identity: UserIdentity
    state_dir: Path
    config_dir: Path
    data_dir: Path
    save_path: Path
    lock_path: Path
    export_dir: Path
    backup_dir: Path
    migration_marker: Path
    config_path: Path
    global_config_path: Path | None


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else None


def _materialize_private_dir(candidates: list[Path]) -> Path:
    errors = []
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(candidate, 0o700)
            except OSError:
                pass
            return candidate
        except OSError as exc:
            errors.append(f"{candidate}: {exc}")
    joined = "; ".join(errors)
    raise OSError(f"Nao foi possivel preparar diretorio privado: {joined}")


def _private_dir_candidates(identity: UserIdentity, env_name: str, home_parts: tuple[str, ...], cwd_name: str) -> list[Path]:
    uid_leaf = f"uid-{identity.uid}"
    candidates: list[Path] = []
    env_base = _env_path(env_name)
    if env_base is not None:
        candidates.append(env_base / APP_DIR_NAME / uid_leaf)
    candidates.append(identity.home.joinpath(*home_parts) / APP_DIR_NAME / uid_leaf)
    candidates.append(Path.cwd() / cwd_name / uid_leaf)
    return candidates


def _first_global_config() -> Path | None:
    candidates = [
        Path("/etc/xdg/gotchi") / CONFIG_FILE_NAME,
        Path("/etc/gotchi") / CONFIG_FILE_NAME,
    ]
    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def resolve_paths(identity: UserIdentity | None = None) -> PathInfo:
    user = identity or resolve_identity()
    state_dir = _materialize_private_dir(_private_dir_candidates(user, "XDG_STATE_HOME", (".local", "state"), ".gotchi-state"))
    config_dir = _materialize_private_dir(_private_dir_candidates(user, "XDG_CONFIG_HOME", (".config",), ".gotchi-config"))
    data_dir = _materialize_private_dir(_private_dir_candidates(user, "XDG_DATA_HOME", (".local", "share"), ".gotchi-data"))
    export_dir = _materialize_private_dir([data_dir / "exports"])
    backup_dir = _materialize_private_dir([state_dir / "legacy-backups"])
    save_path = state_dir / "pet.db"
    lock_path = state_dir / "pet.lock"
    migration_marker = state_dir / "migration.json"
    config_path = config_dir / CONFIG_FILE_NAME
    return PathInfo(
        identity=user,
        state_dir=state_dir,
        config_dir=config_dir,
        data_dir=data_dir,
        save_path=save_path,
        lock_path=lock_path,
        export_dir=export_dir,
        backup_dir=backup_dir,
        migration_marker=migration_marker,
        config_path=config_path,
        global_config_path=_first_global_config(),
    )


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _merge_tuning(*configs: dict) -> Tuning:
    values = asdict(Tuning())
    for config in configs:
        values.update({key: config[key] for key in config if key in values})
    return Tuning(**values)


def load_tuning(identity: UserIdentity | None = None) -> Tuning:
    paths = resolve_paths(identity)
    global_config = {}
    user_config = {}
    if paths.global_config_path is not None:
        try:
            global_config = _load_json(paths.global_config_path)
        except OSError:
            global_config = {}
    try:
        if paths.config_path.exists():
            user_config = _load_json(paths.config_path)
    except OSError:
        user_config = {}
    return _merge_tuning(global_config, user_config)


def write_default_config(identity: UserIdentity | None = None, path: Path | None = None) -> Path:
    if path is not None:
        target = path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(Tuning().to_json() + "\n", encoding="utf-8")
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
        return target

    paths = resolve_paths(identity)
    if not paths.config_path.exists():
        paths.config_path.write_text(Tuning().to_json() + "\n", encoding="utf-8")
    try:
        os.chmod(paths.config_path, 0o600)
    except OSError:
        pass
    return paths.config_path


def permissions_report(paths: PathInfo) -> dict[str, str]:
    report: dict[str, str] = {}
    for label, target in (("state_dir", paths.state_dir), ("config_dir", paths.config_dir), ("data_dir", paths.data_dir)):
        try:
            report[label] = oct(_mode(target))
        except OSError:
            report[label] = "unavailable"
    if paths.save_path.exists():
        try:
            report["save_path"] = oct(_mode(paths.save_path))
        except OSError:
            report["save_path"] = "unavailable"
    return report


def legacy_db_candidates(identity: UserIdentity | None = None) -> list[Path]:
    user = identity or resolve_identity()
    env_data = _env_path("XDG_DATA_HOME") or user.home.joinpath(".local", "share")
    candidates = [env_data / name / "gotchi.db" for name in LEGACY_APP_DIR_NAMES]
    candidates.append(user.home / ".gotchi-data" / "gotchi.db")
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique
