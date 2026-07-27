import unittest
import time
import json
from unittest.mock import MagicMock, patch
from backend.domain.models import ConversationSession, Message
from backend.infrastructure.session import RedisSessionManager, InMemorySessionManager

class TestBasilicaSRE(unittest.TestCase):
    def test_in_memory_basic_operations(self):
        manager = InMemorySessionManager(session_ttl_seconds=2)
        sess = manager.get_session("session_basic")
        self.assertEqual(sess.session_id, "session_basic")
        
        sess.last_intent = "confession"
        manager.save_session(sess)
        
        retrieved = manager.get_session("session_basic")
        self.assertEqual(retrieved.last_intent, "confession")
        
        # Test TTL expiration
        time.sleep(2.1)
        expired = manager.get_session("session_basic")
        self.assertIsNone(expired.last_intent)  # Cleared/Recreated as a fresh session

    @patch("redis.Redis")
    def test_redis_session_manager_success_lifecycle(self, mock_redis_class):
        # Setup mock Redis client behavior
        mock_client = MagicMock()
        mock_redis_class.from_url.return_value = mock_client
        
        # Simulated session binary data payload
        stored_data = {
            "session_id": "redis_sess_1",
            "history": [{"role": "user", "text": "hello", "timestamp": 123.0}],
            "last_intent": "greeting",
            "metadata": {"session_ttl_seconds": 3600}
        }
        mock_client.get.return_value = json.dumps(stored_data).encode("utf-8")

        # Instantiate manager
        manager = RedisSessionManager(redis_url="redis://localhost:6379/0", session_ttl_seconds=1800)
        self.assertTrue(manager.is_redis_active)

        # Retrieve session
        session = manager.get_session("redis_sess_1")
        self.assertEqual(session.session_id, "redis_sess_1")
        self.assertEqual(session.last_intent, "greeting")
        self.assertEqual(len(session.history), 1)
        self.assertEqual(session.history[0].role, "user")

        # Verify dynamic sliding TTL expiration refresh was triggered
        mock_client.expire.assert_called_with("sess:redis_sess_1", 3600)

    @patch("redis.Redis")
    def test_redis_failover_and_recovery_loop(self, mock_redis_class):
        mock_client = MagicMock()
        mock_redis_class.from_url.return_value = mock_client
        
        # Define connection failure on save_session
        mock_client.pipeline.side_effect = Exception("Redis timed out!")

        manager = RedisSessionManager(redis_url="redis://localhost:6379/0", session_ttl_seconds=1800)
        self.assertTrue(manager.is_redis_active)

        # Triggers write which catches error, toggles is_redis_active to False, and falls back
        session = ConversationSession(session_id="failover_sess")
        session.last_intent = "mass_times"
        manager.save_session(session)

        self.assertFalse(manager.is_redis_active)

        # Check retrieval reads from memory fallback cleanly
        fallback_session = manager.get_session("failover_sess")
        self.assertEqual(fallback_session.last_intent, "mass_times")

        # Now simulate Redis recovery self-healing ping
        mock_client.ping.return_value = True
        manager.last_recovery_check = 0.0  # Force cooldown reset
        
        # Saving again triggers recovery test, succeeds, and reconnects to Redis!
        mock_client.pipeline.side_effect = None  # Clear connection exception
        manager.save_session(session)
        
        self.assertTrue(manager.is_redis_active)

if __name__ == "__main__":
    unittest.main()
