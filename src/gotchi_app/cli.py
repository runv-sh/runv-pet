from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from .config import load_tuning, write_default_config
from .runv_mode import inspect_server_pet
from .simulator import SPECIES, apply_time, create_pet, interact
from .storage import StorageError, current_username, load_pet, require_pet, save_pet
from .ui import help_text, runv_status_screen, status_screen


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(prog="gotchi", add_help=False)
    command_parser.add_argument("command", nargs="?", default="dashboard")
    command_parser.add_argument("argument", nargs="?")
    command_parser.add_argument("--species", choices=SPECIES, default=SPECIES[0])
    command_parser.add_argument("--name")
    command_parser.add_argument("--write-config", action="store_true")
    return command_parser


def load_and_tick() -> tuple:
    tuning = load_tuning()
    pet = require_pet()
    pet = apply_time(pet, utcnow(), tuning)
    save_pet(pet)
    return pet, tuning


def cmd_init(args: argparse.Namespace) -> int:
    existing = load_pet()
    if existing and existing.alive:
        print("Voce ja tem um pet. Use `gotchi status` para encontra-lo.")
        return 1

    if args.write_config:
        path = write_default_config()
        print(f"Config padrao criada em {path}")

    name = args.name or current_username().split()[0].capitalize()
    pet = create_pet(current_username(), name, args.species, utcnow())
    save_pet(pet)
    print(status_screen(pet, utcnow()))
    return 0


def cmd_status() -> int:
    pet, _ = load_and_tick()
    print(status_screen(pet, utcnow()))
    return 0


def cmd_action(action: str) -> int:
    pet, tuning = load_and_tick()
    updated = interact(pet, action, utcnow(), tuning)
    save_pet(updated)
    print(status_screen(updated, utcnow()))
    return 0


def cmd_rename(new_name: str | None) -> int:
    if not new_name:
        print("Uso: gotchi rename NOVO_NOME")
        return 1
    pet, _ = load_and_tick()
    if not pet.alive:
        print("Nao da para renomear um pet morto.")
        return 1
    pet = pet.evolve(name=new_name, last_message=f"Agora atende por {new_name}.")
    save_pet(pet)
    print(status_screen(pet, utcnow()))
    return 0


def cmd_runv() -> int:
    print(runv_status_screen(inspect_server_pet()))
    return 0


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] == "-runv":
        return cmd_runv()

    args = parser().parse_args(raw_argv)
    command = args.command

    try:
        if command in ("help", "--help", "-h"):
            print(help_text())
            return 0
        if command == "init":
            return cmd_init(args)
        if command in ("dashboard", "status"):
            return cmd_status()
        if command in {"feed", "play", "sleep", "clean", "doctor"}:
            return cmd_action(command)
        if command == "rename":
            return cmd_rename(args.argument)
        print(help_text())
        return 1
    except StorageError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompido.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
