from __future__ import annotations

import math
from typing import Any


def parse_hhmm(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def format_hhmm(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def estimate_walk_minutes(source: dict[str, Any], target: dict[str, Any]) -> int:
    if source["id"] == target["id"]:
        return 0
    distance = math.hypot(source["x"] - target["x"], source["y"] - target["y"])
    return max(4, round(distance * 0.32 + 2))
