from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from .config import Tuning
from .models import Pet


SPECIES = ("crow", "raven", "owl", "cat", "fox", "blob")


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def create_pet(owner_uid: int, username: str, name: str, species: str, now: datetime) -> Pet:
    species_name = species if species in SPECIES else SPECIES[0]
    return Pet(
        owner_uid=owner_uid,
        username=username,
        name=name,
        species=species_name,
        created_at=now,
        last_interaction_at=now,
        last_update_at=now,
        age_hours=0.0,
        hunger=18.0,
        energy=78.0,
        mood=82.0,
        hygiene=76.0,
        health=92.0,
        is_sleeping=False,
        sleeping_since=None,
        illness=False,
        alive=True,
        cause_of_death=None,
        last_message="Pousou no terminal e tomou posse do poleiro.",
    )


def general_status(pet: Pet) -> str:
    if not pet.alive:
        return "morto"
    worst = min(100.0 - pet.hunger, pet.energy, pet.mood, pet.hygiene, pet.health)
    if worst >= 75:
        return "excelente"
    if worst >= 50:
        return "bem"
    if worst >= 25:
        return "atencao"
    return "critico"


def mood_message(pet: Pet) -> str:
    if not pet.alive:
        return "O poleiro ficou quieto demais."
    if pet.illness:
        return f"{pet.name} arrepia as penas e precisa de cuidado."
    if pet.is_sleeping:
        return f"{pet.name} dorme empoleirado, um olho quase aberto para o servidor."
    state = general_status(pet)
    if state == "excelente":
        return f"{pet.name} vigia o terminal com elegancia suspeita."
    if state == "bem":
        return f"{pet.name} segue firme, mas quer um agrado antes de voar pela casa."
    if state == "atencao":
        return f"{pet.name} bate o bico no prompt pedindo presenca."
    return f"{pet.name} esta sem paciencia para abandono."


def _health_pressure(pet: Pet) -> Tuple[float, float]:
    pressure = 0.0
    neglect_hours = 0.0
    if pet.hunger >= 75:
        pressure += (pet.hunger - 74) / 26
        neglect_hours += 1.0
    if pet.energy <= 25:
        pressure += (26 - pet.energy) / 26
        neglect_hours += 1.0
    if pet.hygiene <= 25:
        pressure += (26 - pet.hygiene) / 26
        neglect_hours += 1.0
    return pressure, neglect_hours


def apply_time(pet: Pet, now: datetime, tuning: Tuning) -> Pet:
    if now <= pet.last_update_at:
        return pet.evolve(last_message=mood_message(pet))
    elapsed_hours = (now - pet.last_update_at).total_seconds() / 3600.0
    age_hours = pet.age_hours + elapsed_hours

    hunger = pet.hunger
    energy = pet.energy
    hygiene = pet.hygiene
    mood = pet.mood
    health = pet.health
    is_sleeping = pet.is_sleeping
    sleeping_since = pet.sleeping_since

    if pet.is_sleeping:
        hunger += tuning.sleep_hunger_per_hour * elapsed_hours
        energy += tuning.sleep_energy_gain_per_hour * elapsed_hours
        hygiene -= (tuning.hygiene_loss_per_hour * 0.35) * elapsed_hours
        if energy >= 92:
            is_sleeping = False
            sleeping_since = None
    else:
        hunger += tuning.hunger_per_hour * elapsed_hours
        energy -= tuning.energy_loss_per_hour * elapsed_hours
        hygiene -= tuning.hygiene_loss_per_hour * elapsed_hours

    hunger = clamp(hunger, 0.0, tuning.max_stat)
    energy = clamp(energy, 0.0, tuning.max_stat)
    hygiene = clamp(hygiene, 0.0, tuning.max_stat)

    comfort = ((100.0 - hunger) + energy + hygiene) / 3.0
    target_mood = clamp((comfort * 0.75) + (health * 0.25))
    if target_mood >= mood:
        mood += tuning.mood_recovery_per_hour * elapsed_hours
    else:
        mood -= tuning.mood_penalty_per_hour * elapsed_hours
    mood = clamp((mood + target_mood) / 2.0)

    pressure, neglect_markers = _health_pressure(
        pet.evolve(hunger=hunger, energy=energy, hygiene=hygiene, mood=mood, health=health)
    )
    if pressure > 0:
        health -= tuning.health_penalty_per_hour * pressure * elapsed_hours
    else:
        health += tuning.health_recovery_per_hour * elapsed_hours
    health = clamp(health, 0.0, tuning.max_stat)

    illness = pet.illness or health <= tuning.illness_threshold
    if illness and health >= tuning.illness_threshold + 18:
        illness = False

    dead = not pet.alive
    cause = pet.cause_of_death
    neglect_hours = elapsed_hours * neglect_markers
    if health <= 0:
        dead = True
        cause = "Saude zerada apos negligencia prolongada."
    elif neglect_hours >= tuning.death_threshold_hours:
        dead = True
        cause = "Abandono completo por tempo demais."

    if dead:
        return pet.evolve(
            age_hours=age_hours,
            hunger=hunger,
            energy=energy,
            mood=0.0,
            hygiene=hygiene,
            health=0.0,
            is_sleeping=False,
            sleeping_since=None,
            illness=True,
            alive=False,
            cause_of_death=cause,
            last_update_at=now,
            last_message=mood_message(
                pet.evolve(
                    alive=False,
                    cause_of_death=cause,
                    age_hours=age_hours,
                    hunger=hunger,
                    energy=energy,
                    hygiene=hygiene,
                    health=0.0,
                    mood=0.0,
                    is_sleeping=False,
                    sleeping_since=None,
                    illness=True,
                    last_update_at=now,
                )
            ),
        )

    updated = pet.evolve(
        age_hours=age_hours,
        hunger=hunger,
        energy=energy,
        mood=mood,
        hygiene=hygiene,
        health=health,
        is_sleeping=is_sleeping,
        sleeping_since=sleeping_since,
        illness=illness,
        last_update_at=now,
    )
    return updated.evolve(last_message=mood_message(updated))


def interact(pet: Pet, action: str, now: datetime, tuning: Tuning) -> Pet:
    pet = apply_time(pet, now, tuning)
    if not pet.alive:
        return pet

    hunger = pet.hunger
    energy = pet.energy
    hygiene = pet.hygiene
    mood = pet.mood
    health = pet.health
    is_sleeping = pet.is_sleeping
    sleeping_since = pet.sleeping_since
    message = pet.last_message

    if action == "feed":
        hunger = clamp(hunger - 28)
        energy = clamp(energy + 6)
        mood = clamp(mood + 8)
        health = clamp(health + 3)
        message = f"{pet.name} bicou a comida e ficou de vigia no poleiro."
    elif action == "play":
        hunger = clamp(hunger + 10)
        energy = clamp(energy - 14)
        hygiene = clamp(hygiene - 7)
        mood = clamp(mood + 16)
        health = clamp(health + 2)
        message = f"{pet.name} deu rasantes pelo terminal e voltou satisfeito(a)."
    elif action == "sleep":
        if pet.is_sleeping:
            message = f"{pet.name} ja esta dormindo. Melhor nao mexer no poleiro."
        else:
            is_sleeping = True
            sleeping_since = now
            mood = clamp(mood + 4)
            message = f"{pet.name} se encolheu no poleiro para tirar um sono leve."
    elif action == "clean":
        hygiene = clamp(hygiene + 32)
        mood = clamp(mood + 6)
        health = clamp(health + 4)
        message = f"{pet.name} alinhou as penas e ficou bem mais apresentavel."
    elif action == "doctor":
        if pet.illness or pet.health < 70:
            health = clamp(health + 24)
            mood = clamp(mood + 5)
            energy = clamp(energy + 4)
            message = f"{pet.name} recebeu cuidados e voltou a firmar o olhar."
        else:
            message = f"{pet.name} nao precisava de medico, mas aceitou a visita com dignidade."

    illness = pet.illness
    if health >= tuning.illness_threshold + 15:
        illness = False

    updated = pet.evolve(
        hunger=hunger,
        energy=energy,
        hygiene=hygiene,
        mood=mood,
        health=health,
        is_sleeping=is_sleeping,
        sleeping_since=sleeping_since,
        illness=illness,
        last_interaction_at=now,
        last_update_at=now,
        last_message=message,
    )
    return updated
