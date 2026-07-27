import unittest
import time
import os
import json
from backend.domain.models import ConversationSession, Message
from backend.shared.utils import clean_text, detect_language_and_enrich
from backend.infrastructure.cache import OrderedDictLRUCache
from backend.infrastructure.session import InMemorySessionManager
from backend.application.assistant import BasilicaAssistant
from backend.domain.interfaces import IDatabaseService, IAIService

class MockDatabaseService(IDatabaseService):
    def get_answer(self, intent_id: str) -> str:
        if intent_id == "mass_times":
            return "Sunday Mass: 7 AM, 9 AM, 11 AM."
        elif intent_id == "confession":
            return "Confession is available every Saturday from 3:00 PM."
        elif intent_id == "donations":
            return "Parish donations support our local ministries."
        return "Local Mock Answer"
    def save_answer(self, intent_id: str, text: str) -> bool:
        return True

class MockAIService(IAIService):
    def classify_intent(self, text: str) -> tuple[str, float]:
        if "mass" in text or "misa" in text:
            return "mass_times", 0.95
        elif "confession" in text or "reconciliation" in text:
            return "confession", 0.95
        elif "donate" in text or "sadaka" in text:
            return "donations", 0.95
        return "general_faq", 0.35
    def generate_fallback_response(self, question: str, session=None) -> str:
        return "Generative Fallback Mock Answer"

class TestBasilicaCore(unittest.TestCase):
    def test_text_cleaning(self):
        self.assertEqual(clean_text("  MASS times! "), "mass times")
        self.assertEqual(clean_text("confesion??"), "confesion?")

    def test_swahili_enrichment(self):
        res = detect_language_and_enrich("misa ya jumapili")
        self.assertTrue(res["is_swahili"])
        self.assertIn("mass times", res["text"])

    def test_cache_service(self):
        cache = OrderedDictLRUCache(capacity=2)
        cache.set("key1", "val1", expiration_seconds=10)
        cache.set("key2", "val2", expiration_seconds=10)
        self.assertEqual(cache.get("key1"), "val1")
        
        # Trigger eviction
        cache.set("key3", "val3", expiration_seconds=10)
        self.assertIsNone(cache.get("key2")) # evicted (LRU)

    def test_session_manager(self):
        sm = InMemorySessionManager(session_ttl_seconds=2)
        session = sm.get_session("test_sess")
        self.assertEqual(session.session_id, "test_sess")
        
        session.last_intent = "mass_times"
        sm.save_session(session)
        
        retrieved = sm.get_session("test_sess")
        self.assertEqual(retrieved.last_intent, "mass_times")

    def test_assistant_orchestration(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        # Test standard match
        res = assistant.process_question("when is mass", "sess_1")
        self.assertEqual(res.intent, "mass_times")
        self.assertFalse(res.is_fallback)
        self.assertEqual(res.answer, "Sunday Mass: 7 AM, 9 AM, 11 AM.")
        
        # Test contextual resolution on follow-up
        res_follow = assistant.process_question("when is it?", "sess_1")
        self.assertEqual(res_follow.intent, "mass_times")
        self.assertEqual(res_follow.source, "context_memory")

    def test_conversational_manager_v2(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        # 1. Test First Greeting with elongation "hiiiii"
        res1 = assistant.process_question("hiiiii", "session_conv")
        self.assertEqual(res1.intent, "greeting")
        self.assertIn("Welcome to BASILICA", res1.answer)
        
        # 2. Test Bilingual Swahili Greeting
        res_sw = assistant.process_question("habari yako", "session_conv_swahili")
        self.assertEqual(res_sw.intent, "greeting")
        self.assertIn("Bwana awe nanyi", res_sw.answer)

        # 3. Test Bilingual Swahili Thanks
        res_th = assistant.process_question("asante sana", "session_conv_swahili")
        self.assertEqual(res_th.intent, "thanks")
        self.assertIn("Mungu akubariki", res_th.answer)

    def test_contextual_pronoun_resolution(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        # Ask first question
        assistant.process_question("when is confession?", "session_pronoun")
        
        # Ask short pronoun question
        res = assistant.process_question("where is it?", "session_pronoun")
        self.assertEqual(res.intent, "confession")
        self.assertEqual(res.source, "context_memory")

    def test_emotion_recognition(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        # Test grief detection
        res = assistant.process_question("I lost my mother yesterday", "session_emotion")
        self.assertEqual(res.intent, "emotional_response")
        self.assertIn("sorry for your loss", res.answer)

    def test_clarification_question(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        # Ask ambiguous question with empty history
        res = assistant.process_question("When is it?", "session_ambiguous")
        self.assertEqual(res.intent, "clarification_prompt")
        self.assertIn("Are you referring to Mass times", res.answer)

    def test_goal_oriented_workflow_with_confirmations(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        # 1. Trigger baptism workflow
        res1 = assistant.process_question("I want to baptize my child", "session_goal")
        self.assertEqual(res1.intent, "baptism_pending")
        self.assertIn("guide you through the registration process step by step", res1.answer)
        
        # 2. Confirm to begin
        res2 = assistant.process_question("yes", "session_goal")
        self.assertEqual(res2.intent, "baptism")
        self.assertIn("Step 1: Required Documentation", res2.answer)
        
        # 3. Trigger step 2
        res3 = assistant.process_question("yes I have them", "session_goal")
        self.assertEqual(res3.intent, "baptism")
        self.assertIn("Step 2: Preparatory Classes", res3.answer)

    def test_global_interceptors(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        # Start a baptism confirmation trigger
        assistant.process_question("I want to baptize my child", "session_cancel")
        
        # Send global cancel command
        res = assistant.process_question("nevermind stop", "session_cancel")
        self.assertEqual(res.intent, "navigation_interceptor")
        self.assertIn("cancelled", res.answer)
        
        # Verify goal state was cleared
        session = sm.get_session("session_cancel")
        self.assertIsNone(session.current_goal)

    def test_interruption_stack(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        # 1. Start baptism workflow
        assistant.process_question("I want to baptize my child", "session_stack")
        assistant.process_question("yes", "session_stack") # Step 1 active
        
        # 2. Ask a completely unrelated FAQ question
        res_faq = assistant.process_question("when is confession?", "session_stack")
        self.assertEqual(res_faq.intent, "confession")
        self.assertIn("Confession is available", res_faq.answer)
        self.assertIn("resume where we left off", res_faq.answer)
        
        # 3. Confirm resumption
        res_resumed = assistant.process_question("continue", "session_stack")
        self.assertEqual(res_resumed.intent, "baptism")
        self.assertIn("resuming your", res_resumed.answer)
        
        # Verify restored step
        session = sm.get_session("session_stack")
        self.assertEqual(session.current_goal, "baptism")
        self.assertEqual(session.goal_step, 1)

    def test_proactive_suggestions_and_multi_calendar(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        res = assistant.process_question("when is confession?", "session_proactive")
        self.assertEqual(res.intent, "confession")
        self.assertIn("Proactive Tip:", res.answer)
        self.assertIn("Google Calendar", res.answer)
        self.assertIn("Outlook Calendar", res.answer)

    def test_safeguarding_human_handoff_context_aware(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        # 1. Test Safeguarding Officer Routing
        res1 = assistant.process_question("This is a child abuse and safeguarding issue", "session_handoff")
        self.assertEqual(res1.intent, "human_handoff")
        self.assertIn("Parish Safeguarding Officer", res1.answer)
        self.assertIn("safeguarding@stjosephruiru.org", res1.answer)
        
        # 2. Test Bereavement Routing
        res2 = assistant.process_question("We need funeral and bereavement help", "session_handoff")
        self.assertEqual(res2.intent, "human_handoff")
        self.assertIn("Bereavement & Pastoral Team", res2.answer)
        self.assertIn("pastoral@stjosephruiru.org", res2.answer)

    def test_operational_analytics_logging(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        audit_path = "/Users/kelvinkipkirui/.gemini/antigravity/brain/9839e950-e872-4710-bdc1-4b7c3b3de3d9/audit_trails.jsonl"
        gap_path = "/Users/kelvinkipkirui/.gemini/antigravity/brain/9839e950-e872-4710-bdc1-4b7c3b3de3d9/knowledge_gaps.jsonl"
        
        if os.path.exists(audit_path):
            os.remove(audit_path)
        if os.path.exists(gap_path):
            os.remove(gap_path)
            
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        assistant.process_question("when is mass", "session_explain_audit")
        self.assertTrue(os.path.exists(audit_path))
        
        with open(audit_path, "r") as f:
            log_line = json.loads(f.readline())
            self.assertEqual(log_line["intent"], "mass_times")
            self.assertEqual(log_line["response_version"], "4.0")
            self.assertIn("trust_score", log_line)
            
        assistant.process_question("where can I buy some ice cream?", "session_gap")
        self.assertTrue(os.path.exists(gap_path))
        with open(gap_path, "r") as f:
            gap_line = json.loads(f.readline())
            self.assertEqual(gap_line["predicted_intent"], "general_faq")
            self.assertTrue(gap_line["confidence"] < 0.5)

    def test_user_consent_preferences(self):
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        # Save preferences
        res1 = assistant.process_question("remember me", "session_pref")
        self.assertEqual(res1.intent, "user_preference_saved")
        self.assertIn("remembered your preferences", res1.answer)
        
        # Verify preferences stored in session
        session = sm.get_session("session_pref")
        self.assertTrue(session.user_preferences["consent_given"])
        self.assertEqual(session.user_preferences["preferred_language"], "en")
        
        # Delete preferences
        res2 = assistant.process_question("forget me", "session_pref")
        self.assertEqual(res2.intent, "user_preference_deleted")
        
        session_cleared = sm.get_session("session_pref")
        self.assertEqual(session_cleared.user_preferences, {})

    def test_knowledge_graph_lookup(self):
        if os.path.exists("admin_content.json"):
            try:
                os.remove("admin_content.json")
            except Exception:
                pass
        db = MockDatabaseService()
        ai = MockAIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)
        
        res = assistant.process_question("baptism coordinator", "session_graph")
        self.assertEqual(res.intent, "knowledge_graph_lookup")
        self.assertIn("Baptism Coordinator", res.answer)
        self.assertIn("parish directory", res.answer)

    def test_unknown_input_mitigation(self):
        from backend.infrastructure.ai_pipeline import AIService
        db = MockDatabaseService()
        ai = AIService()
        sm = InMemorySessionManager()
        cache = OrderedDictLRUCache()
        
        assistant = BasilicaAssistant(db, ai, sm, cache)

        
        # 1. Assert standard greetings still resolve perfectly
        for text in ["hi", "hello", "good morning", "habari", "thank you"]:
            res = assistant.process_question(text, "session_valid")
            self.assertIn(res.intent, ["greeting", "thanks"])
            self.assertNotIn("rephrase", res.answer)
            
        # 2. Assert keyboard smash and gibberish inputs return unknown_input and explain capabilities
        GIBBERISH_INPUTS = [
            "fhqefijqef", "qwerty", "asdfghjk", 
            ";;;;;;;;;", "123456", "...........", 
            "xxxxxxxxx", "   ", "     "
        ]
        for gibberish in GIBBERISH_INPUTS:
            res = assistant.process_question(gibberish, f"session_gibberish_{gibberish[:4]}")
            self.assertEqual(res.intent, "unknown_input")
            self.assertIn("rephrase your question", res.answer)
            self.assertIn("Mass times, sacraments", res.answer)

if __name__ == "__main__":
    unittest.main()

