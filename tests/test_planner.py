import unittest

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
        self.assertEqual(len(response["timeline"]), 5)
        self.assertTrue(any(item["is_fixed"] for item in response["timeline"]))
        self.assertEqual(response["timeline"][-1]["location_id"], "kent_ridge_hall")

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


if __name__ == "__main__":
    unittest.main()
