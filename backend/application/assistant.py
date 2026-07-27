import time
import json
import uuid
from typing import Optional
from backend.domain.models import Message, ConversationSession, IntentClassification
from backend.domain.interfaces import IDatabaseService, IAIService, ISessionManager, ICacheService
from backend.config.settings import CONFIDENCE_THRESHOLD, FALLBACK_MESSAGE
from backend.shared.utils import (
    detect_language_and_enrich,
    generate_google_calendar_link,
    generate_outlook_calendar_link,
    generate_ical_content
)
from backend.infrastructure.logging import log_event
from backend.application.conversation_manager import (
    detect_conversational_intent_v2,
    get_bilingual_personality_response,
    detect_emotional_tone,
    is_goal_initiation,
    handle_workflow_confirmation,
    handle_global_interceptors,
    handle_goal_oriented_conversation_v2,
    detect_handoff_trigger,
    get_context_aware_contact,
    query_knowledge_graph,
    calculate_trust_score,
    evaluate_response_integrity
)

def log_audit_trail(record: dict):
    path = "/Users/kelvinkipkirui/.gemini/antigravity/brain/9839e950-e872-4710-bdc1-4b7c3b3de3d9/audit_trails.jsonl"
    try:
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

def log_knowledge_gap(record: dict):
    path = "/Users/kelvinkipkirui/.gemini/antigravity/brain/9839e950-e872-4710-bdc1-4b7c3b3de3d9/knowledge_gaps.jsonl"
    try:
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

class BasilicaAssistant:
    def __init__(
        self,
        db_service: IDatabaseService,
        ai_service: IAIService,
        session_manager: ISessionManager,
        cache_service: ICacheService
    ):
        self.db_service = db_service
        self.ai_service = ai_service
        self.session_manager = session_manager
        self.cache_service = cache_service

    def _is_follow_up(self, cleaned_text: str) -> bool:
        FOLLOW_UP_TRIGGERS = ["when", "where", "it", "they", "who", "them", "how much", "how", "time", "cost", "direction", "location", "there", "that"]
        words = cleaned_text.split()
        if len(words) <= 4:
            return True
        return any(trigger in cleaned_text for trigger in FOLLOW_UP_TRIGGERS)

    def process_question(self, question: str, session_id: str) -> IntentClassification:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        session: ConversationSession = self.session_manager.get_session(session_id)
        
        # 1. Clean and enrich language
        enrichment = detect_language_and_enrich(question)
        cleaned_text = enrichment["text"]
        is_swahili = enrichment["is_swahili"]

        # User Consent Preferences: Remember/Forget Commands
        if cleaned_text in ["remember me", "remember", "hifadhi data"]:
            session.user_preferences["consent_given"] = True
            session.user_preferences["preferred_language"] = "sw" if is_swahili else "en"
            session.user_preferences["last_active"] = time.time()
            self.session_manager.save_session(session)
            
            answer_text = (
                "I have successfully remembered your preferences! You can type 'forget me' at any time to clear them."
                if not is_swahili else
                "Nimehifadhi mapendeleo yako kikamilifu! Unaweza kuandika 'futa data' wakati wowote ili kuyafuta."
            )
            result = IntentClassification(
                intent="user_preference_saved",
                confidence=1.0,
                answer=answer_text,
                is_fallback=False,
                source="preference_manager"
            )
            self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
            return result

        if cleaned_text in ["forget me", "futa data"]:
            session.user_preferences = {}
            self.session_manager.save_session(session)
            answer_text = (
                "I have successfully deleted all your stored preferences."
                if not is_swahili else
                "Nimefuta mapendeleo yako yote yaliyohifadhiwa kikamilifu."
            )
            result = IntentClassification(
                intent="user_preference_deleted",
                confidence=1.0,
                answer=answer_text,
                is_fallback=False,
                source="preference_manager"
            )
            self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
            return result

        # 1.5. Unknown Input Detection Interceptor
        from backend.shared.utils import detect_unknown_input
        
        if detect_unknown_input(cleaned_text):
            answer_text = (
                "I'm sorry, I didn't quite understand that. Could you rephrase your question? "
                "I can help with Mass times, sacraments, parish events, donations, and other parish information."
                if not is_swahili else
                "Samahani, sijaelewa vizuri. Je, unaweza kurudia swali lako? "
                "Naweza kukusaidia kwa masuala ya ratiba ya Misa, sakramenti, matukio ya parokia, michango, na habari zingine za parokia."
            )
            result = IntentClassification(
                intent="unknown_input",
                confidence=1.0,
                answer=answer_text,
                is_fallback=True,
                source="unknown_detector",
                document_reference=None,
                gemini_used=False,
                context_used="unknown_gibberish"
            )
            session.last_activity = time.time()
            self._update_session_history(session, question, answer_text, "unknown_input", 1.0)
            self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
            return result

        # 2. Safeguarding & Critical Context-Aware Human Handoff Escalation Interceptor

        if detect_handoff_trigger(cleaned_text):
            contact = get_context_aware_contact(cleaned_text)
            answer_text = (
                f"I am here to support you, but this concerns a scenario that requires human care and pastoral expertise. "
                f"Please reach out directly to our **{contact['role']}** at **{contact['phone']}** or email **{contact['email']}**. "
                f"If this is an emergency, please contact local emergency services immediately. May God bless and protect you. 🙏"
                if not is_swahili else
                f"Niko hapa kukusaidia, lakini swali hili linahitaji msaada wa kibinadamu na ushauri wa kichungaji. "
                f"Tafadhali wasiliana na **{contact['role']}** wetu moja kwa moja kwa nambari **{contact['phone']}** au barua pepe **{contact['email']}**. "
                f"Ikiwa kuna dharura, wasiliana na huduma za dharura mara moja. Mungu akubariki na kukulinda. 🙏"
            )
            result = IntentClassification(
                intent="human_handoff",
                confidence=1.0,
                answer=answer_text,
                is_fallback=False,
                source="handoff_escalation",
                document_reference="safeguarding_emergency_protocol",
                gemini_used=False,
                context_used="safeguarding_or_emergency"
            )
            session.last_activity = time.time()
            self._update_session_history(session, question, answer_text, "human_handoff", 1.0)
            self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
            return result

        # 3. Global Conversation Interceptors (cancel, stop, back, repeat, restart)
        interceptor_response = handle_global_interceptors(cleaned_text, session, is_swahili)
        if interceptor_response:
            result = IntentClassification(
                intent="navigation_interceptor",
                confidence=1.0,
                answer=interceptor_response,
                is_fallback=False,
                source="navigation_controller",
                document_reference=None,
                gemini_used=False,
                context_used="navigation_command"
            )
            session.last_activity = time.time()
            self._update_session_history(session, question, interceptor_response, "navigation_interceptor", 1.0)
            self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
            return result

        # 4. Interruption Stack Resumption check
        if session.goal_stack and (cleaned_text in ["continue", "yes", "resume", "ndio", "endelea"]):
            popped = session.goal_stack.pop()
            session.current_goal = popped["goal"]
            session.goal_step = popped["step"]
            session.metadata = popped["metadata"]
            
            resumed_text = f"Welcome back to our guided process! We are resuming your **{session.current_goal}** setup at Step {session.goal_step}. Please let me know if you are ready to continue."
            result = IntentClassification(
                intent=session.current_goal,
                confidence=1.0,
                answer=resumed_text,
                is_fallback=False,
                source="state_machine",
                document_reference=None,
                gemini_used=False,
                context_used="stack_resumption"
            )
            session.last_activity = time.time()
            self._update_session_history(session, question, resumed_text, session.current_goal, 1.0)
            self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
            return result

        # Parish Knowledge Graph lookup traversal check
        graph_match = query_knowledge_graph(cleaned_text)
        if graph_match:
            result = IntentClassification(
                intent="knowledge_graph_lookup",
                confidence=1.0,
                answer=graph_match,
                is_fallback=False,
                source="knowledge_graph",
                document_reference="parish_knowledge_graph",
                gemini_used=False,
                context_used="relational_graph"
            )
            session.last_activity = time.time()
            self._update_session_history(session, question, graph_match, "knowledge_graph_lookup", 1.0)
            self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
            return result

        # Early Intent Classification to detect interruptions before goal routing
        is_empty_vector = False
        if hasattr(self.ai_service, "vectorizer") and self.ai_service.vectorizer:
            X_temp = self.ai_service.vectorizer.transform([cleaned_text])
            is_empty_vector = (X_temp.nnz == 0)
            
        if is_empty_vector:
            predicted_intent, confidence = "unknown_input", 1.0
        else:
            predicted_intent, confidence = self.ai_service.classify_intent(cleaned_text)

        # 5. Detect and handle Interruption before executing active workflow
        unrelated_faq = predicted_intent and predicted_intent != session.current_goal and confidence >= 0.85
        if session.current_goal in ["baptism", "donation"] and unrelated_faq:
            session.goal_stack.append({
                "goal": session.current_goal,
                "step": session.goal_step,
                "metadata": session.metadata
            })
            session.current_goal = None
            session.goal_step = 0

        # 6. Goal Trigger & Activation with Pre-Entry Confirmation
        if session.current_goal in ["baptism_pending", "donation_pending", "baptism", "donation"]:
            goal_answer = handle_goal_oriented_conversation_v2(cleaned_text, session, is_swahili)
            if goal_answer:
                result = IntentClassification(
                    intent=session.current_goal,
                    confidence=1.0,
                    answer=goal_answer,
                    is_fallback=False,
                    source="state_machine",
                    document_reference=f"goal_workflow_{session.current_goal}",
                    gemini_used=False,
                    context_used="multi_step_goal"
                )
                session.last_activity = time.time()
                self._update_session_history(session, question, goal_answer, session.current_goal, 1.0)
                self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
                return result
        else:
            new_goal = is_goal_initiation(cleaned_text)
            if new_goal:
                session.current_goal = f"{new_goal}_pending"
                session.goal_step = 0
                confirm_prompt = (
                    "I'd be happy to help you prepare for Holy Baptism. I can guide you through the registration process step by step. Would you like to begin now?"
                    if new_goal == "baptism" else
                    "I'd be happy to help you support our parish. I can guide you through our giving options step by step. Would you like to begin now?"
                )
                result = IntentClassification(
                    intent=session.current_goal,
                    confidence=1.0,
                    answer=confirm_prompt,
                    is_fallback=False,
                    source="state_machine",
                    document_reference=f"goal_confirmation_{new_goal}",
                    gemini_used=False,
                    context_used="workflow_confirmation"
                )
                session.last_activity = time.time()
                self._update_session_history(session, question, confirm_prompt, session.current_goal, 1.0)
                self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
                return result

        # 7. Intercept Conversational Small Talk / Greeting Manager
        conv_intent = detect_conversational_intent_v2(cleaned_text)
        if conv_intent:
            answer_text = get_bilingual_personality_response(conv_intent, session, is_swahili)
            if session.goal_stack:
                answer_text += f"\n\n*We were in the middle of preparing for your baptism registration. Type 'continue' if you'd like to resume where we left off!*"

            result = IntentClassification(
                intent=conv_intent,
                confidence=1.0,
                answer=answer_text,
                is_fallback=False,
                source="personality_engine",
                document_reference=None,
                gemini_used=False,
                context_used="small_talk"
            )
            session.last_activity = time.time()
            self._update_session_history(session, question, answer_text, conv_intent, 1.0)
            self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
            return result

        # 8. Emotion Recognition Layer
        emotion = detect_emotional_tone(cleaned_text)
        if emotion:
            if emotion == "grief":
                answer_text = "I'm sorry for your loss. May they rest in peace. 🙏\n\nIf you are looking for funeral arrangements, bereavement support, or parish prayer requests, please let me know."
            elif emotion == "anxious":
                answer_text = "Please be at peace. It is completely natural to feel nervous, but you are in a safe and welcoming space. How can I help you take your next steps? 😊"
            elif emotion == "excited":
                answer_text = "What a beautiful blessing! We rejoice with you and thank God for this joy in your life. What can I help you coordinate or share? 🎉"
            else:
                answer_text = "I understand and apologize for any frustration. Let's make this right. How can I best guide you or connect you with our parish office? 🙏"
                
            result = IntentClassification(
                intent="emotional_response",
                confidence=1.0,
                answer=answer_text,
                is_fallback=False,
                source="emotion_engine",
                document_reference=None,
                gemini_used=False,
                context_used="emotion_recognized"
            )
            session.last_activity = time.time()
            self._update_session_history(session, question, answer_text, "emotional_response", 1.0)
            self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
            return result
        
        # Check cache
        cache_key = f"q:{session_id}:{cleaned_text}"
        cached_result = self.cache_service.get(cache_key)
        if cached_result:
            log_event("cache_hit", {"question": question, "cache_key": cache_key})
            session.last_activity = time.time()
            self._update_session_history(session, question, cached_result.answer, cached_result.intent, cached_result.confidence)
            self._write_audit(request_id, session_id, start_time, cached_result, cache_hit=True, session=session)
            return cached_result
        
        # 9. Contextual Resolution: Handle follow-up questions
        resolved_intent = predicted_intent
        resolved_confidence = confidence
        is_context_fallback = False
        
        if confidence < CONFIDENCE_THRESHOLD and not session.last_intent:
            if cleaned_text in ["when is it", "when is it?", "where is it", "where is it?"]:
                clarify_answer = "Are you referring to Mass times, confession, or our youth group meetings?"
                result = IntentClassification(
                    intent="clarification_prompt",
                    confidence=0.5,
                    answer=clarify_answer,
                    is_fallback=False,
                    source="clarification_engine",
                    document_reference=None,
                    gemini_used=False,
                    context_used="clarification_prompt"
                )
                session.last_activity = time.time()
                self._update_session_history(session, question, clarify_answer, "clarification_prompt", 0.5)
                self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)
                return result

        NON_CONTENT_INTENTS = [
            "greeting", "goodbye", "thanks", "how_are_you", "who_are_you",
            "unknown_input", "user_preference_saved", "user_preference_deleted",
            "navigation_interceptor", "human_handoff"
        ]
        if confidence < CONFIDENCE_THRESHOLD and session.last_intent and session.last_intent not in NON_CONTENT_INTENTS:
            if self._is_follow_up(cleaned_text):
                resolved_intent = session.last_intent
                resolved_confidence = session.last_confidence * 0.9 if session.last_confidence else CONFIDENCE_THRESHOLD
                is_context_fallback = True
                session.follow_up_count += 1

        # 10. Retrieval & Generation
        answer_text = None
        is_fallback = False
        source = "classifier"
        doc_ref = None
        gemini_used = False
        context_used = "follow_up_context" if is_context_fallback else "direct_query"

        if resolved_intent == "unknown_input":
            answer_text = FALLBACK_MESSAGE
            is_fallback = True
            source = "unknown_detector"
            doc_ref = None
        elif resolved_confidence >= CONFIDENCE_THRESHOLD and resolved_intent:
            db_cache_key = f"intent:{resolved_intent}"
            answer_text = self.cache_service.get(db_cache_key)
            if answer_text:
                source = "context_memory" if is_context_fallback else "cache"
                doc_ref = f"cache_db:{resolved_intent}"
            else:
                answer_text = self.db_service.get_answer(resolved_intent)
                if answer_text:
                    self.cache_service.set(db_cache_key, answer_text, expiration_seconds=600)
                    source = "context_memory" if is_context_fallback else "classifier"
                    doc_ref = f"firestore:{resolved_intent}"
                else:
                    answer_text = FALLBACK_MESSAGE
                    is_fallback = True
                    source = "db_missing_fallback"
            
            # Phase 3: Proactive Suggestions & Multi-Calendar Integrations
            if resolved_intent == "confession":
                google_url = generate_google_calendar_link(
                    "St. Joseph Confession",
                    "20260801T150000/20260801T160000",
                    "Weekly Sacrament of Reconciliation",
                    "Reconciliation Chapel, Ruiru"
                )
                outlook_url = generate_outlook_calendar_link(
                    "St. Joseph Confession",
                    "2026-08-01T15:00:00",
                    "2026-08-01T16:00:00",
                    "Weekly Sacrament of Reconciliation",
                    "Reconciliation Chapel, Ruiru"
                )
                if "*Proactive Tip" not in answer_text:
                    answer_text += "\n\n*Proactive Tip: You may also be interested in our Saturday evening vigil Mass (5:30 PM) or our Eucharistic Adoration schedule.*"
                if "Google Calendar" not in answer_text:
                    answer_text += (
                        f"\n\n📅 **Add Confession to Calendar**:\n"
                        f"• [Google Calendar]({google_url})\n"
                        f"• [Outlook Calendar]({outlook_url})"
                    )
                    
            elif resolved_intent == "donations" and "*Proactive Tip" not in answer_text:
                answer_text += "\n\n*Proactive Tip: You can copy our M-Pesa details instantly using the quick-copy widget above!*"

            session.last_topic = resolved_intent
        else:
            answer_text = self.ai_service.generate_fallback_response(question, session)
            is_fallback = True
            source = "generative_fallback"
            resolved_intent = None
            gemini_used = True
            doc_ref = "gemini_pro"

        # Interruption Push Handling
        if session.goal_stack:
            answer_text += f"\n\n*We were in the middle of preparing for your baptism registration. Type 'continue' or 'yes' if you'd like to resume where we left off!*"

        # Self-Evaluation Verification Loop
        answer_text = evaluate_response_integrity(answer_text)

        result = IntentClassification(
            intent=resolved_intent,
            confidence=round(resolved_confidence, 3),
            answer=answer_text,
            is_fallback=is_fallback,
            source=source,
            document_reference=doc_ref,
            gemini_used=gemini_used,
            context_used=context_used
        )

        # Cache the final response
        NON_CACHED_INTENTS = ["greeting", "goodbye", "thanks", "how_are_you", "who_are_you", "emotional_response", "preview_simulation", "unknown_input"]
        if resolved_intent not in NON_CACHED_INTENTS:
            self.cache_service.set(cache_key, result, expiration_seconds=120)

        # 11. Update session history, write audit, and log knowledge gaps
        session.last_activity = time.time()
        self._update_session_history(session, question, answer_text, resolved_intent, resolved_confidence)
        self._write_audit(request_id, session_id, start_time, result, cache_hit=False, session=session)

        return result

    def _write_audit(self, request_id: str, session_id: str, start_time: float, result: IntentClassification, cache_hit: bool, session: Optional[ConversationSession] = None):
        latency_ms = int((time.time() - start_time) * 1000)
        trust_score = calculate_trust_score(result.source, result.confidence, result.is_fallback)
        
        audit_record = {
            "request_id": request_id,
            "session_id": session_id,
            "timestamp": time.time(),
            "intent": result.intent,
            "confidence": result.confidence,
            "retrieval_method": result.source,
            "document_reference": result.document_reference,
            "context_used": result.context_used,
            "cache_hit": cache_hit,
            "gemini_used": result.gemini_used,
            "latency_ms": latency_ms,
            "trust_score": f"{trust_score}%",
            "response_version": "4.0"
        }
        log_audit_trail(audit_record)

        # Log Knowledge Gaps
        if result.is_fallback or (result.confidence and result.confidence < 0.5):
            gap_record = {
                "question": result.answer[:60], # Clean snippet representing original
                "predicted_intent": result.intent or "general_faq",
                "confidence": result.confidence,
                "gemini_used": result.gemini_used,
                "user_continued": True
            }
            log_knowledge_gap(gap_record)

    def _update_session_history(
        self,
        session: ConversationSession,
        question: str,
        answer: str,
        intent: Optional[str],
        confidence: float
    ) -> None:
        now = time.time()
        session.history.append(Message(role="user", text=question, timestamp=now))
        session.history.append(Message(role="assistant", text=answer, timestamp=now))
        
        if len(session.history) > 20:
            session.history = session.history[-20:]
            
        if intent:
            session.last_intent = intent
            session.last_confidence = confidence
            
        self.session_manager.save_session(session)
        log_event("session_saved", {
            "session_id": session.session_id,
            "has_greeted": session.has_greeted,
            "last_intent": session.last_intent,
            "last_topic": session.last_topic,
            "current_goal": session.current_goal,
            "goal_step": session.goal_step,
            "follow_up_count": session.follow_up_count
        })
