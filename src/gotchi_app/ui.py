from __future__ import annotations

import textwrap
from datetime import datetime, timezone

from .models import Pet
from .runv_mode import ServerPetStatus
from .simulator import general_status


ASCII_ART = {
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


def pick_art(pet: Pet) -> str:
    if not pet.alive:
        return ASCII_ART["dead"]
    if pet.is_sleeping:
        return ASCII_ART["sleep"]
    if pet.illness or pet.health < 35:
        return ASCII_ART["sick"]
    if pet.energy < 35 or pet.mood < 35:
        return ASCII_ART["tired"]
    return ASCII_ART["happy"]


def bar(label: str, value: float, invert: bool = False, width: int = 22) -> str:
    shown = 100.0 - value if invert else value
    shown = max(0.0, min(100.0, shown))
    filled = round((shown / 100.0) * width)
    meter = "#" * filled + "-" * (width - filled)
    return f"{label:>9} [{meter}] {shown:5.1f}"


def human_delta(from_dt: datetime, to_dt: datetime) -> str:
    delta = max(0, int((to_dt - from_dt).total_seconds()))
    hours, rem = divmod(delta, 3600)
    minutes, _ = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _pet_hint(pet: Pet) -> str:
    if not pet.alive:
        return "O ciclo deste corvo se encerrou."
    if pet.illness or pet.health < 40:
        return "Sugestao: `gotchi doctor` e depois um pouco de descanso."
    if pet.hunger > 70:
        return "Sugestao: `gotchi feed` antes que o humor azede."
    if pet.energy < 35:
        return "Sugestao: `gotchi sleep` para recuperar o poleiro."
    if pet.hygiene < 40:
        return "Sugestao: `gotchi clean` para alinhar as penas."
    if pet.mood < 45:
        return "Sugestao: `gotchi play` para espantar a carranca."
    return "Tudo em ordem. Um agrado ocasional ja mantem o corvo por perto."


def status_screen(pet: Pet, now: datetime) -> str:
    utc_now = now.astimezone(timezone.utc)
    created = pet.created_at.astimezone(timezone.utc)
    interaction = pet.last_interaction_at.astimezone(timezone.utc)
    lines = [
        "gotchi // poleiro",
        f"{pet.name} [{pet.species}]",
        pick_art(pet),
        (
            f"Estado: {general_status(pet)} | Saude: {'doente' if pet.illness else 'estavel'} "
            f"| Vida: {'ativo' if pet.alive else 'encerrado'} | Sono: {'dormindo' if pet.is_sleeping else 'acordado'}"
        ),
        bar("fome", pet.hunger),
        bar("energia", pet.energy),
        bar("humor", pet.mood),
        bar("higiene", pet.hygiene),
        bar("saude", pet.health),
        "",
        textwrap.fill(pet.last_message, width=72),
        textwrap.fill(_pet_hint(pet), width=72),
        "",
        f"Idade: {pet.age_hours / 24.0:.1f} dias | Criado ha: {human_delta(created, utc_now)}",
        f"Ultima interacao: {human_delta(interaction, utc_now)} atras",
        f"Ultimo update: {pet.last_update_at.isoformat()}",
        "",
        "Acoes: init | status | feed | play | sleep | clean | rename NOVO_NOME | doctor | help",
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
        "runv // observatorio",
        "corvo do servidor",
        RUNV_ART[status.status],
        f"Estado geral: {status.status} | Ninho: {status.perch}",
        f"Ritmo do ar: {detail_map[status.load_state]}",
        f"Poleiro de dados: {detail_map[status.disk_state]}",
        f"Trilha de escrita: {detail_map[status.write_state]}",
        "",
        textwrap.fill(status.message, width=72),
        textwrap.fill("Este corvo nao aceita comandos. Ele so observa o humor do ninho.", width=72),
    ]
    return "\n".join(lines)


def help_text() -> str:
    return textwrap.dedent(
        """
        gotchi: bichinho virtual de terminal para comunidades pubnix.

        Comandos:
          gotchi                 abre a tela textual principal
          gotchi init            cria seu pet
          gotchi status          mostra o estado atual
          gotchi feed            alimenta o pet
          gotchi play            brinca com o pet
          gotchi sleep           coloca o pet para dormir
          gotchi clean           limpa o pet
          gotchi rename NOME     renomeia o pet
          gotchi doctor          tenta tratar doenca / recuperar saude
          gotchi help            mostra esta ajuda

        Sem daemon:
          O estado e recalculado pelo tempo decorrido desde o ultimo update.

        desenvolvido por admin@runv.club
        """
    ).strip()
