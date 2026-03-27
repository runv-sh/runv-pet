from __future__ import annotations

import os
import sys
import textwrap
from datetime import datetime, timezone

from .models import Pet
from .runv_mode import ServerPetStatus
from .simulator import general_status, normalize_species
from .storage import MigrationReport, StorageDoctorReport


PET_ART = {
    "cat": {
        "happy": r"""
 /\_/\\
( o.o )
 > ^ <
""".strip("\n"),
        "sleep": r"""
 /\_/\\
( -.- ) z
 > ^ <
""".strip("\n"),
        "tired": r"""
 /\_/\\
( -.- )
 > ^ <
""".strip("\n"),
        "sick": r"""
 /\_/\\
( x.x )
 > ^ <
""".strip("\n"),
        "dead": r"""
 /\_/\\
( _._ )
 > ^ <
""".strip("\n"),
    },
    "dog": {
        "happy": r"""
 / \__
(    @\___
 /         O
/   (_____/
/_____/   U
""".strip("\n"),
        "sleep": r"""
 / \__
(    -\___ z
 /         O
/   (_____/
/_____/   U
""".strip("\n"),
        "tired": r"""
 / \__
(    -\___
 /         O
/   (_____/
/_____/   U
""".strip("\n"),
        "sick": r"""
 / \__
(    x\___
 /         O
/   (_____/
/_____/   U
""".strip("\n"),
        "dead": r"""
 / \__
(    _\___
 /         O
/   (_____/
/_____/   U
""".strip("\n"),
    },
    "fox": {
        "happy": r"""
 /\   /\\
((ovo ))
():::()
  V V
""".strip("\n"),
        "sleep": r"""
 /\   /\\
((uvu )) z
():::()
  V V
""".strip("\n"),
        "tired": r"""
 /\   /\\
((-v- ))
():::()
  V V
""".strip("\n"),
        "sick": r"""
 /\   /\\
((xvx ))
():::()
  V V
""".strip("\n"),
        "dead": r"""
 /\   /\\
((___ ))
():::()
  V V
""".strip("\n"),
    },
    "rabbit": {
        "happy": r"""
 (\_/)
 (o.o)
 /|_|\\
""".strip("\n"),
        "sleep": r"""
 (\_/)
 (-.-) z
 /|_|\\
""".strip("\n"),
        "tired": r"""
 (\_/)
 (-.-)
 /|_|\\
""".strip("\n"),
        "sick": r"""
 (\_/)
 (x.x)
 /|_|\\
""".strip("\n"),
        "dead": r"""
 (\_/)
 (_._)
 /|_|\\
""".strip("\n"),
    },
    "turtle": {
        "happy": r"""
  _____
 / . .\\
|  ---  |_
 \_____/
""".strip("\n"),
        "sleep": r"""
  _____
 / - -\\ z
|  ---  |_
 \_____/
""".strip("\n"),
        "tired": r"""
  _____
 / - -\\
|  ---  |_
 \_____/
""".strip("\n"),
        "sick": r"""
  _____
 / x x\\
|  ---  |_
 \_____/
""".strip("\n"),
        "dead": r"""
  _____
 / _ _\\
|  ---  |_
 \_____/
""".strip("\n"),
    },
    "bat": {
        "happy": r"""
 /\                 /\\
/ \'._   (\_/)   _.'/ \\
|.''._'--(o.o)--'_.''.|
 \\_ / `;=/ \=;` \ _//
   `\__| \___/ |__/`
""".strip("\n"),
        "sleep": r"""
 /\                 /\\
/ \'._   (\_/)   _.'/ \\
|.''._'--(-.-)--'_.''.|
 \\_ / `;=/ \=;` \ _//
   `\__| \___/ |__/` z
""".strip("\n"),
        "tired": r"""
 /\                 /\\
/ \'._   (\_/)   _.'/ \\
|.''._'--(-.-)--'_.''.|
 \\_ / `;=/ \=;` \ _//
   `\__| \___/ |__/`
""".strip("\n"),
        "sick": r"""
 /\                 /\\
/ \'._   (\_/)   _.'/ \\
|.''._'--(x.x)--'_.''.|
 \\_ / `;=/ \=;` \ _//
   `\__| \___/ |__/`
""".strip("\n"),
        "dead": r"""
 /\                 /\\
/ \'._   (\_/)   _.'/ \\
|.''._'--(_._)--'_.''.|
 \\_ / `;=/ \=;` \ _//
   `\__| \___/ |__/`
""".strip("\n"),
    },
    "crow": {
        "happy": r"""
   \
   (o>
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "sleep": r"""
   \
   (u>   z
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "tired": r"""
   \
   (-<
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "sick": r"""
   \
   (x<
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "dead": r"""
   \
   (_x)
\\_//)
 \_/_
  _|_
""".strip("\n"),
    },
    "raven": {
        "happy": r"""
   \
   (O>
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "sleep": r"""
   \
   (U>   z
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "tired": r"""
   \
   (-<
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "sick": r"""
   \
   (x<
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "dead": r"""
   \
   (_x)
\\_//)
 \_/_
  _|_
""".strip("\n"),
    },
    "owl": {
        "happy": r"""
  ,_,
 (O,O)
 (   )
  " "
""".strip("\n"),
        "sleep": r"""
  ,_,
 (-,-) z
 (   )
  " "
""".strip("\n"),
        "tired": r"""
  ,_,
 (-,-)
 (   )
  " "
""".strip("\n"),
        "sick": r"""
  ,_,
 (x,x)
 (   )
  " "
""".strip("\n"),
        "dead": r"""
  ,_,
 (_,_)
 (   )
  " "
""".strip("\n"),
    },
    "blob": {
        "happy": r"""
  .-.
 (o o)
 | O \
  \   \
   `~~~'
""".strip("\n"),
        "sleep": r"""
  .-.
 (- -) z
 | O \
  \   \
   `~~~'
""".strip("\n"),
        "tired": r"""
  .-.
 (- -)
 | O \
  \   \
   `~~~'
""".strip("\n"),
        "sick": r"""
  .-.
 (x x)
 | O \
  \   \
   `~~~'
""".strip("\n"),
        "dead": r"""
  .-.
 (_ _)
 | O \
  \   \
   `~~~'
""".strip("\n"),
    },
}


RUNV_ART = {
    "excelente": r"""
    _
   \\
   (O>
\\_//)
 \_/_
  / \\
""".strip("\n"),
    "bem": r"""
    _
   \\
   (o>
\\_//)
 \_/_
  / \\
""".strip("\n"),
    "atencao": r"""
    _
   \\
   (-<
\\_//)
 \_/_
  / \\
""".strip("\n"),
    "critico": r"""
    _
   \\
   (x<
\\_//)
 \_/_
  / \\
""".strip("\n"),
}


ANSI = {
    "reset": "\033[0m",
    "title": "\033[1;36m",
    "good": "\033[1;32m",
    "warn": "\033[1;33m",
    "bad": "\033[1;31m",
    "dim": "\033[2m",
    "cat": "\033[38;5;219m",
    "dog": "\033[38;5;180m",
    "fox": "\033[38;5;208m",
    "rabbit": "\033[38;5;225m",
    "turtle": "\033[38;5;71m",
    "bat": "\033[38;5;141m",
    "crow": "\033[38;5;250m",
    "raven": "\033[38;5;245m",
    "owl": "\033[38;5;110m",
    "blob": "\033[38;5;117m",
}


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _paint(text: str, color: str | None) -> str:
    if not color or not _supports_color():
        return text
    return f"{color}{text}{ANSI['reset']}"


def _state_color(pet: Pet) -> str:
    if not pet.alive or pet.health < 25:
        return ANSI["bad"]
    if pet.illness or pet.hunger > 70 or pet.energy < 35 or pet.hygiene < 40:
        return ANSI["warn"]
    return ANSI["good"]


def pick_art(pet: Pet) -> str:
    species = normalize_species(pet.species)
    art = PET_ART.get(species, PET_ART["blob"])
    if not pet.alive:
        mood = "dead"
    elif pet.is_sleeping:
        mood = "sleep"
    elif pet.illness or pet.health < 35:
        mood = "sick"
    elif pet.energy < 35 or pet.mood < 35:
        mood = "tired"
    else:
        mood = "happy"
    return _paint(art[mood], ANSI.get(species))


def bar(label: str, value: float, invert: bool = False, width: int = 22) -> str:
    shown = 100.0 - value if invert else value
    shown = max(0.0, min(100.0, shown))
    filled = round((shown / 100.0) * width)
    meter = "#" * filled + "-" * (width - filled)
    return f"{label:>9} [{meter}] {shown:5.1f}"


def human_delta(from_dt: datetime, to_dt: datetime) -> str:
    delta = max(0, int((to_dt - from_dt).total_seconds()))
    days, rem = divmod(delta, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        if days == 1:
            return "1 dia"
        return f"{days} dias"
    if hours:
        if hours == 1:
            return "1 hora"
        return f"{hours} horas"
    if minutes <= 1:
        return "1 minuto"
    return f"{minutes} minutos"


def human_ago(from_dt: datetime, to_dt: datetime) -> str:
    delta = max(0, int((to_dt - from_dt).total_seconds()))
    if delta < 60:
        return "agora mesmo"
    return f"{human_delta(from_dt, to_dt)} atras"


def _pet_hint(pet: Pet) -> str:
    if not pet.alive:
        return "O ciclo deste companheiro terminou."
    if pet.illness or pet.health < 40:
        return "Sugestao: `gotchi doctor` e depois um pouco de descanso."
    if pet.hunger > 70:
        return "Sugestao: `gotchi feed` antes que o humor piore."
    if pet.energy < 35:
        return "Sugestao: `gotchi sleep` para recuperar energia."
    if pet.hygiene < 40:
        return "Sugestao: `gotchi clean` para colocar tudo em ordem."
    if pet.mood < 45:
        return "Sugestao: `gotchi play` para animar o ambiente."
    return "Tudo em ordem. Um pouco de cuidado de vez em quando ja mantem o pet feliz."


def status_screen(pet: Pet, now: datetime) -> str:
    utc_now = now.astimezone(timezone.utc)
    created = pet.created_at.astimezone(timezone.utc)
    interaction = pet.last_interaction_at.astimezone(timezone.utc)
    header = _paint("gotchi // habitat", ANSI["title"])
    name_line = _paint(f"{pet.name} [{pet.species}]", ANSI.get(normalize_species(pet.species)))
    state_line = _paint(
        (
            f"Estado: {general_status(pet)} | Saude: {'doente' if pet.illness else 'estavel'} "
            f"| Vida: {'ativo' if pet.alive else 'encerrado'} | Sono: {'dormindo' if pet.is_sleeping else 'acordado'}"
        ),
        _state_color(pet),
    )
    lines = [
        header,
        name_line,
        pick_art(pet),
        state_line,
        bar("fome", pet.hunger),
        bar("energia", pet.energy),
        bar("humor", pet.mood),
        bar("higiene", pet.hygiene),
        bar("saude", pet.health),
        "",
        textwrap.fill(pet.last_message, width=72),
        textwrap.fill(_pet_hint(pet), width=72),
        "",
        f"Idade: {pet.age_hours / 24.0:.1f} dias | Criado: {human_ago(created, utc_now)}",
        f"Ultima interacao: {human_ago(interaction, utc_now)}",
        f"Ultimo update: {human_ago(pet.last_update_at, utc_now)}",
        "",
        _paint(
            "Acoes: init | status | path | line | feed | play | sleep | clean | rename NOVO_NOME | doctor | migrate | export | import | help",
            ANSI["dim"],
        ),
    ]
    if pet.cause_of_death:
        lines.insert(5, f"Causa da morte: {pet.cause_of_death}")
    return "\n".join(lines)


def runv_status_screen(status: ServerPetStatus) -> str:
    detail_map = {
        "excelente": "estavel",
        "bem": "calmo",
        "atencao": "sensivel",
        "critico": "hostil",
    }
    lines = [
        _paint("runv // observatorio", ANSI["title"]),
        _paint("corvo do servidor", ANSI["crow"]),
        _paint(RUNV_ART[status.status], ANSI["crow"]),
        _paint(f"Estado geral: {status.status} | Ninho: {status.perch}", ANSI["good"] if status.status in {"excelente", "bem"} else ANSI["warn"] if status.status == "atencao" else ANSI["bad"]),
        f"Ritmo do ar: {detail_map[status.load_state]}",
        f"Poleiro de dados: {detail_map[status.disk_state]}",
        f"Trilha de escrita: {detail_map[status.write_state]}",
        "",
        textwrap.fill(status.message, width=72),
        textwrap.fill("Este corvo nao aceita comandos. Ele so observa o humor do ninho.", width=72),
    ]
    return "\n".join(lines)


def path_screen(report: dict[str, str]) -> str:
    lines = [_paint("gotchi // path", ANSI["title"]), ""]
    for key in (
        "uid",
        "username",
        "home",
        "state_dir",
        "config_dir",
        "data_dir",
        "save_path",
        "lock_path",
        "config_path",
        "global_config_path",
    ):
        if key in report:
            lines.append(f"{key:>18}: {report[key]}")
    return "\n".join(lines)


def doctor_storage_screen(report: StorageDoctorReport) -> str:
    lines = [
        _paint("gotchi // storage doctor", ANSI["title"]),
        "",
        _paint(f"resultado: {'ok' if report.ok else 'problemas encontrados'}", ANSI["good"] if report.ok else ANSI["warn"]),
        f"save_path: {report.save_path}",
        f"lock_path: {report.lock_path}",
        "",
    ]
    lines.extend(report.checks)
    return "\n".join(lines)


def migration_screen(report: MigrationReport) -> str:
    lines = [_paint("gotchi // migrate", ANSI["title"]), "", report.message]
    if report.source_path is not None:
        lines.append(f"origem: {report.source_path}")
    if report.backup_path is not None:
        lines.append(f"backup: {report.backup_path}")
    return "\n".join(lines)


def status_line(pet: Pet) -> str:
    if not pet.alive:
        return f"{pet.name} se foi. O habitat ficou silencioso."
    hunger_band = "atencao" if pet.hunger >= 70 else "ok"
    mood_band = "otimo" if pet.mood >= 75 else "instavel" if pet.mood < 45 else "bom"
    if pet.is_sleeping:
        return f"{pet.name} dormiu bem. Humor: {mood_band}."
    return f"{pet.name} esta por perto. Fome: {hunger_band}. Humor: {mood_band}."


def help_text() -> str:
    return textwrap.dedent(
        """
        gotchi: bichinho virtual de terminal para comunidades pubnix.

        Comandos:
          gotchi                 abre a tela textual principal
          gotchi init            cria seu pet
          gotchi status          mostra o estado atual
          gotchi path            mostra caminhos e identidade efetiva
          gotchi line            mostra uma linha curta para login/shell
          gotchi feed            alimenta o pet
          gotchi play            brinca com o pet
          gotchi sleep           coloca o pet para dormir
          gotchi clean           limpa o pet
          gotchi rename NOME     renomeia o pet
          gotchi doctor          tenta tratar doenca / recuperar saude
          gotchi doctor --storage verifica storage, migracao e integridade
          gotchi migrate         tenta migrar save legado
          gotchi export [ARQ]    exporta o pet atual em JSON
          gotchi import ARQ      importa backup do proprio usuario
          gotchi help            mostra esta ajuda

        Sem daemon:
          O estado e recalculado pelo tempo decorrido desde o ultimo update.

        desenvolvido por admin@runv.club
        """
    ).strip()
