import unittest
import os
import json
import time
from backend.run import create_app

class TestBasilicaIAM(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        
        # Isolated mock files for IAM testing
        self.users_file = "test_iam_users.json"
        self.profiles_file = "test_iam_profiles.json"
        self.prefs_file = "test_iam_preferences.json"
        self.church_file = "test_iam_church.json"

        # Apply mocks globally within context
        import backend.presentation.routes as routes
        self._orig_users = routes.USERS_FILE
        self._orig_profiles = routes.PROFILES_FILE
        self._orig_prefs = routes.PREFERENCES_FILE
        self._orig_church = routes.CHURCH_FILE

        routes.USERS_FILE = self.users_file
        routes.PROFILES_FILE = self.profiles_file
        routes.PREFERENCES_FILE = self.prefs_file
        routes.CHURCH_FILE = self.church_file

        # Clean setup state
        for f in [self.users_file, self.profiles_file, self.prefs_file, self.church_file]:
            if os.path.exists(f):
                os.remove(f)

    def tearDown(self):
        import backend.presentation.routes as routes
        routes.USERS_FILE = self._orig_users
        routes.PROFILES_FILE = self._orig_profiles
        routes.PREFERENCES_FILE = self._orig_prefs
        routes.CHURCH_FILE = self._orig_church

        for f in [self.users_file, self.profiles_file, self.prefs_file, self.church_file]:
            if os.path.exists(f):
                os.remove(f)

    def test_user_registration_and_login_lockout(self):
        # 1. Register a fresh account
        res = self.client.post("/api/v1/auth/register", json={
            "username": "tester_iam",
            "password": "securepassword2026",
            "email": "tester@basilica.org",
            "first_name": "Kelly",
            "last_name": "Kip"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["role"], "Registered Parishioner")
        token = data["token"]

        # 2. Login successfully
        res_login = self.client.post("/api/v1/auth/login", json={
            "username": "tester_iam",
            "password": "securepassword2026"
        })
        self.assertEqual(res_login.status_code, 200)
        login_data = res_login.get_json()
        self.assertIn("token", login_data)
        self.assertIn("refresh_token", login_data)

        # 3. Simulate failed attempts lockout
        for _ in range(5):
            self.client.post("/api/v1/auth/login", json={
                "username": "tester_iam",
                "password": "wrong_password_copy"
            })
        
        # 6th attempt must block with 403 Account Locked
        res_lock = self.client.post("/api/v1/auth/login", json={
            "username": "tester_iam",
            "password": "securepassword2026"
        })
        self.assertEqual(res_lock.status_code, 403)
        self.assertIn("locked", res_lock.get_json()["error"])

    def test_user_self_profile_queries(self):
        # Register and get access token
        self.client.post("/api/v1/auth/register", json={
            "username": "tester_me",
            "password": "securepassword2026",
            "email": "me@basilica.org"
        })
        res_login = self.client.post("/api/v1/auth/login", json={
            "username": "tester_me",
            "password": "securepassword2026"
        })
        token = res_login.get_json()["token"]

        # Query profile
        res_profile = self.client.get("/api/v1/users/me", headers={
            "Authorization": f"Bearer {token}"
        })
        self.assertEqual(res_profile.status_code, 200)
        p_data = res_profile.get_json()
        self.assertEqual(p_data["username"], "tester_me")
        self.assertEqual(p_data["profile"]["email_address"], "me@basilica.org")

        # Update profile
        res_up = self.client.put("/api/v1/users/me", json={
            "profile": {"phone_number": "+254 700 000 000"},
            "preferences": {"dark_mode": False}
        }, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_up.status_code, 200)

        # Re-query verification
        res_profile2 = self.client.get("/api/v1/users/me", headers={
            "Authorization": f"Bearer {token}"
        })
        self.assertEqual(res_profile2.get_json()["profile"]["phone_number"], "+254 700 000 000")
        self.assertFalse(res_profile2.get_json()["preferences"]["dark_mode"])

if __name__ == "__main__":
    unittest.main()
