from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"


def build_sync_candidates(plan_response: dict[str, Any]) -> list[dict[str, Any]]:
    date = plan_response.get("date")
    timezone_name = plan_response.get("timezone", "Asia/Singapore")
    scenario_title = plan_response.get("scenario_title") or "Student Assistant Route"
    candidates: list[dict[str, Any]] = []

    for item in plan_response.get("timeline", []):
        if item.get("is_fixed"):
            continue

        materials = ", ".join(item.get("materials", []))
        description_parts = [f"Generated from {scenario_title}."]
        if item.get("notes"):
            description_parts.append(item["notes"])
        if materials:
            description_parts.append(f"Materials: {materials}.")

        candidates.append(
            {
                "event_id": f"timeline-{item['step']}",
                "event_title": item["action"],
                "date": date,
                "start_time": item["time_est"],
                "end_time": item["end_time"],
                "all_day": False,
                "timezone": timezone_name,
                "location": item["location_name"],
                "description": " ".join(description_parts),
                "needs_confirmation": True,
                "source_step": item["step"],
            }
        )

    return candidates


def _escape_ics(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _to_ics_datetime(date: str, time_value: str) -> str:
    compact_date = date.replace("-", "")
    compact_time = time_value.replace(":", "")
    return f"{compact_date}T{compact_time}00"


def export_events_to_ics(
    events: list[dict[str, Any]],
    output_dir: str | None = None,
) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else EXPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    file_path = target_dir / f"student-assistant-sync-{timestamp}.ics"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Student Assistant//EN",
        "CALSCALE:GREGORIAN",
    ]

    for index, event in enumerate(events, start=1):
        uid = f"{timestamp}-{index}@student-assistant"
        now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART:{_to_ics_datetime(event['date'], event['start_time'])}",
                f"DTEND:{_to_ics_datetime(event['date'], event['end_time'])}",
                f"SUMMARY:{_escape_ics(event['event_title'])}",
                f"LOCATION:{_escape_ics(event.get('location') or '')}",
                f"DESCRIPTION:{_escape_ics(event.get('description') or '')}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "status": "success",
        "synced_events": events,
        "skipped_events": [],
        "failed_events": [],
        "reasons": [],
        "suggested_next_action": f"Import the exported ICS into Google Calendar or another calendar app from {file_path}.",
        "export_file": str(file_path),
        "provider": "ics",
    }


def _google_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": event["event_title"],
        "location": event.get("location"),
        "description": event.get("description"),
        "start": {
            "dateTime": f"{event['date']}T{event['start_time']}:00",
            "timeZone": event.get("timezone", "Asia/Singapore"),
        },
        "end": {
            "dateTime": f"{event['date']}T{event['end_time']}:00",
            "timeZone": event.get("timezone", "Asia/Singapore"),
        },
    }


def sync_events_to_google(
    events: list[dict[str, Any]],
    access_token: str | None = None,
    calendar_id: str | None = None,
) -> dict[str, Any]:
    access_token = access_token or os.environ.get("GOOGLE_CALENDAR_ACCESS_TOKEN")
    calendar_id = calendar_id or os.environ.get("GOOGLE_CALENDAR_ID", "primary")

    if not access_token:
        return {
            "status": "failed",
            "synced_events": [],
            "skipped_events": [],
            "failed_events": [
                {
                    "event_title": event["event_title"],
                    "reason": "Missing GOOGLE_CALENDAR_ACCESS_TOKEN.",
                }
                for event in events
            ],
            "reasons": ["Missing GOOGLE_CALENDAR_ACCESS_TOKEN."],
            "suggested_next_action": "Set GOOGLE_CALENDAR_ACCESS_TOKEN (and optionally GOOGLE_CALENDAR_ID) before syncing to Google Calendar.",
            "provider": "google",
        }

    synced_events: list[dict[str, Any]] = []
    failed_events: list[dict[str, Any]] = []

    for event in events:
        encoded_calendar_id = urllib.parse.quote(calendar_id, safe="")
        url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar_id}/events"
        request = urllib.request.Request(
            url,
            data=json.dumps(_google_event_payload(event)).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            synced_events.append(
                {
                    "event_title": event["event_title"],
                    "event_id": payload.get("id"),
                    "html_link": payload.get("htmlLink"),
                }
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            failed_events.append(
                {
                    "event_title": event["event_title"],
                    "reason": str(exc),
                }
            )

    status = "success"
    if failed_events and synced_events:
        status = "partial"
    elif failed_events and not synced_events:
        status = "failed"

    reasons = [item["reason"] for item in failed_events]
    if status == "success":
        next_action = "Google Calendar sync completed."
    elif status == "partial":
        next_action = "Review the failed items and retry after fixing Google Calendar access or event data."
    else:
        next_action = "Check Google Calendar credentials and network access, then retry."

    return {
        "status": status,
        "synced_events": synced_events,
        "skipped_events": [],
        "failed_events": failed_events,
        "reasons": reasons,
        "suggested_next_action": next_action,
        "provider": "google",
    }


def sync_calendar_events(
    events: list[dict[str, Any]],
    provider: str,
    output_dir: str | None = None,
) -> dict[str, Any]:
    if provider == "ics":
        return export_events_to_ics(events, output_dir=output_dir)
    if provider == "google":
        return sync_events_to_google(events)

    return {
        "status": "failed",
        "synced_events": [],
        "skipped_events": [],
        "failed_events": [],
        "reasons": [f"Unsupported provider: {provider}"],
        "suggested_next_action": "Use provider 'google' or 'ics'.",
        "provider": provider,
    }
