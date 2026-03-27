from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gotchi_app.cli import main
from gotchi_app.config import Tuning, config_path, load_tuning
from gotchi_app.runv_mode import inspect_server_pet
from gotchi_app.simulator import apply_time, create_pet, interact
from gotchi_app.storage import load_pet, save_pet


class SimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
        self.tuning = Tuning()
        self.pet = create_pet("alice", "Nix", "crow", self.now)

    def test_time_passage_degrades_needs(self) -> None:
        later = self.now + timedelta(hours=4)
        updated = apply_time(self.pet, later, self.tuning)
        self.assertGreater(updated.hunger, self.pet.hunger)
        self.assertLess(updated.energy, self.pet.energy)
        self.assertLess(updated.hygiene, self.pet.hygiene)

    def test_feed_reduces_hunger(self) -> None:
        hungry = self.pet.evolve(hunger=80.0, energy=50.0, mood=40.0)
        fed = interact(hungry, "feed", self.now, self.tuning)
        self.assertLess(fed.hunger, hungry.hunger)
        self.assertGreater(fed.mood, hungry.mood)

    def test_sleep_restores_energy_over_time(self) -> None:
        sleepy = interact(self.pet.evolve(energy=20.0), "sleep", self.now, self.tuning)
        later = self.now + timedelta(hours=3)
        rested = apply_time(sleepy, later, self.tuning)
        self.assertGreater(rested.energy, sleepy.energy)

    def test_sleep_is_idempotent_while_already_sleeping(self) -> None:
        sleepy = interact(self.pet.evolve(energy=20.0, mood=40.0), "sleep", self.now, self.tuning)
        same_sleep = interact(sleepy, "sleep", self.now + timedelta(seconds=5), self.tuning)
        self.assertTrue(same_sleep.is_sleeping)
        self.assertEqual(same_sleep.sleeping_since, sleepy.sleeping_since)
        self.assertIn("ja esta dormindo", same_sleep.last_message)

    def test_clean_improves_hygiene(self) -> None:
        dirty = self.pet.evolve(hygiene=10.0)
        cleaned = interact(dirty, "clean", self.now, self.tuning)
        self.assertGreater(cleaned.hygiene, dirty.hygiene)

    def test_neglect_causes_illness(self) -> None:
        weak = self.pet.evolve(hunger=92.0, energy=8.0, hygiene=6.0, health=42.0)
        later = self.now + timedelta(hours=6)
        updated = apply_time(weak, later, self.tuning)
        self.assertTrue(updated.illness)
        self.assertLess(updated.health, weak.health)

    def test_extreme_neglect_causes_death(self) -> None:
        doomed = self.pet.evolve(hunger=100.0, energy=0.0, hygiene=0.0, health=8.0)
        later = self.now + timedelta(hours=24)
        updated = apply_time(doomed, later, self.tuning)
        self.assertFalse(updated.alive)
        self.assertEqual(updated.health, 0.0)


class StorageTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self) -> None:
        db = Path(__file__).resolve().parents[1] / ".test-artifacts" / "gotchi.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        if db.exists():
            db.unlink()
        now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
        pet = create_pet("bob", "Rune", "crow", now)
        save_pet(pet, path=db)
        loaded = load_pet("bob", path=db)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Rune")


class ConfigTests(unittest.TestCase):
    def test_config_load_returns_defaults_when_preferred_xdg_path_is_unusable(self) -> None:
        artifacts = Path(__file__).resolve().parents[1] / ".test-artifacts" / "config-case"
        artifacts.mkdir(parents=True, exist_ok=True)
        config_home = artifacts / "config-home"
        config_home.mkdir(parents=True, exist_ok=True)
        collision = config_home / "runv-pet"
        collision.write_text("occupied", encoding="utf-8")

        old = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = str(config_home)
        try:
            resolved = config_path()
            tuning = load_tuning()
        finally:
            if old is None:
                os.environ.pop("XDG_CONFIG_HOME", None)
            else:
                os.environ["XDG_CONFIG_HOME"] = old

        self.assertEqual(tuning, Tuning())
        self.assertEqual(resolved.name, "gotchi.json")


class RunvModeTests(unittest.TestCase):
    def test_runv_status_is_renderable(self) -> None:
        status = inspect_server_pet()
        self.assertIn(status.status, {"excelente", "bem", "atencao", "critico"})

    def test_hidden_runv_flag_does_not_crash(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["-runv"])
        self.assertEqual(code, 0)
        output = buffer.getvalue()
        self.assertIn("corvo do servidor", output)
        self.assertIn("Estado geral:", output)


if __name__ == "__main__":
    unittest.main()
