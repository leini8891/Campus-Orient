from __future__ import annotations

import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.scenario_store import get_all_locations


KB_DIR = Path(__file__).resolve().parent / "data" / "knowledge_base"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+")


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _tokenize(text: str) -> set[str]:
    normalized = _normalize(text)
    return set(TOKEN_PATTERN.findall(normalized))


@lru_cache(maxsize=1)
def _load_documents() -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for path in sorted(KB_DIR.glob("*.json")):
        documents.append(json.loads(path.read_text(encoding="utf-8")))
    return documents


def list_documents() -> list[dict[str, Any]]:
    return [deepcopy(doc) for doc in _load_documents()]


def _coerce_document(candidate: dict[str, Any], fallback_id: str) -> dict[str, Any] | None:
    locations = get_all_locations()
    tasks = candidate.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return None

    normalized_tasks: list[dict[str, Any]] = []
    for index, task in enumerate(tasks, start=1):
        location_id = task.get("location_id")
        if location_id not in locations:
            return None
        normalized_tasks.append(
            {
                "task_id": task.get("task_id", f"{fallback_id}_task_{index}"),
                "action": task.get("action", f"Task {index}"),
                "location_id": location_id,
                "working_hours": list(task.get("working_hours", [])),
                "estimated_duration_mins": int(task.get("estimated_duration_mins", 10)),
                "required_materials": list(task.get("required_materials", [])),
                "notes": task.get("notes", ""),
            }
        )

    destination_location = candidate.get("destination_location")
    if destination_location and destination_location not in locations:
        destination_location = None

    keywords = list(candidate.get("keywords", []))
    title = candidate.get("title", fallback_id.replace("_", " ").title())
    summary = candidate.get("summary", title)
    return {
        "id": candidate.get("id", fallback_id),
        "title": title,
        "summary": summary,
        "keywords": keywords or [title],
        "intent_keywords": list(candidate.get("intent_keywords", [])),
        "default_current_location": candidate.get("default_current_location", "blk365_singapore"),
        "destination_location": destination_location,
        "destination_action": candidate.get("destination_action"),
        "destination_duration_mins": int(candidate.get("destination_duration_mins", 0)),
        "destination_materials": list(candidate.get("destination_materials", [])),
        "destination_notes": candidate.get("destination_notes", ""),
        "success_alerts": list(candidate.get("success_alerts", [])),
        "blocked_alerts": list(candidate.get("blocked_alerts", [])),
        "tasks": normalized_tasks,
        "evidence_snippets": list(candidate.get("evidence_snippets", [])),
    }


def parse_uploaded_documents(uploads: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not uploads:
        return []

    documents: list[dict[str, Any]] = []
    for index, upload in enumerate(uploads, start=1):
        file_name = upload.get("file_name", f"upload_{index}.json")
        suffix = Path(file_name).suffix.lower()
        if suffix != ".json":
            continue

        try:
            parsed = json.loads(upload.get("content", ""))
        except json.JSONDecodeError:
            continue

        candidates = parsed if isinstance(parsed, list) else [parsed]
        for doc_index, candidate in enumerate(candidates, start=1):
            if not isinstance(candidate, dict):
                continue
            fallback_id = f"{Path(file_name).stem}_{doc_index}"
            normalized = _coerce_document(candidate, fallback_id)
            if normalized is not None:
                documents.append(normalized)
    return documents


def search_documents(query: str, extra_documents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    query_tokens = _tokenize(query)
    normalized_query = _normalize(query)
    best_doc: dict[str, Any] | None = None
    best_score = 0.0
    best_keywords: list[str] = []

    documents = [*_load_documents(), *(extra_documents or [])]
    for document in documents:
        matched_keywords = [
            keyword
            for keyword in document.get("keywords", [])
            if _normalize(keyword) in normalized_query
        ]
        document_tokens = _tokenize(" ".join(document.get("keywords", [])))
        token_overlap = len(query_tokens & document_tokens)
        score = len(matched_keywords) * 2 + token_overlap
        if score > best_score:
            best_doc = document
            best_score = float(score)
            best_keywords = matched_keywords

    if best_doc is None or best_score <= 0:
        return {
            "matched": False,
            "confidence": 0.0,
            "matched_keywords": [],
            "documents": [],
        }

    keyword_total = max(1, len(best_doc.get("keywords", [])))
    confidence = min(0.99, 0.25 + (best_score / keyword_total) * 0.8)
    evidence = [
        {
            "scenario_id": best_doc["id"],
            "title": best_doc["title"],
            "snippet": snippet,
        }
        for snippet in best_doc.get("evidence_snippets", [])[:3]
    ]
    return {
        "matched": True,
        "scenario": deepcopy(best_doc),
        "confidence": round(confidence, 2),
        "matched_keywords": best_keywords,
        "documents": evidence,
    }
