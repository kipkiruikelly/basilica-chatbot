from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from backend.domain.models import ConversationSession, IntentClassification

class IDatabaseService(ABC):
    @abstractmethod
    def get_answer(self, intent_id: str) -> Optional[str]:
        pass

    @abstractmethod
    def save_answer(self, intent_id: str, text: str) -> bool:
        pass


class IAIService(ABC):
    @abstractmethod
    def classify_intent(self, text: str) -> tuple[Optional[str], float]:
        pass

    @abstractmethod
    def generate_fallback_response(self, question: str, session: Optional[ConversationSession] = None) -> str:
        pass


class ISessionManager(ABC):
    @abstractmethod
    def get_session(self, session_id: str) -> ConversationSession:
        pass

    @abstractmethod
    def save_session(self, session: ConversationSession) -> None:
        pass

    @abstractmethod
    def clear_session(self, session_id: str) -> None:
        pass


class ICacheService(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, expiration_seconds: int = 3600) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
