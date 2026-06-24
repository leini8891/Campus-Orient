from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from backend.scenario_store import get_all_locations
from backend.utils import format_hhmm


CALENDAR_DIR = Path(__file__).resolve().parent / "data" / "calendars"
ICAL_KEY_VALUE = re.compile(r"^([A-Z-]+)(?:;[^:]+)?:([^\n]+)$")


def _load_calendar_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _filter_events(events: list[dict[str, Any]], scenario_id: str | None) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for event in events:
        scenario_ids = event.get("scenario_ids", [])
        if not scenario_ids or scenario_id in scenario_ids:
            filtered.append(
                {
                    "start_time": event["start_time"],
                    "end_time": event["end_time"],
                    "event": event["event"],
                    "location_id": event["location_id"],
                }
            )
    return filtered


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _infer_location_id(raw_text: str | None, fallback_location_id: str | None) -> str | None:
    if not raw_text:
        return fallback_location_id

    normalized = _normalize(raw_text)
    for location in get_all_locations().values():
        haystacks = [location["id"], location["name"], location["short_name"]]
        if any(_normalize(item) in normalized or normalized in _normalize(item) for item in haystacks):
            return location["id"]
    return fallback_location_id


def _parse_json_upload(content: str, date: str, scenario_id: str | None) -> dict[str, Any]:
    parsed = json.loads(content)
    if isinstance(parsed, dict) and "dates" in parsed:
        events = parsed.get("dates", {}).get(date, [])
        return {
            "timezone": parsed.get("timezone", "Asia/Singapore"),
            "busy_slots": _filter_events(events, scenario_id),
        }
    if isinstance(parsed, dict) and "busy_slots" in parsed:
        return {
            "timezone": parsed.get("timezone", "Asia/Singapore"),
            "busy_slots": list(parsed.get("busy_slots", [])),
        }
    if isinstance(parsed, list):
        return {
            "timezone": "Asia/Singapore",
            "busy_slots": list(parsed),
        }
    return {
        "timezone": "Asia/Singapore",
        "busy_slots": [],
    }


def _parse_ics_datetime(value: str) -> tuple[str, str]:
    value = value.strip()
    if len(value) >= 15 and "T" in value:
        date_part = value[:8]
        time_part = value[9:13]
        date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        time = f"{time_part[:2]}:{time_part[2:4]}"
        return date, time
    if len(value) >= 8:
        date_part = value[:8]
        date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        return date, "00:00"
    return "", "00:00"


def _parse_ics_upload(content: str, date: str, fallback_location_id: str | None) -> dict[str, Any]:
    timezone = "Asia/Singapore"
    busy_slots: list[dict[str, Any]] = []
    current_event: dict[str, str] = {}

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line == "BEGIN:VEVENT":
            current_event = {}
            continue
        if line == "END:VEVENT":
            start_date, start_time = _parse_ics_datetime(current_event.get("DTSTART", ""))
            end_date, end_time = _parse_ics_datetime(current_event.get("DTEND", ""))
            if start_date == date and (end_date == date or not end_date):
                location_id = (
                    current_event.get("X-LOCATION-ID")
                    or _infer_location_id(current_event.get("LOCATION"), fallback_location_id)
                    or _infer_location_id(current_event.get("SUMMARY"), fallback_location_id)
                )
                if location_id:
                    busy_slots.append(
                        {
                            "start_time": start_time,
                            "end_time": end_time if end_time != "00:00" else format_hhmm((24 * 60) - 1),
                            "event": current_event.get("SUMMARY", "Calendar Event"),
                            "location_id": location_id,
                        }
                    )
            current_event = {}
            continue

        match = ICAL_KEY_VALUE.match(line)
        if match:
            key, value = match.groups()
            current_event[key] = value
            if key == "X-WR-TIMEZONE":
                timezone = value

    return {
        "timezone": timezone,
        "busy_slots": busy_slots,
    }


def parse_uploaded_calendar(
    upload: dict[str, Any] | None,
    date: str,
    scenario_id: str | None,
    fallback_location_id: str | None,
) -> dict[str, Any] | None:
    if not upload:
        return None

    file_name = upload.get("file_name", "")
    content = upload.get("content", "")
    suffix = Path(file_name).suffix.lower()
    try:
        if suffix == ".json":
            return _parse_json_upload(content, date, scenario_id)
        if suffix == ".ics":
            return _parse_ics_upload(content, date, fallback_location_id)
    except (json.JSONDecodeError, ValueError):
        return {
            "timezone": "Asia/Singapore",
            "busy_slots": [],
        }

    return {
        "timezone": "Asia/Singapore",
        "busy_slots": [],
    }


def load_calendar_events(
    user_id: str,
    date: str,
    scenario_id: str | None = None,
    calendar_file: str | None = None,
    uploaded_calendar: dict[str, Any] | None = None,
    fallback_location_id: str | None = None,
) -> dict[str, Any]:
    parsed_upload = parse_uploaded_calendar(uploaded_calendar, date, scenario_id, fallback_location_id)
    if parsed_upload is not None:
        return parsed_upload

    try:
        if calendar_file:
            data = _load_calendar_file(Path(calendar_file))
        else:
            data = _load_calendar_file(CALENDAR_DIR / f"{user_id}.json")
    except FileNotFoundError:
        return {
            "timezone": "Asia/Singapore",
            "busy_slots": [],
        }

    events = data.get("dates", {}).get(date, [])
    return {
        "timezone": data.get("timezone", "Asia/Singapore"),
        "busy_slots": _filter_events(events, scenario_id),
    }
