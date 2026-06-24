from __future__ import annotations

import itertools
from copy import deepcopy
from typing import Any, Iterable

from backend.scenario_store import get_all_locations
from backend.utils import format_hhmm, parse_hhmm


def _route_minutes(route_matrix: dict[str, Any], from_id: str, to_id: str) -> int:
    if from_id == to_id:
        return 0
    return route_matrix[f"{from_id}-{to_id}"]["time_mins"]


def _segment_compositions(total: int, bins: int) -> Iterable[tuple[int, ...]]:
    if bins == 1:
        yield (total,)
        return
    for current in range(total + 1):
        for remainder in _segment_compositions(total - current, bins - 1):
            yield (current,) + remainder


def _schedule_task(
    task: dict[str, Any],
    time_cursor: int,
    current_location: str,
    route_matrix: dict[str, Any],
) -> dict[str, Any] | None:
    travel_time = _route_minutes(route_matrix, current_location, task["location_id"])
    arrival = time_cursor + travel_time

    for raw_window in task["working_hours"]:
        window_start_raw, window_end_raw = raw_window.split("-")
        window_start = parse_hhmm(window_start_raw)
        window_end = parse_hhmm(window_end_raw)
        start_time = max(arrival, window_start)
        end_time = start_time + task["estimated_duration_mins"]
        if end_time <= window_end:
            return {
                "start": start_time,
                "end": end_time,
                "arrival": arrival,
                "travel_time": travel_time,
                "location_id": task["location_id"],
                "action": task["action"],
                "required_materials": list(task.get("required_materials", [])),
                "notes": task.get("notes", ""),
                "window": raw_window,
                "is_fixed": False,
                "kind": "task",
            }

    return None


def _schedule_busy_slot(
    slot: dict[str, Any],
    time_cursor: int,
    current_location: str,
    route_matrix: dict[str, Any],
) -> dict[str, Any] | None:
    travel_time = _route_minutes(route_matrix, current_location, slot["location_id"])
    arrival = time_cursor + travel_time
    slot_start = parse_hhmm(slot["start_time"])
    slot_end = parse_hhmm(slot["end_time"])
    if arrival > slot_start:
        return None

    return {
        "start": slot_start,
        "end": slot_end,
        "arrival": arrival,
        "travel_time": travel_time,
        "location_id": slot["location_id"],
        "action": f"上课：{slot['event']}",
        "required_materials": [],
        "notes": "固定日程，来自本地日历。",
        "window": f"{slot['start_time']}-{slot['end_time']}",
        "is_fixed": True,
        "kind": "busy_slot",
    }


def _append_destination(
    scenario: dict[str, Any],
    time_cursor: int,
    current_location: str,
    route_matrix: dict[str, Any],
) -> dict[str, Any] | None:
    destination_location = scenario.get("destination_location")
    destination_action = scenario.get("destination_action")
    if not destination_location or not destination_action:
        return None

    travel_time = _route_minutes(route_matrix, current_location, destination_location)
    arrival = time_cursor + travel_time
    duration = scenario.get("destination_duration_mins", 0)
    return {
        "start": arrival,
        "end": arrival + duration,
        "arrival": arrival,
        "travel_time": travel_time,
        "location_id": destination_location,
        "action": destination_action,
        "required_materials": list(scenario.get("destination_materials", [])),
        "notes": scenario.get("destination_notes", ""),
        "window": None,
        "is_fixed": False,
        "kind": "destination",
    }


def _to_timeline_entry(step: int, item: dict[str, Any], locations: dict[str, Any]) -> dict[str, Any]:
    location = locations[item["location_id"]]
    return {
        "step": step,
        "time_est": format_hhmm(item["start"]),
        "end_time": format_hhmm(item["end"]),
        "location_id": item["location_id"],
        "location_name": location["name"],
        "action": item["action"],
        "is_fixed": item["is_fixed"],
        "type": item["kind"],
        "materials": item["required_materials"],
        "notes": item["notes"],
        "window": item["window"],
    }


def _score_schedule(sequence: list[dict[str, Any]]) -> tuple[int, int]:
    finish = sequence[-1]["end"] if sequence else 24 * 60
    wait_cost = sum(max(0, item["start"] - item["arrival"]) for item in sequence)
    return finish, wait_cost


def _build_route_paths(stops: list[str], route_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for current, nxt in zip(stops, stops[1:]):
        if current == nxt:
            continue
        paths.append(
            {
                "from": current,
                "to": nxt,
                "method": "walk",
                "time_mins": _route_minutes(route_matrix, current, nxt),
            }
        )
    return paths


def _simulate(
    ordered_tasks: tuple[dict[str, Any], ...],
    segment_counts: tuple[int, ...],
    busy_slots: list[dict[str, Any]],
    scenario: dict[str, Any],
    current_time: int,
    current_location: str,
    route_matrix: dict[str, Any],
) -> dict[str, Any] | None:
    time_cursor = current_time
    location_cursor = current_location
    scheduled: list[dict[str, Any]] = []
    stops = [current_location]
    task_index = 0

    for segment_index, count in enumerate(segment_counts):
        next_busy_slot = busy_slots[segment_index] if segment_index < len(busy_slots) else None

        for _ in range(count):
            task = ordered_tasks[task_index]
            task_result = _schedule_task(task, time_cursor, location_cursor, route_matrix)
            if task_result is None:
                return None
            if next_busy_slot and task_result["end"] > parse_hhmm(next_busy_slot["start_time"]):
                return None
            scheduled.append(task_result)
            time_cursor = task_result["end"]
            location_cursor = task["location_id"]
            stops.append(location_cursor)
            task_index += 1

        if next_busy_slot:
            fixed_result = _schedule_busy_slot(next_busy_slot, time_cursor, location_cursor, route_matrix)
            if fixed_result is None:
                return None
            scheduled.append(fixed_result)
            time_cursor = fixed_result["end"]
            location_cursor = next_busy_slot["location_id"]
            stops.append(location_cursor)

    destination = _append_destination(scenario, time_cursor, location_cursor, route_matrix)
    if destination is not None:
        scheduled.append(destination)
        location_cursor = destination["location_id"]
        stops.append(location_cursor)

    if not scheduled:
        return None

    return {
        "sequence": scheduled,
        "stops": stops,
        "score": _score_schedule(scheduled),
        "destination_location": location_cursor,
    }


def plan_scenario(
    scenario: dict[str, Any],
    current_time: str,
    current_location: str,
    busy_slots: list[dict[str, Any]],
    route_matrix: dict[str, Any],
) -> dict[str, Any]:
    locations = get_all_locations()
    tasks = scenario.get("tasks", [])
    fixed_slots = sorted(busy_slots, key=lambda item: parse_hhmm(item["start_time"]))
    current_minutes = parse_hhmm(current_time)
    candidates: list[dict[str, Any]] = []

    for ordered_tasks in itertools.permutations(tasks):
        for segment_counts in _segment_compositions(len(tasks), len(fixed_slots) + 1):
            candidate = _simulate(
                ordered_tasks=ordered_tasks,
                segment_counts=segment_counts,
                busy_slots=fixed_slots,
                scenario=scenario,
                current_time=current_minutes,
                current_location=current_location,
                route_matrix=route_matrix,
            )
            if candidate is not None:
                candidates.append(candidate)

    if not candidates:
        return {"status": "blocked"}

    best_plan = min(candidates, key=lambda item: item["score"])
    timeline = [
        _to_timeline_entry(index, entry, locations)
        for index, entry in enumerate(best_plan["sequence"], start=1)
    ]
    relevant_locations = {current_location, best_plan["destination_location"]}
    relevant_locations.update(item["location_id"] for item in best_plan["sequence"])
    location_catalog = {
        location_id: deepcopy(locations[location_id])
        for location_id in relevant_locations
    }

    return {
        "status": "success",
        "timeline": timeline,
        "route_paths": _build_route_paths(best_plan["stops"], route_matrix),
        "location_catalog": location_catalog,
        "destination_location": best_plan["destination_location"],
    }


def plan_itinerary(request_body: dict[str, Any] | None = None) -> dict[str, Any]:
    from backend.agent import PlanningAgent

    agent = PlanningAgent()
    return agent.handle(request_body)
