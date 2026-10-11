"""Regression tests for activity enrollment limits."""

import copy
import importlib.util
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location(
    "school_app", Path(__file__).resolve().parents[1] / "app.py"
)
school_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(school_app)


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.original = copy.deepcopy(school_app.activities)
        school_app.activities.clear()
        school_app.activities["Test Club"] = {
            "description": "Test activity",
            "schedule": "Test schedule",
            "max_participants": 2,
            "participants": ["first@mergington.edu"],
        }
        self.client = TestClient(school_app.app)

    def tearDown(self):
        self.client.close()
        school_app.activities.clear()
        school_app.activities.update(self.original)

    def signup(self, email):
        return self.client.post(
            "/activities/Test%20Club/signup", params={"email": email}
        )

    def test_last_seat_can_be_filled(self):
        self.assertEqual(self.signup("second@mergington.edu").status_code, 200)
        self.assertEqual(len(school_app.activities["Test Club"]["participants"]), 2)

    def test_full_activity_rejects_without_mutation(self):
        self.signup("second@mergington.edu")
        before = list(school_app.activities["Test Club"]["participants"])
        response = self.signup("third@mergington.edu")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Activity is full")
        self.assertEqual(school_app.activities["Test Club"]["participants"], before)

    def test_over_capacity_activity_rejects_without_mutation(self):
        school_app.activities["Test Club"]["participants"].extend(
            ["second@mergington.edu", "third@mergington.edu"]
        )
        before = list(school_app.activities["Test Club"]["participants"])
        self.assertEqual(self.signup("fourth@mergington.edu").status_code, 400)
        self.assertEqual(school_app.activities["Test Club"]["participants"], before)

    def test_duplicate_keeps_existing_error_even_when_full(self):
        self.signup("second@mergington.edu")
        response = self.signup("first@mergington.edu")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Student is already signed up")

    def test_unknown_activity_returns_404(self):
        response = self.client.post(
            "/activities/Unknown/signup", params={"email": "new@mergington.edu"}
        )
        self.assertEqual(response.status_code, 404)

    def test_unregister_frees_seat_for_new_signup(self):
        self.signup("second@mergington.edu")
        response = self.client.delete(
            "/activities/Test%20Club/unregister",
            params={"email": "first@mergington.edu"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.signup("third@mergington.edu").status_code, 200)
        self.assertEqual(
            school_app.activities["Test Club"]["participants"],
            ["second@mergington.edu", "third@mergington.edu"],
        )


if __name__ == "__main__":
    unittest.main()
