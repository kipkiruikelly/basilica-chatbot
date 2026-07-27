import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional
from backend.domain.interfaces import IDatabaseService
from backend.infrastructure.logging import log_event

class FirestoreService(IDatabaseService):
    def __init__(self):
        self.db = None
        self.local_fallback_data = {}
        
        # Load local fallback answers if Firestore is not available
        try:
            answers_path = os.path.join(os.path.dirname(__file__), "../../answers.json")
            if os.path.exists(answers_path):
                with open(answers_path, "r") as f:
                    self.local_fallback_data = json.load(f)
        except Exception as e:
            log_event("local_fallback_load_error", {"error": str(e)}, "warning")

        # Initialize Firestore
        try:
            if not firebase_admin._apps:
                if os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("K_SERVICE"):
                    firebase_admin.initialize_app(credentials.ApplicationDefault())
                elif os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON"):
                    key_dict = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"])
                    cred = credentials.Certificate(key_dict)
                    firebase_admin.initialize_app(cred)
                elif os.path.exists("serviceAccountKey.json"):
                    cred = credentials.Certificate("serviceAccountKey.json")
                    firebase_admin.initialize_app(cred)
                else:
                    log_event("firebase_init_bypass", {"info": "No credentials found, using local JSON backup"}, "warning")
            
            if firebase_admin._apps:
                self.db = firestore.client()
                log_event("firebase_init_success", {})
        except Exception as e:
            log_event("firebase_init_error", {"error": str(e)}, "error")

    def get_answer(self, intent_id: str) -> Optional[str]:
        if not self.db:
            log_event("firestore_fallback", {"intent_id": intent_id, "source": "local_json"})
            return self.local_fallback_data.get(intent_id)

        try:
            start_time = os.times()[4]
            doc = self.db.collection("answers").document(intent_id).get()
            latency = os.times()[4] - start_time
            
            if doc.exists:
                text = doc.to_dict().get("text")
                log_event("firestore_read", {"intent_id": intent_id, "latency_seconds": latency, "hit": True})
                return text
            else:
                log_event("firestore_read", {"intent_id": intent_id, "latency_seconds": latency, "hit": False}, "warning")
                # Fallback to local json if missing from Firestore
                return self.local_fallback_data.get(intent_id)
        except Exception as e:
            log_event("firestore_read_error", {"intent_id": intent_id, "error": str(e)}, "error")
            return self.local_fallback_data.get(intent_id)

    def save_answer(self, intent_id: str, text: str) -> bool:
        if not self.db:
            self.local_fallback_data[intent_id] = text
            return True
        try:
            self.db.collection("answers").document(intent_id).set({"text": text})
            log_event("firestore_write", {"intent_id": intent_id})
            return True
        except Exception as e:
            log_event("firestore_write_error", {"intent_id": intent_id, "error": str(e)}, "error")
            return False
