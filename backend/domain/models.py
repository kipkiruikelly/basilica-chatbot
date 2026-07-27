from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Message:
    role: str  # "user" or "assistant"
    text: str
    timestamp: float

@dataclass
class ConversationSession:
    session_id: str
    history: List[Message] = field(default_factory=list)
    last_intent: Optional[str] = None
    last_confidence: Optional[float] = None
    has_greeted: bool = False
    conversation_stage: str = "active"
    last_topic: Optional[str] = None
    last_entity: Optional[str] = None
    last_activity: float = 0.0
    follow_up_count: int = 0
    current_goal: Optional[str] = None
    goal_step: int = 0
    metadata: dict = field(default_factory=dict)
    goal_stack: List[dict] = field(default_factory=list)
    user_preferences: dict = field(default_factory=dict)




@dataclass
class IntentClassification:
    intent: Optional[str]
    confidence: float
    answer: str
    is_fallback: bool
    source: str  # "classifier", "cache", "fallback", "memory", "emotion_engine", "state_machine", "clarification_engine"
    document_reference: Optional[str] = None
    gemini_used: bool = False
    context_used: Optional[str] = None


