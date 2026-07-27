import os
import joblib
from typing import Optional
from backend.domain.models import ConversationSession
from backend.domain.interfaces import IAIService
from backend.config.settings import (
    CONFIDENCE_THRESHOLD,
    FALLBACK_MESSAGE,
    GEMINI_API_KEY,
    GEMINI_MODEL_NAME,
    PARISH_CONTEXT,
)
from backend.infrastructure.logging import log_event

# Try importing google-generativeai to handle dynamic AI fallbacks
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


class AIService(IAIService):
    def __init__(self):
        self.model = None
        self.vectorizer = None
        
        # Load ML models relative to project root
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        model_path = os.path.join(base_dir, "intent_classifier_v1.joblib")
        vectorizer_path = os.path.join(base_dir, "tfidf_vectorizer_v1.joblib")

        try:
            if os.path.exists(model_path) and os.path.exists(vectorizer_path):
                self.model = joblib.load(model_path)
                self.vectorizer = joblib.load(vectorizer_path)
                log_event("ai_model_load_success", {"model_path": model_path})
            else:
                log_event("ai_model_load_missing", {"model_path": model_path, "vectorizer_path": vectorizer_path}, "warning")
        except Exception as e:
            log_event("ai_model_load_error", {"error": str(e)}, "error")

        # Set up Gemini
        self.gemini_enabled = False
        if HAS_GEMINI and GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel(
                    model_name=GEMINI_MODEL_NAME,
                    system_instruction=PARISH_CONTEXT,
                )
                self.gemini_enabled = True
                log_event("gemini_init_success", {"model": GEMINI_MODEL_NAME})
            except Exception as e:
                log_event("gemini_init_error", {"error": str(e)}, "error")
        else:
            if not HAS_GEMINI:
                log_event("gemini_disabled", {"reason": "google-generativeai library not installed"})
            elif not GEMINI_API_KEY:
                log_event("gemini_disabled", {"reason": "GEMINI_API_KEY environment variable not set"})

    def classify_intent(self, text: str) -> tuple[Optional[str], float]:
        if not self.model or not self.vectorizer:
            log_event("ai_classification_bypass", {"info": "Models not loaded, fallback to default"}, "warning")
            return None, 0.0

        try:
            start_time = os.times()[4]
            X = self.vectorizer.transform([text])
            
            # Step 2: Empty vector check (OOD / Unknown text bypasses the classifier)
            if X.nnz == 0:
                log_event("ai_classification_empty_vector", {"text": text})
                return None, 0.0

            probs = self.model.predict_proba(X)[0]
            top_idx = probs.argmax()
            predicted_intent = self.model.classes_[top_idx]
            confidence = float(probs[top_idx])
            latency = os.times()[4] - start_time
            
            log_event("ai_classification", {
                "intent": predicted_intent,
                "confidence": round(confidence, 3),
                "latency_seconds": latency
            })
            return predicted_intent, confidence
        except Exception as e:
            log_event("ai_classification_error", {"error": str(e)}, "error")
            return None, 0.0

    def generate_fallback_response(self, question: str, session: Optional[ConversationSession] = None) -> str:
        if not self.gemini_enabled:
            return FALLBACK_MESSAGE

        try:
            start_time = os.times()[4]
            # Construct a conversation context prompt if history exists
            prompt = ""
            if session and session.history:
                prompt += "Previous conversation:\n"
                for msg in session.history[-4:]:  # last 4 messages for token efficiency
                    prompt += f"{msg.role.capitalize()}: {msg.text}\n"
                prompt += "\n"
            
            prompt += f"User's new question: {question}\nAnswer:"
            
            response = self.gemini_model.generate_content(prompt)
            latency = os.times()[4] - start_time
            
            answer_text = response.text.strip()
            log_event("gemini_generation", {
                "prompt_length": len(prompt),
                "response_length": len(answer_text),
                "latency_seconds": latency
            })
            return answer_text
        except Exception as e:
            log_event("gemini_generation_error", {"error": str(e)}, "error")
            return FALLBACK_MESSAGE
