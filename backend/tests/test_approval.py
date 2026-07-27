import unittest
import json
import os
import time
from backend.run import create_app
from backend.presentation import routes as api_routes
from backend.shared.admin_auth import generate_token

class TestBasilicaApprovalWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reset JSON databases
        for f in ["admin_users.json", "admin_content.json", "admin_versions.json", "admin_notifications.json"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        
        # Fresh seed admin
        api_routes.seed_users()
        
        # Authorize as Super Administrator
        token = generate_token({"id": "u1", "username": "admin", "role": "Super Administrator"})
        self.headers = {"Authorization": f"Bearer {token}"}
        
        # Authorize as Secretary
        sec_token = generate_token({"id": "u3", "username": "sec_mary", "role": "Secretary"})
        self.sec_headers = {"Authorization": f"Bearer {sec_token}"}

    def test_01_complete_approval_lifecycle_and_comments(self):
        # 1. Secretary creates a draft sacrament entry
        payload = {
            "title": "Baptism Sacrament Classes",
            "category": "sacraments",
            "status": "Draft",
            "content_data": {
                "coordinator": "Sister Claire (+254 711 222 333)",
                "requirements": "Parish registration, sponsor letter",
                "schedule": "First Saturday of the month"
            }
        }
        res_create = self.client.post("/api/v1/admin/content", json=payload, headers=self.sec_headers)
        self.assertEqual(res_create.status_code, 201)
        item_id = res_create.json["id"]
        self.assertEqual(res_create.json["status"], "Draft")

        # 2. Secretary submits draft for review
        res_sub = self.client.post(f"/api/v1/admin/content/{item_id}/submit", headers=self.sec_headers)
        self.assertEqual(res_sub.status_code, 200)
        self.assertEqual(res_sub.json["status"], "Pending Review")

        # 3. SuperAdmin reviews and Rejects first, adding commentary
        res_reject = self.client.post(f"/api/v1/admin/content/{item_id}/review", json={
            "action": "Reject",
            "comment": "Incorrect mobile phone code, double-check number."
        }, headers=self.headers)
        self.assertEqual(res_reject.status_code, 200)
        self.assertEqual(res_reject.json["status"], "Draft")
        self.assertTrue(len(res_reject.json["comments"]) > 0)

        # 4. Secretary edits details to correct phone, then resubmits
        payload["content_data"]["coordinator"] = "Sister Claire (+254 711 000 000)"
        payload["status"] = "Draft"
        res_edit = self.client.put(f"/api/v1/admin/content/{item_id}", json=payload, headers=self.sec_headers)
        self.assertEqual(res_edit.status_code, 200)
        
        res_sub2 = self.client.post(f"/api/v1/admin/content/{item_id}/submit", headers=self.sec_headers)
        self.assertEqual(res_sub2.status_code, 200)

        # 5. SuperAdmin reviews and Approves
        res_approve = self.client.post(f"/api/v1/admin/content/{item_id}/review", json={
            "action": "Approve"
        }, headers=self.headers)
        self.assertEqual(res_approve.status_code, 200)
        self.assertEqual(res_approve.json["status"], "Published")  # Auto-published since no scheduled times exist

    def test_02_dynamic_knowledge_graph_sync(self):
        # Trigger query to knowledge graph asking about baptism requirements.
        from backend.application.conversation_manager import query_knowledge_graph
        graph_coord = query_knowledge_graph("tell me about baptism coordinator")
        self.assertIsNotNone(graph_coord)
        self.assertIn("Sister Claire", graph_coord)
        
        graph_reqs = query_knowledge_graph("tell me about baptism requirements")
        self.assertIsNotNone(graph_reqs)
        self.assertIn("sponsor letter", graph_reqs)

    def test_03_preview_sandbox_drafts(self):
        # Create a private draft that is unpublished
        payload = {
            "title": "Confession Advent Schedule Special",
            "category": "confessions",
            "status": "Draft",
            "content_data": {
                "location": "Chapel of Grace",
                "schedule": "Fridays 6:00 PM"
            }
        }
        res = self.client.post("/api/v1/admin/content", json=payload, headers=self.sec_headers)
        self.assertEqual(res.status_code, 201)

        # Query ask without preview mode -> must NOT expose draft
        res_public = self.client.post("/api/v1/ask", json={
            "question": "what is the Advent schedule for confession?"
        })
        # Should fall back or not mention the private draft
        self.assertNotIn("Chapel of Grace", res_public.json.get("answer", ""))

        # Query ask WITH preview_drafts parameter -> must show draft details
        res_preview = self.client.post("/api/v1/ask", json={
            "question": "what is the Confession Advent Schedule Special?",
            "preview_drafts": True
        })
        self.assertEqual(res_preview.status_code, 200)
        self.assertIn("[PREVIEW MODE Sandbox]", res_preview.json["answer"])
        self.assertIn("Chapel of Grace", res_preview.json["answer"])

    def test_04_role_based_access_block(self):
        # A Secretary lacks Approving permission
        res = self.client.post("/api/v1/admin/content/some-id/review", json={
            "action": "Approve"
        }, headers=self.sec_headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("lacks permission", res.json["error"])

if __name__ == "__main__":
    unittest.main()
