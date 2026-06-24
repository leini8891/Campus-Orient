from __future__ import annotations

from copy import deepcopy
from datetime import date as date_type, timedelta
from typing import Any

from backend.calendar_sync import build_sync_candidates
from backend.scenario_store import get_all_locations
from backend.skills import calculate_route_matrix, get_calendar_events, search_knowledge_base
from backend.utils import format_hhmm, parse_hhmm


DEFAULT_TIMEZONE = "Asia/Singapore"
DEFAULT_CURRENT_TIME = "09:40"
RECOVERY_SEARCH_DAYS = 3


class PlanningAgent:
    def handle(self, request_body: dict[str, Any] | None = None) -> dict[str, Any]:
        from backend.planner import plan_scenario

        request_body = request_body or {}
        query = (request_body.get("query") or "").strip()
        intent = search_knowledge_base(query, request_body.get("knowledge_uploads"))

        if not intent.get("matched"):
            return self._build_needs_input_response(request_body)

        scenario = intent["scenario"]
        all_locations = get_all_locations()
        current_location = request_body.get("current_location") or scenario["default_current_location"]
        if current_location not in all_locations:
            current_location = scenario["default_current_location"]

        current_time = request_body.get("current_time") or DEFAULT_CURRENT_TIME
        current_date = request_body.get("date") or "2026-03-13"
        calendar_events = get_calendar_events(
            request_body.get("user_id", "student_001"),
            current_date,
            scenario,
            request_body,
        )

        relevant_location_ids = {
            current_location,
            *[task["location_id"] for task in scenario["tasks"]],
            *[slot["location_id"] for slot in calendar_events["busy_slots"]],
        }
        if scenario.get("destination_location"):
            relevant_location_ids.add(scenario["destination_location"])

        route_matrix = calculate_route_matrix(sorted(relevant_location_ids))
        plan_result = plan_scenario(
            scenario=scenario,
            current_time=current_time,
            current_location=current_location,
            busy_slots=calendar_events["busy_slots"],
            route_matrix=route_matrix["matrix"],
        )

        if plan_result["status"] == "success":
            return self._build_success_response(
                request_body=request_body,
                scenario=scenario,
                intent=intent,
                current_location=current_location,
                current_time=current_time,
                current_date=current_date,
                calendar_events=calendar_events,
                route_matrix=route_matrix,
                plan_result=plan_result,
            )

        return self._build_blocked_response(
            request_body=request_body,
            scenario=scenario,
            intent=intent,
            current_location=current_location,
            current_time=current_time,
            current_date=current_date,
            calendar_events=calendar_events,
            route_matrix=route_matrix,
        )

    def _build_needs_input_response(self, request_body: dict[str, Any]) -> dict[str, Any]:
        current_location = request_body.get("current_location") or "blk365_singapore"
        response = {
            "status": "needs_input",
            "scenario": None,
            "scenario_title": "需要更多信息",
            "timezone": DEFAULT_TIMEZONE,
            "query": request_body.get("query", ""),
            "date": request_body.get("date") or "2026-03-13",
            "current_time": request_body.get("current_time") or DEFAULT_CURRENT_TIME,
            "current_location": current_location,
            "start_location": current_location,
            "destination_location": current_location,
            "agent_thought_process": "我还不能确定你要办理的是哪一类校园事务。请在问题里说明业务目标，例如“宿舍入住”“财务处交表”“取快递”。",
            "alerts": [
                "未识别到足够明确的办事意图，暂时无法安全生成路线。",
                "请补充具体业务名称、地点偏好或时间约束。"
            ],
            "timeline": [],
            "route_paths": [],
            "location_catalog": deepcopy(get_all_locations()),
            "knowledge_hits": [],
            "calendar_sync_candidates": [],
            "skills_used": [
                "search_knowledge_base"
            ],
            "agent_trace": [
                {
                    "skill": "search_knowledge_base",
                    "summary": "没有找到足够匹配的办事场景。"
                }
            ]
        }
        response["product_view"] = {
            "experience": "newcomer_move_in",
            "headline": "先选一个常见任务",
            "subheadline": "这版助手先专注于新生入住类问题。选一个常见目标后，我会直接告诉你今天能不能办完。",
            "badge": "等待任务",
            "can_finish_today": None,
            "next_step": None,
            "finish_time": "--:--",
            "finish_note": "还没有今天的办理结果。",
            "deadline_title": "先说明你要办什么",
            "constraint_note": "例如“我今天要办理宿舍入住，请帮我规划线路”。",
            "material_status": {
                "required": [],
                "available": self._available_materials(request_body),
                "ready": [],
                "missing": [],
                "has_selection": bool(self._available_materials(request_body)),
                "completion_label": "待确认",
            },
            "recovery_plan": None,
        }
        return response

    def _build_success_response(
        self,
        request_body: dict[str, Any],
        scenario: dict[str, Any],
        intent: dict[str, Any],
        current_location: str,
        current_time: str,
        current_date: str,
        calendar_events: dict[str, Any],
        route_matrix: dict[str, Any],
        plan_result: dict[str, Any],
    ) -> dict[str, Any]:
        matched_keywords = intent.get("matched_keywords", [])
        busy_descriptions = [
            f"{slot['start_time']}-{slot['end_time']} 在 {slot['location_id']} 有 {slot['event']}"
            for slot in calendar_events["busy_slots"]
        ]
        annotated_timeline = self._annotate_timeline_materials(
            request_body=request_body,
            timeline=plan_result["timeline"],
        )
        ordered_actions = " -> ".join(item["action"] for item in annotated_timeline)
        alerts = list(scenario.get("success_alerts", []))
        if calendar_events["busy_slots"]:
            alerts.append("已预留固定课表时间，规划结果不会与这些日程冲突。")
        else:
            alerts.append("未读取到固定课表，本次规划仅按办事时间窗与路径耗时计算。")
        evidence_titles = "；".join(item["snippet"] for item in intent.get("documents", [])[:2])

        response = {
            "status": "success",
            "scenario": scenario["id"],
            "scenario_title": scenario["title"],
            "timezone": DEFAULT_TIMEZONE,
            "query": request_body.get("query", ""),
            "date": current_date,
            "current_time": current_time,
            "current_location": current_location,
            "start_location": current_location,
            "destination_location": plan_result["destination_location"],
            "agent_thought_process": (
                f"已识别办事意图“{scenario['title']}”，匹配关键词：{', '.join(matched_keywords) or '无显式关键词'}。"
                f"固定日程：{'；'.join(busy_descriptions) if busy_descriptions else '无'}。"
                f"知识库证据：{evidence_titles or '已命中对应办事文档'}。"
                f"Agent 先调用知识库提取任务节点，再根据路线矩阵与时间窗求解最早可行序列：{ordered_actions}。"
            ),
            "alerts": alerts,
            "timeline": annotated_timeline,
            "route_paths": plan_result["route_paths"],
            "location_catalog": deepcopy(plan_result["location_catalog"]),
            "knowledge_hits": intent.get("documents", []),
            "calendar_sync_candidates": [],
            "skills_used": [
                "search_knowledge_base",
                "get_calendar_events",
                "calculate_route_matrix",
                "plan_scenario"
            ],
            "agent_trace": [
                {
                    "skill": "search_knowledge_base",
                    "summary": f"命中场景 {scenario['id']}，置信度 {intent['confidence']}。"
                },
                {
                    "skill": "get_calendar_events",
                    "summary": f"读取到 {len(calendar_events['busy_slots'])} 个固定日程。"
                },
                {
                    "skill": "calculate_route_matrix",
                    "summary": f"为 {len(plan_result['location_catalog'])} 个地点生成步行时间矩阵。"
                },
                {
                    "skill": "plan_scenario",
                    "summary": f"找到可行方案，共 {len(plan_result['timeline'])} 个时间节点。"
                }
            ],
            "route_matrix": route_matrix
        }
        response["calendar_sync_candidates"] = build_sync_candidates(response)
        response["product_view"] = self._build_success_product_view(
            scenario=scenario,
            request_body=request_body,
            current_location=current_location,
            current_time=current_time,
            calendar_events=calendar_events,
            timeline=annotated_timeline,
            alerts=alerts,
        )
        return response

    def _build_blocked_response(
        self,
        request_body: dict[str, Any],
        scenario: dict[str, Any],
        intent: dict[str, Any],
        current_location: str,
        current_time: str,
        current_date: str,
        calendar_events: dict[str, Any],
        route_matrix: dict[str, Any],
    ) -> dict[str, Any]:
        recovery_plan = self._suggest_recovery_plan(
            request_body=request_body,
            scenario=scenario,
            current_location=current_location,
        )
        response = {
            "status": "blocked",
            "scenario": scenario["id"],
            "scenario_title": scenario["title"],
            "timezone": DEFAULT_TIMEZONE,
            "query": request_body.get("query", ""),
            "date": current_date,
            "current_time": current_time,
            "current_location": current_location,
            "start_location": current_location,
            "destination_location": scenario.get("destination_location") or current_location,
            "agent_thought_process": (
                f"已识别办事意图“{scenario['title']}”，但根据当前出发时间、固定日程和部门时间窗，"
                "Agent 未找到完整可行解。"
            ),
            "alerts": list(scenario.get("blocked_alerts", [])),
            "timeline": [],
            "route_paths": [],
            "location_catalog": deepcopy(get_all_locations()),
            "knowledge_hits": intent.get("documents", []),
            "calendar_sync_candidates": [],
            "skills_used": [
                "search_knowledge_base",
                "get_calendar_events",
                "calculate_route_matrix",
                "plan_scenario"
            ],
            "agent_trace": [
                {
                    "skill": "search_knowledge_base",
                    "summary": f"命中场景 {scenario['id']}，置信度 {intent['confidence']}。"
                },
                {
                    "skill": "get_calendar_events",
                    "summary": f"读取到 {len(calendar_events['busy_slots'])} 个固定日程。"
                },
                {
                    "skill": "calculate_route_matrix",
                    "summary": "已生成相关地点步行矩阵。"
                },
                {
                    "skill": "plan_scenario",
                    "summary": "没有找到满足全部硬时间窗的完整路线。"
                }
            ],
            "route_matrix": route_matrix
        }
        response["product_view"] = self._build_blocked_product_view(
            scenario=scenario,
            request_body=request_body,
            current_location=current_location,
            current_time=current_time,
            alerts=response["alerts"],
            recovery_plan=recovery_plan,
        )
        return response

    def _available_materials(self, request_body: dict[str, Any]) -> list[str]:
        values = request_body.get("available_materials") or []
        if not isinstance(values, list):
            return []
        available: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                continue
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            available.append(normalized)
        return available

    def _ordered_unique(self, values: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    def _required_materials(
        self,
        scenario: dict[str, Any],
        timeline: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        materials: list[str] = []
        if timeline:
            for item in timeline:
                if item.get("is_fixed"):
                    continue
                materials.extend(item.get("materials", []))
            return self._ordered_unique(materials)

        for task in scenario.get("tasks", []):
            materials.extend(task.get("required_materials", []))
        materials.extend(scenario.get("destination_materials", []))
        return self._ordered_unique(materials)

    def _build_material_status(
        self,
        request_body: dict[str, Any],
        scenario: dict[str, Any],
        timeline: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        required = self._required_materials(scenario, timeline=timeline)
        available = self._available_materials(request_body)
        ready = [item for item in required if item in available]
        missing = [item for item in required if item not in available]
        has_selection = bool(available)
        if has_selection:
            completion_label = f"{len(ready)}/{len(required) or 0} 已确认"
        else:
            completion_label = "待确认"
        return {
            "required": required,
            "available": available,
            "ready": ready,
            "missing": missing,
            "has_selection": has_selection,
            "completion_label": completion_label,
        }

    def _annotate_timeline_materials(
        self,
        request_body: dict[str, Any],
        timeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        available = set(self._available_materials(request_body))
        has_selection = bool(available)
        annotated: list[dict[str, Any]] = []

        for item in timeline:
            entry = deepcopy(item)
            required = list(item.get("materials", []))
            if item.get("is_fixed"):
                entry["ready_materials"] = []
                entry["missing_materials"] = []
                entry["material_status_label"] = "固定安排"
                entry["material_status_tone"] = "fixed"
            elif not required:
                entry["ready_materials"] = []
                entry["missing_materials"] = []
                entry["material_status_label"] = "无需额外材料"
                entry["material_status_tone"] = "ready"
            elif not has_selection:
                entry["ready_materials"] = []
                entry["missing_materials"] = required
                entry["material_status_label"] = f"待确认 {len(required)} 项"
                entry["material_status_tone"] = "pending"
            else:
                ready = [material for material in required if material in available]
                missing = [material for material in required if material not in available]
                entry["ready_materials"] = ready
                entry["missing_materials"] = missing
                if missing:
                    entry["material_status_label"] = f"缺 {len(missing)} 项"
                    entry["material_status_tone"] = "missing"
                else:
                    entry["material_status_label"] = "材料齐了"
                    entry["material_status_tone"] = "ready"
            annotated.append(entry)

        return annotated

    def _first_actionable_step(self, timeline: list[dict[str, Any]]) -> dict[str, Any] | None:
        for item in timeline:
            if not item.get("is_fixed"):
                return item
        return timeline[0] if timeline else None

    def _constraint_copy(
        self,
        alerts: list[str],
        next_step: dict[str, Any] | None,
    ) -> tuple[str, str]:
        if next_step and next_step.get("window"):
            _, window_end = next_step["window"].split("-")
            return "先守住这个时间窗", f"建议在 {window_end} 前完成“{next_step['action']}”。"
        if alerts:
            return "今天的关键提醒", alerts[0]
        return "安排依据", "我会优先把硬时间窗和固定日程避开。"

    def _build_success_product_view(
        self,
        scenario: dict[str, Any],
        request_body: dict[str, Any],
        current_location: str,
        current_time: str,
        calendar_events: dict[str, Any],
        timeline: list[dict[str, Any]],
        alerts: list[str],
    ) -> dict[str, Any]:
        locations = get_all_locations()
        next_step = self._first_actionable_step(timeline)
        material_status = self._build_material_status(request_body, scenario, timeline=timeline)
        finish_time = timeline[-1]["end_time"] if timeline else "--:--"
        location_name = locations.get(current_location, {}).get("short_name", current_location)
        headline = "今天来得及办完入住" if scenario["id"] == "dorm_move_in" else f"今天的{scenario['title']}已经排好了"
        subheadline = (
            f"按你 {current_time} 从 {location_name} 出发，预计 {finish_time} 前完成今天的流程。"
        )
        if material_status["missing"] and material_status["has_selection"]:
            subheadline += f" 但你还缺 {len(material_status['missing'])} 项材料，建议先补齐。"
        finish_note = (
            f"共 {len(timeline)} 个节点，已避开 {len(calendar_events['busy_slots'])} 个固定安排。"
            if calendar_events["busy_slots"]
            else f"共 {len(timeline)} 个节点，本次按办事窗口和步行时间计算。"
        )
        if next_step and next_step.get("missing_materials") and material_status["has_selection"]:
            deadline_title = "下一步前先补材料"
            constraint_note = (
                f"“{next_step['action']}”还缺：{'、'.join(next_step['missing_materials'])}。"
            )
        else:
            deadline_title, constraint_note = self._constraint_copy(alerts, next_step)
        return {
            "experience": "newcomer_move_in",
            "headline": headline,
            "subheadline": subheadline,
            "badge": "今天办得完",
            "can_finish_today": True,
            "next_step": next_step,
            "finish_time": finish_time,
            "finish_note": finish_note,
            "deadline_title": deadline_title,
            "constraint_note": constraint_note,
            "material_status": material_status,
            "recovery_plan": None,
        }

    def _build_blocked_product_view(
        self,
        scenario: dict[str, Any],
        request_body: dict[str, Any],
        current_location: str,
        current_time: str,
        alerts: list[str],
        recovery_plan: dict[str, Any] | None,
    ) -> dict[str, Any]:
        material_status = self._build_material_status(request_body, scenario)
        locations = get_all_locations()
        location_name = locations.get(current_location, {}).get("short_name", current_location)
        if recovery_plan:
            subheadline = (
                f"按你 {current_time} 从 {location_name} 出发，今天大概率赶不上关键窗口。"
                f" 更稳的方案是 {recovery_plan['date']} {recovery_plan['display_start_time']} 再开始。"
            )
            next_step = self._first_actionable_step(recovery_plan["timeline_preview"]) if recovery_plan["timeline_preview"] else None
            finish_time = recovery_plan["finish_time"]
            finish_note = "这是下一套更稳的开始时间，方便你直接改计划。"
        else:
            subheadline = f"按你 {current_time} 从 {location_name} 出发，今天已经很难赶上所有硬时间窗。"
            next_step = None
            finish_time = "--:--"
            finish_note = "暂时没找到下一套足够稳的替代方案。"
        headline = "今天大概率办不完入住" if scenario["id"] == "dorm_move_in" else f"今天来不及完成{scenario['title']}"
        return {
            "experience": "newcomer_move_in",
            "headline": headline,
            "subheadline": subheadline,
            "badge": "建议改期",
            "can_finish_today": False,
            "next_step": next_step,
            "finish_time": finish_time,
            "finish_note": finish_note,
            "deadline_title": "为什么今天不行",
            "constraint_note": alerts[0] if alerts else "当前时间与窗口冲突，没法完整走通。",
            "material_status": material_status,
            "recovery_plan": recovery_plan,
        }

    def _candidate_recovery_times(self, scenario: dict[str, Any]) -> list[str]:
        starts = [
            parse_hhmm(window.split("-")[0])
            for task in scenario.get("tasks", [])
            for window in task.get("working_hours", [])
        ]
        earliest = min(starts) if starts else parse_hhmm(DEFAULT_CURRENT_TIME)
        search_start = max(parse_hhmm("08:00"), earliest - 60)
        search_end = min(parse_hhmm("12:00"), earliest + 120)
        return [format_hhmm(value) for value in range(search_start, search_end + 1, 15)]

    def _parse_iso_date(self, raw_value: str) -> date_type | None:
        try:
            return date_type.fromisoformat(raw_value)
        except ValueError:
            return None

    def _suggest_recovery_plan(
        self,
        request_body: dict[str, Any],
        scenario: dict[str, Any],
        current_location: str,
    ) -> dict[str, Any] | None:
        from backend.planner import plan_scenario

        current_date = self._parse_iso_date(request_body.get("date") or "2026-03-13")
        if current_date is None:
            return None

        user_id = request_body.get("user_id", "student_001")
        locations = get_all_locations()
        current_location_name = locations.get(current_location, {}).get("name", current_location)

        for day_offset in range(1, RECOVERY_SEARCH_DAYS + 1):
            candidate_date = (current_date + timedelta(days=day_offset)).isoformat()
            recovery_request = dict(request_body)
            recovery_request["date"] = candidate_date
            calendar_events = get_calendar_events(user_id, candidate_date, scenario, recovery_request)
            relevant_location_ids = {
                current_location,
                *[task["location_id"] for task in scenario["tasks"]],
                *[slot["location_id"] for slot in calendar_events["busy_slots"]],
            }
            if scenario.get("destination_location"):
                relevant_location_ids.add(scenario["destination_location"])

            route_matrix = calculate_route_matrix(sorted(relevant_location_ids))
            for candidate_time in self._candidate_recovery_times(scenario):
                plan_result = plan_scenario(
                    scenario=scenario,
                    current_time=candidate_time,
                    current_location=current_location,
                    busy_slots=calendar_events["busy_slots"],
                    route_matrix=route_matrix["matrix"],
                )
                if plan_result["status"] != "success":
                    continue

                timeline = self._annotate_timeline_materials(
                    request_body=request_body,
                    timeline=plan_result["timeline"],
                )
                first_step = self._first_actionable_step(timeline)
                if first_step is None:
                    continue

                opening_step = timeline[0]
                if opening_step.get("is_fixed"):
                    display_start_time = opening_step["time_est"]
                    summary = (
                        f"先预留 {opening_step['time_est']}-{opening_step['end_time']} 的固定安排“{opening_step['action']}”，"
                        f"再在 {first_step['time_est']} 去 {first_step['location_name']} 办理“{first_step['action']}”，"
                        f"预计 {timeline[-1]['end_time']} 前走完整条流程。"
                    )
                else:
                    display_start_time = candidate_time
                    summary = (
                        f"{candidate_time} 从 {current_location_name} 出发，"
                        f"先去 {first_step['location_name']} 办理“{first_step['action']}”，"
                        f"预计 {timeline[-1]['end_time']} 前走完整条流程。"
                    )

                return {
                    "date": candidate_date,
                    "start_time": candidate_time,
                    "display_start_time": display_start_time,
                    "headline": f"建议 {candidate_date} {display_start_time} 重新开始",
                    "summary": summary,
                    "first_action": first_step["action"],
                    "first_action_time": first_step["time_est"],
                    "first_location_name": first_step["location_name"],
                    "first_end_time": first_step["end_time"],
                    "finish_time": timeline[-1]["end_time"],
                    "timeline_preview": timeline[:4],
                }

        return None
