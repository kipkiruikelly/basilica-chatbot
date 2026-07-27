import unittest
import json
import os
import time
from backend.run import create_app
from backend.presentation import routes as api_routes
from backend.shared.admin_auth import generate_token

class TestBasilicaAdmin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure standard persistent files are removed/clean for testing
        for f in ["admin_users.json", "admin_content.json", "admin_versions.json"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        
        # Explicitly seed users to guarantee fresh presence
        api_routes.seed_users()
        # Authenticate first via Login -> MFA verification
        res_login = self.client.post("/api/v1/admin/auth/login", json={
            "username": "admin",
            "password": "basilica2026"
        })
        self.assertEqual(res_login.status_code, 200)
        self.assertTrue(res_login.json.get("mfa_required"))
        
        # Verify mock MFA
        res_mfa = self.client.post("/api/v1/admin/auth/mfa/verify", json={
            "user_id": "u1",
            "code": "123456"
        })
        self.assertEqual(res_mfa.status_code, 200)
        self.token = res_mfa.json["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_01_authentication_failure(self):
        res = self.client.post("/api/v1/admin/auth/login", json={
            "username": "admin",
            "password": "wrong_password"
        })
        self.assertEqual(res.status_code, 401)

    def test_02_content_crud_and_versioning(self):
        # 1. Create content draft
        payload = {
            "title": "St. Joseph Evening Misa",
            "category": "mass_schedule",
            "status": "Draft",
            "content_data": {
                "church": "St. Joseph, Ruiru",
                "day": "Saturday",
                "time": "5:30 PM",
                "language": "Swahili"
            }
        }
        res_create = self.client.post("/api/v1/admin/content", json=payload, headers=self.headers)
        self.assertEqual(res_create.status_code, 201)
        item_id = res_create.json["id"]
        self.assertEqual(res_create.json["version"], 1)
        
        # 2. Read content item
        res_read = self.client.get(f"/api/v1/admin/content?category=mass_schedule", headers=self.headers)
        self.assertEqual(res_read.status_code, 200)
        self.assertTrue(any(i["id"] == item_id for i in res_read.json["items"]))

        # 3. Update content item (triggers v2 creation)
        update_payload = {
            "title": "St. Joseph Evening Misa Updated",
            "status": "Published",
            "content_data": {
                "church": "St. Joseph, Ruiru",
                "day": "Saturday",
                "time": "6:00 PM",
                "language": "Bilingual"
            },
            "change_notes": "Moved Mass to 6 PM"
        }
        res_update = self.client.put(f"/api/v1/admin/content/{item_id}", json=update_payload, headers=self.headers)
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.json["version"], 2)
        self.assertEqual(res_update.json["status"], "Published")

        # 4. Read history log
        res_hist = self.client.get(f"/api/v1/admin/content/{item_id}/history", headers=self.headers)
        self.assertEqual(res_hist.status_code, 200)
        self.assertEqual(len(res_hist.json), 2)

        # 5. Rollback to version 1
        res_rollback = self.client.post(f"/api/v1/admin/content/{item_id}/rollback/1", headers=self.headers)
        self.assertEqual(res_rollback.status_code, 200)
        self.assertEqual(res_rollback.json["version"], 3)
        self.assertEqual(res_rollback.json["title"], "St. Joseph Evening Misa")
        self.assertEqual(res_rollback.json["content_data"]["time"], "5:30 PM")

    def test_03_role_based_access_control(self):
        # Create a read-only token
        read_only_token = generate_token({"id": "u2", "username": "clerk", "role": "Read Only"})
        ro_headers = {"Authorization": f"Bearer {read_only_token}"}
        
        # Attempting a write action with Read Only role must return 403 Forbidden
        payload = {
            "title": "Unauthorized Draft",
            "category": "events"
        }
        res = self.client.post("/api/v1/admin/content", json=payload, headers=ro_headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("lacks permission", res.json["error"])

    def test_04_system_analytics_and_gap_views(self):
        # Verify analytics parses successfully without erroring
        res_analytics = self.client.get("/api/v1/admin/analytics", headers=self.headers)
        self.assertEqual(res_analytics.status_code, 200)
        self.assertIn("system_status", res_analytics.json)
        self.assertIn("average_latency", res_analytics.json)
        
        # Verify gaps list
        res_gaps = self.client.get("/api/v1/admin/gaps", headers=self.headers)
        self.assertEqual(res_gaps.status_code, 200)
        self.assertIsInstance(res_gaps.json, list)

    def test_05_user_creation_management(self):
        # Create a new administrator account
        payload = {
            "username": "fr_joseph",
            "password": "secret_father_pwd",
            "role": "Priest"
        }
        res_user = self.client.post("/api/v1/admin/users", json=payload, headers=self.headers)
        self.assertEqual(res_user.status_code, 200)
        self.assertTrue(res_user.json["success"])

        # Check in user list
        res_list = self.client.get("/api/v1/admin/users", headers=self.headers)
        self.assertEqual(res_list.status_code, 200)
        self.assertTrue(any(u["username"] == "fr_joseph" for u in res_list.json))

if __name__ == "__main__":
    unittest.main()
