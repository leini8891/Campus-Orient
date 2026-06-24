from __future__ import annotations

from typing import Any

from backend.calendar_provider import load_calendar_events
from backend.knowledge_base import parse_uploaded_documents, search_documents
from backend.scenario_store import get_all_locations
from backend.utils import estimate_walk_minutes


def _search_knowledge_base(
    intent_keyword: str,
    uploaded_documents: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    result = search_documents(intent_keyword, extra_documents=uploaded_documents)
    if not result["matched"]:
        return {
            "matched": False,
            "confidence": 0.0,
            "matched_keywords": [],
            "documents": [],
        }

    scenario = result["scenario"]
    return {
        "matched": True,
        "scenario_id": scenario["id"],
        "department": scenario["title"],
        "summary": scenario["summary"],
        "tasks": scenario["tasks"],
        "matched_keywords": result["matched_keywords"],
        "confidence": result["confidence"],
        "documents": result["documents"],
        "scenario": scenario,
    }


def search_knowledge_base(
    intent_keyword: str,
    uploads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    uploaded_documents = parse_uploaded_documents(uploads)
    return _search_knowledge_base(intent_keyword, uploaded_documents)


def get_calendar_events(
    user_id: str,
    date: str,
    scenario: dict[str, Any],
    request_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if request_body and "calendar_override" in request_body:
        return {"busy_slots": list(request_body["calendar_override"])}
    return load_calendar_events(
        user_id=user_id,
        date=date,
        scenario_id=scenario.get("id"),
        calendar_file=request_body.get("calendar_file") if request_body else None,
        uploaded_calendar=request_body.get("calendar_upload") if request_body else None,
        fallback_location_id=request_body.get("current_location") if request_body else None,
    )


def calculate_route_matrix(location_ids: list[str]) -> dict[str, Any]:
    locations = get_all_locations()
    matrix: dict[str, Any] = {}
    for source_id in location_ids:
        for target_id in location_ids:
            if source_id == target_id:
                continue
            matrix[f"{source_id}-{target_id}"] = {
                "time_mins": estimate_walk_minutes(
                    locations[source_id],
                    locations[target_id],
                )
            }
    return {"matrix": matrix}
