from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_FILE = Path(__file__).resolve().parent / "data" / "scenarios.json"


@lru_cache(maxsize=1)
def _load_data() -> dict[str, Any]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def get_all_locations() -> dict[str, dict[str, Any]]:
    return deepcopy(_load_data()["locations"])


def list_scenarios() -> list[dict[str, Any]]:
    return [deepcopy(item) for item in _load_data()["scenarios"].values()]


def get_scenario(scenario_id: str) -> dict[str, Any]:
    scenarios = _load_data()["scenarios"]
    if scenario_id not in scenarios:
        raise KeyError(f"Unknown scenario: {scenario_id}")
    return deepcopy(scenarios[scenario_id])
