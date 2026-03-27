from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


APP_DIR_NAME = "runv-pet"
CONFIG_FALLBACK_DIR_NAME = "runv-pet-config"
DATA_FALLBACK_DIR_NAME = "runv-pet-data"
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


def xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _writable_candidates(base: Path, preferred_name: str, fallback_name: str) -> list[Path]:
    return [
        base / preferred_name,
        base / fallback_name,
        Path.home() / f".{preferred_name}",
    ]


def _materialize_first_writable(candidates: list[Path]) -> Path:
    errors = []
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError as exc:
            errors.append(f"{candidate}: {exc}")
    joined = "; ".join(errors)
    raise OSError(f"Nao foi possivel preparar diretorio da aplicacao: {joined}")


def _config_candidates() -> list[Path]:
    return [
        xdg_config_home() / APP_DIR_NAME / CONFIG_FILE_NAME,
        xdg_config_home() / CONFIG_FALLBACK_DIR_NAME / CONFIG_FILE_NAME,
        xdg_data_home() / APP_DIR_NAME / CONFIG_FILE_NAME,
        Path.home() / f".{APP_DIR_NAME}" / CONFIG_FILE_NAME,
    ]


def data_dir() -> Path:
    return _materialize_first_writable(
        _writable_candidates(xdg_data_home(), APP_DIR_NAME, DATA_FALLBACK_DIR_NAME)
    )


def config_dir() -> Path:
    return config_path().parent


def config_path() -> Path:
    for candidate in _config_candidates():
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
        except OSError:
            continue
    return _config_candidates()[0]


def ensure_directories() -> None:
    data_dir()


def load_tuning() -> Tuning:
    path = config_path()
    try:
        if not path.exists():
            return Tuning()
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except OSError:
        return Tuning()
    values = asdict(Tuning())
    values.update({key: raw[key] for key in raw if key in values})
    return Tuning(**values)


def write_default_config(path: Path | None = None) -> Path:
    if path is not None:
        target = path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(Tuning().to_json() + "\n", encoding="utf-8")
        return target

    errors = []
    for target in _config_candidates():
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(Tuning().to_json() + "\n", encoding="utf-8")
            return target
        except OSError as exc:
            errors.append(f"{target}: {exc}")
    joined = "; ".join(errors)
    raise OSError(f"Nao foi possivel gravar configuracao padrao: {joined}")
