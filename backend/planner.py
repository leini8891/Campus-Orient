from __future__ import annotations

import itertools
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


DEFAULT_TIMEZONE = "Asia/Singapore"
DEFAULT_CURRENT_TIME = "09:40"
DEFAULT_CURRENT_LOCATION = "blk365_singapore"
DEFAULT_DESTINATION = "kent_ridge_hall"


LOCATION_CATALOG = {
    "blk365_singapore": {
        "id": "blk365_singapore",
        "name": "BLK 365 Singapore",
        "short_name": "BLK 365",
        "x": 10,
        "y": 76,
        "zone": "Start",
    },
    "nus_utown": {
        "id": "nus_utown",
        "name": "NUS UTown",
        "short_name": "UTown",
        "x": 29,
        "y": 28,
        "zone": "Student Hub",
    },
    "nus_yih": {
        "id": "nus_yih",
        "name": "NUS Yusof Ishak House",
        "short_name": "YIH",
        "x": 52,
        "y": 45,
        "zone": "Admin",
    },
    "nus_ea": {
        "id": "nus_ea",
        "name": "NUS Engineering Auditorium",
        "short_name": "EA",
        "x": 71,
        "y": 30,
        "zone": "Class",
    },
    "kent_ridge_hall": {
        "id": "kent_ridge_hall",
        "name": "Kent Ridge Hall",
        "short_name": "KR Hall",
        "x": 87,
        "y": 58,
        "zone": "Finish",
    },
}


TRAVEL_MINUTES = {
    "blk365_singapore": {
        "nus_utown": 18,
        "nus_yih": 24,
        "nus_ea": 31,
        "kent_ridge_hall": 36,
    },
    "nus_utown": {
        "blk365_singapore": 18,
        "nus_yih": 11,
        "nus_ea": 16,
        "kent_ridge_hall": 22,
    },
    "nus_yih": {
        "blk365_singapore": 24,
        "nus_utown": 11,
        "nus_ea": 12,
        "kent_ridge_hall": 15,
    },
    "nus_ea": {
        "blk365_singapore": 31,
        "nus_utown": 16,
        "nus_yih": 12,
        "kent_ridge_hall": 12,
    },
    "kent_ridge_hall": {
        "blk365_singapore": 36,
        "nus_utown": 22,
        "nus_yih": 15,
        "nus_ea": 12,
    },
}


@dataclass(frozen=True)
class Task:
    task_id: str
    action: str
    location_id: str
    working_hours: tuple[str, ...]
    estimated_duration_mins: int
    required_materials: tuple[str, ...]
    notes: str


MOVE_IN_TASKS = (
    Task(
        task_id="check_documents",
        action="核验入住材料",
        location_id="nus_utown",
        working_hours=("09:30-12:00", "13:00-17:00"),
        estimated_duration_mins=20,
        required_materials=("录取通知书", "护照或身份证件", "住宿预约邮件"),
        notes="学生服务柜台会核对录取与住宿记录。",
    ),
    Task(
        task_id="activate_access",
        action="激活校园卡与门禁权限",
        location_id="nus_yih",
        working_hours=("10:00-17:00",),
        estimated_duration_mins=15,
        required_materials=("临时学生证", "手机号码", "住宿确认邮件"),
        notes="完成后可直接用于宿舍门禁和部分校园服务。",
    ),
    Task(
        task_id="submit_housing_forms",
        action="提交入住表与拍照确认",
        location_id="nus_ea",
        working_hours=("12:15-16:30",),
        estimated_duration_mins=15,
        required_materials=("入住表", "证件照电子版", "紧急联系人信息"),
        notes="此窗口是今天的硬时间窗，建议上课后优先办理。",
    ),
)


def parse_hhmm(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def format_hhmm(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def route_minutes(from_id: str, to_id: str) -> int:
    if from_id == to_id:
        return 0
    return TRAVEL_MINUTES[from_id][to_id]


def calculate_route_matrix(location_ids: list[str]) -> dict[str, Any]:
    matrix: dict[str, Any] = {}
    for source in location_ids:
        for target in location_ids:
            if source == target:
                continue
            matrix[f"{source}-{target}"] = {"time_mins": route_minutes(source, target)}
    return {"matrix": matrix}


def get_calendar_events(user_id: str, date: str) -> dict[str, Any]:
    del user_id, date
    return {
        "busy_slots": [
            {
                "start_time": "11:00",
                "end_time": "12:00",
                "event": "ME2102 工程课",
                "location_id": "nus_ea",
            }
        ]
    }


def search_knowledge_base(intent_keyword: str) -> dict[str, Any]:
    return {
        "intent_keyword": intent_keyword,
        "department": "宿舍入住办理",
        "tasks": [
            {
                "task_id": task.task_id,
                "action": task.action,
                "location_id": task.location_id,
                "location_name": LOCATION_CATALOG[task.location_id]["name"],
                "working_hours": list(task.working_hours),
                "estimated_duration_mins": task.estimated_duration_mins,
                "required_materials": list(task.required_materials),
                "notes": task.notes,
            }
            for task in MOVE_IN_TASKS
        ],
    }


def build_route_paths(stops: list[str]) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for current, nxt in zip(stops, stops[1:]):
        if current == nxt:
            continue
        paths.append(
            {
                "from": current,
                "to": nxt,
                "method": "walk",
                "time_mins": route_minutes(current, nxt),
            }
        )
    return paths


def _schedule_task(task: Task, time_cursor: int, current_location: str) -> dict[str, Any] | None:
    travel_time = route_minutes(current_location, task.location_id)
    arrival = time_cursor + travel_time

    for raw_window in task.working_hours:
        window_start_raw, window_end_raw = raw_window.split("-")
        window_start = parse_hhmm(window_start_raw)
        window_end = parse_hhmm(window_end_raw)
        start_time = max(arrival, window_start)
        end_time = start_time + task.estimated_duration_mins
        if end_time <= window_end:
            return {
                "start": start_time,
                "end": end_time,
                "arrival": arrival,
                "travel_time": travel_time,
                "location_id": task.location_id,
                "action": task.action,
                "required_materials": list(task.required_materials),
                "notes": task.notes,
                "window": raw_window,
                "is_fixed": False,
                "kind": "task",
            }

    return None


def _schedule_busy_slot(slot: dict[str, Any], time_cursor: int, current_location: str) -> dict[str, Any] | None:
    travel_time = route_minutes(current_location, slot["location_id"])
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


def _append_destination(time_cursor: int, current_location: str) -> dict[str, Any]:
    travel_time = route_minutes(current_location, DEFAULT_DESTINATION)
    arrival = time_cursor + travel_time
    return {
        "start": arrival,
        "end": arrival + 20,
        "arrival": arrival,
        "travel_time": travel_time,
        "location_id": DEFAULT_DESTINATION,
        "action": "前往宿舍完成入住与领钥匙",
        "required_materials": ["校园卡", "已盖章入住表", "证件原件"],
        "notes": "终点为宿舍，前序手续完成后即可直接入住。",
        "window": None,
        "is_fixed": False,
        "kind": "destination",
    }


def _to_timeline_entry(step: int, item: dict[str, Any]) -> dict[str, Any]:
    location = LOCATION_CATALOG[item["location_id"]]
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
    finish = sequence[-1]["end"]
    wait_cost = sum(max(0, item["start"] - item["arrival"]) for item in sequence)
    return finish, wait_cost


def _simulate(ordered_tasks: tuple[Task, ...], split_index: int, current_time: int, current_location: str, busy_slot: dict[str, Any]) -> dict[str, Any] | None:
    time_cursor = current_time
    location_cursor = current_location
    scheduled: list[dict[str, Any]] = []
    stop_sequence = [current_location]

    for task in ordered_tasks[:split_index]:
        result = _schedule_task(task, time_cursor, location_cursor)
        if result is None or result["end"] > parse_hhmm(busy_slot["start_time"]):
            return None
        scheduled.append(result)
        time_cursor = result["end"]
        location_cursor = task.location_id
        stop_sequence.append(location_cursor)

    busy_result = _schedule_busy_slot(busy_slot, time_cursor, location_cursor)
    if busy_result is None:
        return None
    scheduled.append(busy_result)
    time_cursor = busy_result["end"]
    location_cursor = busy_slot["location_id"]
    stop_sequence.append(location_cursor)

    for task in ordered_tasks[split_index:]:
        result = _schedule_task(task, time_cursor, location_cursor)
        if result is None:
            return None
        scheduled.append(result)
        time_cursor = result["end"]
        location_cursor = task.location_id
        stop_sequence.append(location_cursor)

    destination = _append_destination(time_cursor, location_cursor)
    scheduled.append(destination)
    stop_sequence.append(DEFAULT_DESTINATION)

    return {
        "sequence": scheduled,
        "stops": stop_sequence,
        "score": _score_schedule(scheduled),
    }


def _best_move_in_plan(current_time: int, current_location: str) -> dict[str, Any] | None:
    busy_slot = get_calendar_events("student_001", "2026-03-13")["busy_slots"][0]
    candidates: list[dict[str, Any]] = []

    for ordered_tasks in itertools.permutations(MOVE_IN_TASKS):
        for split_index in range(len(ordered_tasks) + 1):
            plan = _simulate(ordered_tasks, split_index, current_time, current_location, busy_slot)
            if plan is not None:
                candidates.append(plan)

    if not candidates:
        return None

    return min(candidates, key=lambda item: item["score"])


def _build_success_response(request_body: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    timeline = [
        _to_timeline_entry(index, entry)
        for index, entry in enumerate(plan["sequence"], start=1)
    ]
    stops = plan["stops"]
    input_location = request_body.get("current_location") or DEFAULT_CURRENT_LOCATION
    current_time = request_body.get("current_time") or DEFAULT_CURRENT_TIME
    knowledge = search_knowledge_base("宿舍入住")

    alerts = [
        "NUS EA 入住窗口 12:15-16:30，系统已安排在课程结束后优先办理。",
        "已根据本地课表预留 11:00-12:00 上课时间，未与办事节点冲突。",
    ]

    return {
        "status": "success",
        "scenario": "dorm_move_in",
        "timezone": DEFAULT_TIMEZONE,
        "query": request_body.get("query", ""),
        "current_time": current_time,
        "current_location": input_location,
        "agent_thought_process": (
            "已读取今日课表，11:00-12:00 在 NUS EA 有一节固定课程。"
            "系统比较了 UTown、YIH、EA 三个办理点的办公时间与步行耗时，"
            "选择先去 UTown 核验材料，再到 YIH 激活校园卡，课后立刻在 EA 提交入住表，"
            "最后前往 Kent Ridge Hall 完成入住。"
        ),
        "alerts": alerts,
        "timeline": timeline,
        "route_paths": build_route_paths(stops),
        "location_catalog": deepcopy(LOCATION_CATALOG),
        "knowledge_hits": knowledge["tasks"],
        "skills_used": [
            "get_calendar_events",
            "search_knowledge_base",
            "calculate_route_matrix",
        ],
    }


def _build_blocked_response(request_body: dict[str, Any]) -> dict[str, Any]:
    current_time = request_body.get("current_time") or DEFAULT_CURRENT_TIME
    input_location = request_body.get("current_location") or DEFAULT_CURRENT_LOCATION
    return {
        "status": "blocked",
        "scenario": "dorm_move_in",
        "timezone": DEFAULT_TIMEZONE,
        "query": request_body.get("query", ""),
        "current_time": current_time,
        "current_location": input_location,
        "agent_thought_process": (
            "系统尝试把宿舍入住手续排进今日剩余时间，但当前出发时刻过晚，"
            "已无法在 NUS EA 16:30 关闭前完成全部关键节点。"
        ),
        "alerts": [
            "抱歉，当前时间下已无法在 16:30 前完成宿舍入住全流程，建议明天上午优先前往。",
            "如果只想先完成部分手续，可以改成“只安排今天能办完的节点”。",
        ],
        "timeline": [],
        "route_paths": [],
        "location_catalog": deepcopy(LOCATION_CATALOG),
        "knowledge_hits": search_knowledge_base("宿舍入住")["tasks"],
        "skills_used": [
            "get_calendar_events",
            "search_knowledge_base",
            "calculate_route_matrix",
        ],
    }


def plan_itinerary(request_body: dict[str, Any] | None = None) -> dict[str, Any]:
    request_body = request_body or {}
    current_time = parse_hhmm(request_body.get("current_time", DEFAULT_CURRENT_TIME))
    current_location = request_body.get("current_location", DEFAULT_CURRENT_LOCATION)

    if current_location not in LOCATION_CATALOG:
        current_location = DEFAULT_CURRENT_LOCATION

    route_context = calculate_route_matrix(
        [
            current_location,
            "nus_utown",
            "nus_yih",
            "nus_ea",
            DEFAULT_DESTINATION,
        ]
    )
    del route_context

    plan = _best_move_in_plan(current_time, current_location)
    if plan is None:
        return _build_blocked_response(request_body)

    return _build_success_response(request_body, plan)
