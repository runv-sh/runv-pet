from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
from pathlib import Path

from .config import data_dir


@dataclass(frozen=True)
class ServerPetStatus:
    status: str
    perch: str
    message: str
    load_state: str
    disk_state: str
    write_state: str


def _score_state(state: str) -> int:
    return {"excelente": 0, "bem": 1, "atencao": 2, "critico": 3}[state]


def _state_from_ratio(ratio: float, warn: float, critical: float) -> str:
    if ratio >= critical:
        return "critico"
    if ratio >= warn:
        return "atencao"
    if ratio >= warn * 0.7:
        return "bem"
    return "excelente"


def _load_state() -> str:
    try:
        load = os.getloadavg()[0]
        cpus = max(os.cpu_count() or 1, 1)
        ratio = load / cpus
        return _state_from_ratio(ratio, 0.7, 1.0)
    except (AttributeError, OSError):
        return "bem"


def _disk_state() -> str:
    target = data_dir()
    usage = shutil.disk_usage(target)
    ratio = usage.used / max(usage.total, 1)
    return _state_from_ratio(ratio, 0.85, 0.93)


def _write_state() -> str:
    try:
        target = data_dir()
        probe = target / ".runv-touch"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return "excelente"
    except OSError:
        return "critico"


def inspect_server_pet() -> ServerPetStatus:
    load_state = _load_state()
    disk_state = _disk_state()
    write_state = _write_state()
    status = max((load_state, disk_state, write_state), key=_score_state)

    if status == "excelente":
        message = "O corvo do Runv esta alerta, penas alinhadas e poleiro firme."
        perch = "ninho estavel"
    elif status == "bem":
        message = "O corvo vigia tudo com calma, mas o ninho pede observacao."
        perch = "vento leve"
    elif status == "atencao":
        message = "O corvo esta inquieto. O ninho segue de pe, mas ha tensao no ar."
        perch = "galho tenso"
    else:
        message = "O corvo do Runv esta eriçado. Melhor tratar o ninho com cuidado."
        perch = "tempestade"

    return ServerPetStatus(
        status=status,
        perch=perch,
        message=message,
        load_state=load_state,
        disk_state=disk_state,
        write_state=write_state,
    )
