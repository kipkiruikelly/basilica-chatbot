import time
import json
import logging
from typing import Dict, Optional, Any
try:
    import redis
except ImportError:
    redis = None

from backend.domain.models import ConversationSession, Message
from backend.domain.interfaces import ISessionManager

logger = logging.getLogger("basilica")

class InMemorySessionManager(ISessionManager):
    def __init__(self, session_ttl_seconds: int = 1800):
        self.sessions: Dict[str, tuple[ConversationSession, float]] = {}
        self.session_ttl_seconds = session_ttl_seconds

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, (_, expiry) in self.sessions.items() if now > expiry]
        for k in expired_keys:
            del self.sessions[k]

    def get_session(self, session_id: str) -> ConversationSession:
        self._cleanup_expired()
        now = time.time()
        if session_id in self.sessions:
            session, _ = self.sessions[session_id]
            # Refresh TTL
            self.sessions[session_id] = (session, now + self.session_ttl_seconds)
            return session
        
        # Create new session
        new_session = ConversationSession(session_id=session_id)
        self.sessions[session_id] = (new_session, now + self.session_ttl_seconds)
        return new_session

    def save_session(self, session: ConversationSession) -> None:
        now = time.time()
        self.sessions[session.session_id] = (session, now + self.session_ttl_seconds)

    def clear_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]


class RedisSessionManager(ISessionManager):
    def __init__(self, redis_url: str = "redis://localhost:6379/0", session_ttl_seconds: int = 1800):
        self.redis_url = redis_url
        self.session_ttl_seconds = session_ttl_seconds
        self.local_fallback = InMemorySessionManager(session_ttl_seconds)
        self.is_redis_active = False
        self.last_recovery_check = 0.0
        self.client: Optional[Any] = None

        if redis is not None:
            try:
                # Direct thin client initialization with connection timeout safety gates
                self.client = redis.Redis.from_url(redis_url, socket_timeout=1.0, socket_connect_timeout=1.0)
                self.client.ping()
                self.is_redis_active = True
                logger.info(f"Connected to Redis distributed session cluster at: {redis_url}")
            except Exception as e:
                logger.warning(f"Redis not available at startup ({e}). Falling back to local in-memory session manager.")
        else:
            logger.warning("redis-py module not installed. Falling back to local in-memory session manager.")

    def _attempt_recovery(self) -> None:
        now = time.time()
        # Rate-limit self-healing ping tests to once every 10 seconds to avoid spamming sockets
        if now - self.last_recovery_check > 10.0:
            self.last_recovery_check = now
            if redis is not None and self.client is not None:
                try:
                    self.client.ping()
                    self.is_redis_active = True
                    logger.info("Redis distributed session service successfully self-healed and recovered. Reconnecting.")
                except Exception:
                    pass

    def _serialize(self, session: ConversationSession) -> str:
        data = {
            "session_id": session.session_id,
            "history": [{"role": m.role, "text": m.text, "timestamp": m.timestamp} for m in session.history],
            "last_intent": session.last_intent,
            "last_confidence": session.last_confidence,
            "has_greeted": session.has_greeted,
            "conversation_stage": session.conversation_stage,
            "last_topic": session.last_topic,
            "last_entity": session.last_entity,
            "last_activity": session.last_activity,
            "follow_up_count": session.follow_up_count,
            "current_goal": session.current_goal,
            "goal_step": session.goal_step,
            "metadata": session.metadata,
            "goal_stack": session.goal_stack,
            "user_preferences": session.user_preferences,
        }
        return json.dumps(data)

    def _deserialize(self, json_str: str) -> ConversationSession:
        data = json.loads(json_str)
        history = [Message(role=m["role"], text=m["text"], timestamp=m["timestamp"]) for m in data.get("history", [])]
        return ConversationSession(
            session_id=data["session_id"],
            history=history,
            last_intent=data.get("last_intent"),
            last_confidence=data.get("last_confidence"),
            has_greeted=data.get("has_greeted", False),
            conversation_stage=data.get("conversation_stage", "active"),
            last_topic=data.get("last_topic"),
            last_entity=data.get("last_entity"),
            last_activity=data.get("last_activity", 0.0),
            follow_up_count=data.get("follow_up_count", 0),
            current_goal=data.get("current_goal"),
            goal_step=data.get("goal_step", 0),
            metadata=data.get("metadata", {}),
            goal_stack=data.get("goal_stack", []),
            user_preferences=data.get("user_preferences", {}),
        )

    def get_session(self, session_id: str) -> ConversationSession:
        if not self.is_redis_active:
            self._attempt_recovery()

        if self.is_redis_active and self.client is not None:
            t0 = time.time()
            try:
                # Query session payload
                key = f"sess:{session_id}"
                val = self.client.get(key)
                
                # SRE Latency logging
                duration = time.time() - t0
                logger.info(f"SRE_METRIC: Session Read | session_id: {session_id} | duration: {duration:.4f}s | success: True | source: Redis")

                if val is not None:
                    session = self._deserialize(val.decode("utf-8"))
                    # Dynamic slide expiration TTL refresh on active operations
                    ttl = session.metadata.get("session_ttl_seconds", self.session_ttl_seconds)
                    self.client.expire(key, int(ttl))
                    return session
                else:
                    # Instantiate fresh session in Redis
                    new_session = ConversationSession(session_id=session_id)
                    ttl = new_session.metadata.get("session_ttl_seconds", self.session_ttl_seconds)
                    self.client.setex(key, int(ttl), self._serialize(new_session))
                    return new_session

            except Exception as e:
                logger.error(f"SRE_ALERT: Redis connection timeout on read. Switching to memory fallback. Error: {e}")
                self.is_redis_active = False

        # Fallback to local memory session provider gracefully
        return self.local_fallback.get_session(session_id)

    def save_session(self, session: ConversationSession) -> None:
        if not self.is_redis_active:
            self._attempt_recovery()

        # Update activity timestamp automatically
        session.last_activity = time.time()

        if self.is_redis_active and self.client is not None:
            t0 = time.time()
            try:
                key = f"sess:{session.session_id}"
                ttl = session.metadata.get("session_ttl_seconds", self.session_ttl_seconds)
                
                # Atomic transaction pipelining
                pipe = self.client.pipeline()
                pipe.setex(key, int(ttl), self._serialize(session))
                pipe.execute()

                duration = time.time() - t0
                logger.info(f"SRE_METRIC: Session Write | session_id: {session.session_id} | duration: {duration:.4f}s | success: True | source: Redis")
                return
            except Exception as e:
                logger.error(f"SRE_ALERT: Redis connection timeout on write. Switching to memory fallback. Error: {e}")
                self.is_redis_active = False

        # Persist locally during fallback outage
        self.local_fallback.save_session(session)

    def clear_session(self, session_id: str) -> None:
        if not self.is_redis_active:
            self._attempt_recovery()

        if self.is_redis_active and self.client is not None:
            try:
                key = f"sess:{session_id}"
                self.client.delete(key)
                return
            except Exception as e:
                logger.error(f"SRE_ALERT: Redis connection timeout on clear. Error: {e}")
                self.is_redis_active = False

        self.local_fallback.clear_session(session_id)
