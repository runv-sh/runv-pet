from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Pet:
    username: str
    name: str
    species: str
    created_at: datetime
    last_interaction_at: datetime
    last_update_at: datetime
    age_hours: float
    hunger: float
    energy: float
    mood: float
    hygiene: float
    health: float
    is_sleeping: bool
    sleeping_since: Optional[datetime]
    illness: bool
    alive: bool
    cause_of_death: Optional[str]
    last_message: str

    def evolve(self, **changes: Any) -> "Pet":
        return replace(self, **changes)

    def to_record(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "name": self.name,
            "species": self.species,
            "created_at": self.created_at.isoformat(),
            "last_interaction_at": self.last_interaction_at.isoformat(),
            "last_update_at": self.last_update_at.isoformat(),
            "age_hours": self.age_hours,
            "hunger": self.hunger,
            "energy": self.energy,
            "mood": self.mood,
            "hygiene": self.hygiene,
            "health": self.health,
            "is_sleeping": int(self.is_sleeping),
            "sleeping_since": self.sleeping_since.isoformat() if self.sleeping_since else None,
            "illness": int(self.illness),
            "alive": int(self.alive),
            "cause_of_death": self.cause_of_death,
            "last_message": self.last_message,
        }

    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> "Pet":
        return cls(
            username=record["username"],
            name=record["name"],
            species=record["species"],
            created_at=datetime.fromisoformat(record["created_at"]),
            last_interaction_at=datetime.fromisoformat(record["last_interaction_at"]),
            last_update_at=datetime.fromisoformat(record["last_update_at"]),
            age_hours=float(record["age_hours"]),
            hunger=float(record["hunger"]),
            energy=float(record["energy"]),
            mood=float(record["mood"]),
            hygiene=float(record["hygiene"]),
            health=float(record["health"]),
            is_sleeping=bool(record["is_sleeping"]),
            sleeping_since=datetime.fromisoformat(record["sleeping_since"]) if record["sleeping_since"] else None,
            illness=bool(record["illness"]),
            alive=bool(record["alive"]),
            cause_of_death=record["cause_of_death"],
            last_message=record["last_message"] or "",
        )
