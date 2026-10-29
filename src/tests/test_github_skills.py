"""Verify the advertised activity uses the existing registration flow."""

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


class GitHubSkillsTests(unittest.TestCase):
    def setUp(self):
        self.original = copy.deepcopy(school_app.activities)
        self.client = TestClient(school_app.app)

    def tearDown(self):
        self.client.close()
        school_app.activities.clear()
        school_app.activities.update(self.original)

    def test_activity_is_available_to_signup_page(self):
        response = self.client.get("/activities")
        self.assertEqual(response.status_code, 200)
        activity = response.json()["GitHub Skills"]
        self.assertTrue(activity["description"])
        self.assertTrue(activity["schedule"])
        self.assertGreater(activity["max_participants"], 0)
        self.assertEqual(activity["participants"], [])

    def test_registration_duplicate_and_unregister(self):
        path = "/activities/GitHub%20Skills"
        params = {"email": "student@mergington.edu"}
        self.assertEqual(self.client.post(path + "/signup", params=params).status_code, 200)
        activity = self.client.get("/activities").json()["GitHub Skills"]
        self.assertEqual(activity["participants"], [params["email"]])
        duplicate = self.client.post(path + "/signup", params=params)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.json()["detail"], "Student is already signed up")
        self.assertEqual(self.client.delete(path + "/unregister", params=params).status_code, 200)
        self.assertEqual(self.client.get("/activities").json()["GitHub Skills"]["participants"], [])

    def test_capacity_is_enforced(self):
        activity = school_app.activities["GitHub Skills"]
        activity["participants"] = [
            f"student{i}@mergington.edu" for i in range(activity["max_participants"])
        ]
        before = list(activity["participants"])
        response = self.client.post(
            "/activities/GitHub%20Skills/signup", params={"email": "extra@mergington.edu"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Activity is full")
        self.assertEqual(activity["participants"], before)


if __name__ == "__main__":
    unittest.main()
