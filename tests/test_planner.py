import json
import tempfile
import unittest
from unittest.mock import patch

from backend.calendar_sync import sync_calendar_events
from backend.planner import plan_itinerary


class PlannerTests(unittest.TestCase):
    def test_move_in_plan_succeeds(self) -> None:
        response = plan_itinerary(
            {
                "user_id": "student_001",
                "query": "我今天要办理宿舍入住，请帮我规划线路",
                "current_location": "blk365_singapore",
                "current_time": "09:40",
            }
        )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["scenario"], "dorm_move_in")
        self.assertEqual(len(response["timeline"]), 5)
        self.assertTrue(any(item["is_fixed"] for item in response["timeline"]))
        self.assertEqual(response["timeline"][-1]["location_id"], "kent_ridge_hall")
        self.assertEqual(len(response["calendar_sync_candidates"]), 4)
        self.assertEqual(response["product_view"]["badge"], "今天办得完")
        self.assertEqual(response["product_view"]["next_step"]["action"], "核验入住材料")
        self.assertEqual(response["timeline"][0]["material_status_label"], "待确认 3 项")

    def test_finance_query_uses_finance_scenario(self) -> None:
        response = plan_itinerary(
            {
                "user_id": "student_001",
                "query": "下午有两节课，课前帮我规划去财务处交表，顺便去拿个快递。",
                "current_location": "dormitory_a",
                "current_time": "13:00",
            }
        )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["scenario"], "finance_errand")
        self.assertEqual(response["timeline"][0]["location_id"], "express_station")
        self.assertIn("财务交表与取快递", response["agent_thought_process"])
        self.assertEqual(response["timeline"][-1]["location_id"], "finance_office")
        self.assertGreater(len(response["knowledge_hits"]), 0)

    def test_late_departure_blocks_plan(self) -> None:
        response = plan_itinerary(
            {
                "user_id": "student_001",
                "query": "我今天要办理宿舍入住，请帮我规划线路",
                "current_location": "blk365_singapore",
                "current_time": "15:55",
            }
        )

        self.assertEqual(response["status"], "blocked")
        self.assertEqual(response["timeline"], [])
        self.assertEqual(response["product_view"]["badge"], "建议改期")
        self.assertIsNotNone(response["product_view"]["recovery_plan"])
        self.assertGreater(len(response["product_view"]["recovery_plan"]["timeline_preview"]), 0)

    def test_sync_candidates_can_export_to_ics(self) -> None:
        response = plan_itinerary(
            {
                "user_id": "student_001",
                "query": "我今天要办理宿舍入住，请帮我规划线路",
                "current_location": "blk365_singapore",
                "current_time": "09:40",
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = sync_calendar_events(
                events=response["calendar_sync_candidates"],
                provider="ics",
                output_dir=temp_dir,
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["synced_events"]), 4)
        self.assertTrue(result["export_file"].endswith(".ics"))

    def test_google_sync_without_token_fails_cleanly(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = sync_calendar_events(
                events=[
                    {
                        "event_title": "测试同步",
                        "date": "2026-03-13",
                        "start_time": "10:00",
                        "end_time": "10:30",
                        "timezone": "Asia/Singapore",
                    }
                ],
                provider="google",
            )

        self.assertEqual(result["status"], "failed")
        self.assertIn("GOOGLE_CALENDAR_ACCESS_TOKEN", result["reasons"][0])

    def test_material_checklist_reports_missing_items(self) -> None:
        response = plan_itinerary(
            {
                "user_id": "student_001",
                "query": "我今天要办理宿舍入住，请帮我规划线路",
                "current_location": "blk365_singapore",
                "current_time": "09:40",
                "available_materials": [
                    "录取通知书",
                    "护照或身份证件",
                    "住宿预约邮件",
                ],
            }
        )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["product_view"]["material_status"]["ready"][0], "录取通知书")
        self.assertIn("临时学生证", response["product_view"]["material_status"]["missing"])
        self.assertEqual(response["timeline"][0]["material_status_label"], "材料齐了")
        self.assertEqual(response["timeline"][1]["material_status_label"], "缺 3 项")

    def test_unknown_query_requests_more_detail(self) -> None:
        response = plan_itinerary(
            {
                "user_id": "student_001",
                "query": "帮我规划一下今天的事",
                "current_location": "blk365_singapore",
                "current_time": "09:40",
            }
        )

        self.assertEqual(response["status"], "needs_input")
        self.assertEqual(response["timeline"], [])
        self.assertEqual(response["product_view"]["badge"], "等待任务")

    def test_calendar_override_can_block_plan(self) -> None:
        response = plan_itinerary(
            {
                "user_id": "student_001",
                "query": "下午有两节课，课前帮我规划去财务处交表，顺便去拿个快递。",
                "current_location": "dormitory_a",
                "current_time": "13:00",
                "calendar_override": [
                    {
                        "start_time": "13:05",
                        "end_time": "17:30",
                        "event": "全天实验课",
                        "location_id": "building_a",
                    }
                ],
            }
        )

        self.assertEqual(response["status"], "blocked")

    def test_uploaded_knowledge_document_can_add_new_intent(self) -> None:
        uploaded_document = {
            "id": "student_card_reissue",
            "title": "学生证补办",
            "summary": "补办学生证需要先核验身份，再去卡务点制卡。",
            "keywords": ["学生证", "补办", "卡务"],
            "default_current_location": "blk365_singapore",
            "success_alerts": ["学生证补办一般需要先完成身份核验。"],
            "tasks": [
                {
                    "task_id": "verify_identity",
                    "action": "核验身份",
                    "location_id": "nus_utown",
                    "working_hours": ["09:30-17:00"],
                    "estimated_duration_mins": 10,
                    "required_materials": ["护照"],
                    "notes": "先核对个人身份和学生记录。"
                },
                {
                    "task_id": "reissue_card",
                    "action": "补办学生证",
                    "location_id": "nus_yih",
                    "working_hours": ["10:00-16:00"],
                    "estimated_duration_mins": 15,
                    "required_materials": ["证件照", "学生编号"],
                    "notes": "卡务点现场补卡。"
                }
            ],
            "evidence_snippets": [
                "补办学生证前需要先完成身份核验。",
                "卡务点在工作时间内可受理补卡。"
            ]
        }

        response = plan_itinerary(
            {
                "user_id": "student_001",
                "query": "我今天想补办学生证",
                "current_location": "blk365_singapore",
                "current_time": "09:40",
                "knowledge_uploads": [
                    {
                        "file_name": "student_card_reissue.json",
                        "content": json.dumps(uploaded_document, ensure_ascii=False),
                    }
                ],
            }
        )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["scenario"], "student_card_reissue")
        self.assertEqual(response["timeline"][0]["action"], "核验身份")
        self.assertGreater(len(response["knowledge_hits"]), 0)

    def test_uploaded_ics_calendar_can_block_plan(self) -> None:
        ics_content = """BEGIN:VCALENDAR
X-WR-TIMEZONE:Asia/Singapore
BEGIN:VEVENT
DTSTART:20260313T130500
DTEND:20260313T173000
SUMMARY:全天实验课
X-LOCATION-ID:building_a
END:VEVENT
END:VCALENDAR
"""

        response = plan_itinerary(
            {
                "user_id": "student_001",
                "query": "下午有两节课，课前帮我规划去财务处交表，顺便去拿个快递。",
                "current_location": "dormitory_a",
                "current_time": "13:00",
                "date": "2026-03-13",
                "calendar_upload": {
                    "file_name": "heavy_day.ics",
                    "content": ics_content,
                },
            }
        )

        self.assertEqual(response["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
