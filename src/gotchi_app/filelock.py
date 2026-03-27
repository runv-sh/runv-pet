from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, TextIO


class LockError(RuntimeError):
    pass


def _lock_file(handle: TextIO) -> None:
    if os.name == "nt":  # pragma: no cover - exercised in local Windows usage
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file(handle: TextIO) -> None:
    if os.name == "nt":  # pragma: no cover - exercised in local Windows usage
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def file_lock(path: Path, timeout: float = 5.0, poll_interval: float = 0.05) -> Iterator[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    with path.open("a+", encoding="utf-8") as handle:
        while True:
            try:
                _lock_file(handle)
                handle.seek(0)
                handle.truncate()
                handle.write(str(os.getpid()))
                handle.flush()
                os.fsync(handle.fileno())
                try:
                    yield path
                finally:
                    _unlock_file(handle)
                return
            except OSError as exc:
                last_error = exc
                if time.monotonic() >= deadline:
                    break
                time.sleep(poll_interval)

    raise LockError(f"Nao foi possivel adquirir lock em {path}: {last_error}")
