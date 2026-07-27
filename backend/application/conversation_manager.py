import re
import random
import urllib.parse
from typing import Optional, Tuple
from backend.domain.models import ConversationSession, IntentClassification
from backend.shared.utils import detect_unknown_input


# Small talk lists / match patterns
GREETINGS_RE = r"\b(hi+|hello+|hey+|habari+|jambo+|shikamoo+|mambo+|niaje+|morning+|salamu+)\b"
GOODBYES_RE = r"\b(bye+|goodbye+|see ya|kwaheri+|tutaonana+)\b"
THANKS_RE = r"\b(thank\s*you|thanks|asante+|shukran+|shukrani+)\b"
HOW_ARE_YOU_RE = r"\b(how\s*are\s*you|how\s*is\s*it\s*going|habari\s*yako|u\s*mzima|mambo\s*vipi)\b"
WHO_ARE_YOU_RE = r"\b(who\s*are\s*you|what\s*is\s*your\s*name|jina\s*lako|who\s*is\s*basilica|what\s*is\s*basilica)\b"

# Universal Interceptor Commands
CANCEL_CMD = r"\b(cancel|stop|nevermind|reset|home|ondoka|acha)\b"
RESTART_CMD = r"\b(restart|start\s*over|anza\s*tena)\b"
HELP_CMD = r"\b(help|menu|msaada|orodha)\b"
BACK_CMD = r"\b(back|previous|rudi|nyuma)\b"
REPEAT_CMD = r"\b(repeat|say\s*again|rudia)\b"
CONTINUE_CMD = r"\b(continue|next|endelea|sawa|yes|ndio|sure)\b"

# Emotion markers
EMOTION_GRIEF = [r"\blost my\b", r"\bpassed away\b", r"\bdied\b", r"\bdeath\b", r"\bgrief\b", r"\bmsiba\b"]
EMOTION_ANXIOUS = [r"\bnervous\b", r"\banxious\b", r"\bafraid\b", r"\bscared\b", r"\buoga\b"]
EMOTION_EXCITED = [r"\bexcited\b", r"\bhappy\b", r"\bblessed\b", r"\bjoy\b", r"\bfuraha\b"]
EMOTION_FRUSTRATED = [r"\bfrustrated\b", r"\bangry\b", r"\bannoyed\b", r"\bhaileweki\b", r"\bjam\b"]

# Safeguarding / Emergency / Handoff triggers
HANDOFF_TRIGGERS = [
    r"\bsuicide\b", r"\bhurt myself\b", r"\bkill myself\b", r"\bemergency\b", r"\bdanger\b", 
    r"\babuse\b", r"\bneglect\b", r"\bharassment\b", r"\bdispensation\b", r"\bcanon law\b", 
    r"\bnullity\b", r"\bannulment\b", r"\bbereavement\b", r"\bfuneral\b", r"\bgrief\b"
]


def detect_handoff_trigger(text: str) -> bool:
    """Detects if input touches safeguarding, critical emergencies, or canon law."""
    normalized = text.lower().strip()
    return any(re.search(pat, normalized) for pat in HANDOFF_TRIGGERS)

CONTACT_ROUTING = {
    "bapti": {"role": "Baptism Coordinator", "phone": "+254 700 111 222", "email": "baptism@stjosephruiru.org"},
    "marri": {"role": "Marriage Coordinator", "phone": "+254 700 333 444", "email": "marriage@stjosephruiru.org"},
    "bereav": {"role": "Bereavement & Pastoral Team", "phone": "+254 700 555 666", "email": "pastoral@stjosephruiru.org"},
    "grief": {"role": "Bereavement & Pastoral Team", "phone": "+254 700 555 666", "email": "pastoral@stjosephruiru.org"},
    "safeguard": {"role": "Parish Safeguarding Officer", "phone": "+254 700 777 888", "email": "safeguarding@stjosephruiru.org"},
    "tech": {"role": "Parish Administrator", "phone": "+254 700 999 000", "email": "admin@stjosephruiru.org"},
    "default": {"role": "Parish Office", "phone": "+254 700 123 456", "email": "office@stjosephruiru.org"}
}

def get_context_aware_contact(text: str) -> dict:
    normalized = text.lower().strip()
    for key, contact in CONTACT_ROUTING.items():
        if key in normalized:
            return contact
    return CONTACT_ROUTING["default"]


def detect_emotional_tone(text: str) -> Optional[str]:
    normalized = text.lower().strip()
    if any(re.search(pat, normalized) for pat in EMOTION_GRIEF):
        return "grief"
    if any(re.search(pat, normalized) for pat in EMOTION_ANXIOUS):
        return "anxious"
    if any(re.search(pat, normalized) for pat in EMOTION_EXCITED):
        return "excited"
    if any(re.search(pat, normalized) for pat in EMOTION_FRUSTRATED):
        return "frustrated"
    return None

def generate_calendar_link(title: str, date_range: str, details: str, location: str) -> str:
    """Generates a dynamic web-safe Google Calendar URL link."""
    base_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    params = {
        "text": title,
        "dates": date_range,
        "details": details,
        "location": location
    }
    return f"{base_url}&{urllib.parse.urlencode(params)}"

def normalize_fuzzy_text(text: str) -> str:
    """Cleans up repeated characters and normalizes spelling for conversational fuzzy matches."""
    text = text.lower().strip()
    # Compress repeated letters to handle hiiii, heyyyy, helloooo
    text = re.sub(r"i{2,}", "i", text)
    text = re.sub(r"y{2,}", "y", text)
    text = re.sub(r"o{2,}", "o", text)
    text = re.sub(r"e{2,}", "e", text)
    text = re.sub(r"a{2,}", "a", text)
    return text

def detect_conversational_intent_v2(text: str) -> Optional[str]:
    """Detects small talk intents with fuzzy spellings and Swahili support."""
    normalized = normalize_fuzzy_text(text)
    
    if detect_unknown_input(normalized):
        return None
    
    if re.search(GREETINGS_RE, normalized):

        return "greeting"
    if re.search(GOODBYES_RE, normalized):
        return "goodbye"
    if re.search(THANKS_RE, normalized):
        return "thanks"
    if re.search(HOW_ARE_YOU_RE, normalized):
        return "how_are_you"
    if re.search(WHO_ARE_YOU_RE, normalized):
        return "who_are_you"
    return None

def get_bilingual_personality_response(intent: str, session: ConversationSession, is_swahili: bool) -> str:
    """Returns elegant, randomized personality answers with high-quality bilingual English & Swahili support."""
    if is_swahili:
        if intent == "greeting":
            if session.has_greeted:
                return "Karibu tena! 😊\n\nKuna jambo gine naweza kukusaidia nalo leo?"
            session.has_greeted = True
            return (
                "Bwana awe nanyi! 👋\n\n"
                "Karibu kwenye msaidizi wa parokia ya BASILICA.\n\n"
                "Naweza kukusaidia na:\n"
                "• Ratiba ya Misa 🕒\n"
                "• Kitubio na Sakramenti 🕊️\n"
                "• Michango na Sadaka 💵\n"
                "• Matukio ya Parokia 🎉\n\n"
                "Ungependa kujua nini leo?"
            )
        elif intent == "goodbye":
            return "Kwaheri ya kuonana, na Mungu akulinde na kukubariki sana. 🙏"
        elif intent == "thanks":
            return "Karibu sana! Ni furaha yangu kukusaidia. Mungu akubariki. 😊"
        elif intent == "how_are_you":
            return "Niko salama kabisa, asante kwa kuuliza. Unaendeleaje leo? Naweza kukusaidia na nini leo katika parokia yetu?"
        elif intent == "who_are_you":
            return "Mimi ni BASILICA, msaidizi wako wa digitali hapa Kanisa la Mt. Yosefu Ruiru. Naweza kukusaidia kupata ratiba za misa, sakramenti, na matukio ya parokia."
    else:
        # Standard English responses
        if intent == "greeting":
            if session.has_greeted:
                return "Welcome back! 😊\n\nWhat can I help you with today?"
            session.has_greeted = True
            return (
                "Peace be with you! 👋\n\n"
                "Welcome to BASILICA, your parish assistant.\n\n"
                "How can I help you today?\n\n"
                "You can ask me about:\n"
                "• Mass times\n"
                "• Confession\n"
                "• Baptism\n"
                "• Weddings\n"
                "• Parish events\n"
                "• Donations"
            )
        elif intent == "goodbye":
            return "Goodbye, and God bless you. 🙏 Have a peaceful day."
        elif intent == "thanks":
            return "You're most welcome! Happy to help. 😊"
        elif intent == "how_are_you":
            return "I'm doing well, thank you for asking. 😊 How can I assist you today?"
        elif intent == "who_are_you":
            return "I am BASILICA, your digital parish assistant for St. Joseph's Catholic Church in Ruiru."

    return "How can I help you today?"

def is_goal_initiation(text: str) -> Optional[str]:
    """Strictly evaluates if user intends to trigger a multi-step workflow instead of general inquiries."""
    normalized = text.lower().strip()
    
    # Exclude theological or generic non-action inquiries
    if any(exclude in normalized for exclude in ["where was", "who is", "theology of", "history of", "tell me about", "what is"]):
        return None
        
    # Check strict goal initiation triggers
    if any(trigger in normalized for trigger in ["want to bapti", "how to register for bapti", "how do i register for bapti", "register a bapti"]):
        return "baptism"
    if any(trigger in normalized for trigger in ["i want to donate", "making a contribution", "how to give sadaka", "how do i donate"]):
        return "donation"
        
    return None

def handle_workflow_confirmation(text: str, session: ConversationSession, is_swahili: bool) -> Optional[str]:
    """Manages the workflow confirmation stage before trapping users in active flows."""
    normalized = text.lower().strip()
    
    # 1. Ask for confirmation
    if session.current_goal == "baptism_pending":
        if re.search(CONTINUE_CMD, normalized):
            session.current_goal = "baptism"
            session.goal_step = 1
            return (
                "I would be honored to guide you through preparing for Holy Baptism! 🕊️\n\n"
                "**Step 1: Required Documentation**\n"
                "To begin, we require: \n"
                "• The child's Birth Certificate\n"
                "• Parents' Church Marriage Certificate (if applicable)\n"
                "• A recommendation letter from your Small Christian Community (SCC) / Jumuiya\n\n"
                "Do you have these ready, or would you like to know about our mandatory preparatory classes?"
            )
        elif re.search(CANCEL_CMD, normalized) or "no" in normalized or "hapana" in normalized:
            session.current_goal = None
            return "No problem at all! Let me know if you have any other questions about our parish. 😊"
        else:
            return "Would you like to start the multi-step baptism registration guide now? Please say 'yes' to begin or 'no' to cancel."

    if session.current_goal == "donation_pending":
        if re.search(CONTINUE_CMD, normalized):
            session.current_goal = "donation"
            session.goal_step = 1
            return (
                "Thank you for your generous heart in supporting St. Joseph's Parish! 💖\n\n"
                "Would you like to donate through:\n"
                "1. **M-Pesa** (Mobile Money)\n"
                "2. **Bank Transfer**\n"
                "3. **In-Person** (Parish Office)\n\n"
                "Please tell me your preferred channel."
            )
        elif re.search(CANCEL_CMD, normalized) or "no" in normalized or "hapana" in normalized:
            session.current_goal = None
            return "No problem! Let me know if there's anything else I can assist you with."
        else:
            return "Would you like to proceed with our guided donations assistant? Please say 'yes' to begin or 'no' to cancel."
            
    return None

def handle_global_interceptors(text: str, session: ConversationSession, is_swahili: bool) -> Optional[str]:
    """Applies universal controller operations across all workflow guides (back, cancel, repeat, restart)."""
    normalized = text.lower().strip()
    
    # 1. Intercept cancel / reset commands
    if re.search(CANCEL_CMD, normalized):
        session.current_goal = None
        session.goal_step = 0
        session.goal_stack.clear()
        return "The active guided process has been cancelled. Back to the main menu. How can I help you today? 🙏"
        
    # 2. Intercept restart commands
    if re.search(RESTART_CMD, normalized) and session.current_goal:
        session.goal_step = 1
        return "Starting the guide over from Step 1. Please let me know when you are ready to proceed!"

    # 3. Intercept back command
    if re.search(BACK_CMD, normalized) and session.current_goal:
        if session.goal_step > 1:
            session.goal_step -= 1
            return f"Moving back to the previous step. We are now back at Step {session.goal_step}. Ready to proceed?"
        else:
            return "You are already at the very first step of this guided process."

    # 4. Intercept repeat command
    if re.search(REPEAT_CMD, normalized) and session.current_goal:
        return f"Repeating active Step {session.goal_step} instructions. Please let me know when you are ready to continue."

    return None

def handle_goal_oriented_conversation_v2(text: str, session: ConversationSession, is_swahili: bool) -> Optional[str]:
    """State-machine workflow execution supporting multi-step goal navigation and confirm-states."""
    normalized = text.lower().strip()
    
    # 1. Evaluate Confirmation steps
    if session.current_goal in ["baptism_pending", "donation_pending"]:
        return handle_workflow_confirmation(text, session, is_swahili)

    # 2. Process active Baptism Workflow
    if session.current_goal == "baptism":
        if session.goal_step == 1:
            session.goal_step = 2
            return (
                "Wonderful. **Step 2: Preparatory Classes** 📚\n\n"
                "Mandatory instructions for parents and godparents take place on the **First Saturday** of every month from 9:00 AM in the parish hall.\n\n"
                "Would you like to register for the next upcoming class, or proceed to choosing a Baptism date?"
            )
        elif session.goal_step == 2:
            session.goal_step = 3
            return (
                "Got it. **Step 3: Choosing a Date** 📅\n\n"
                "At St. Joseph's, Baptism is solemnly administered on the **2nd and 4th Sundays** of the month during the 9:00 AM youth Mass.\n\n"
                "Does that schedule fit, or would you like to contact our parish office directly to coordinate a special date?"
            )
        elif session.goal_step == 3:
            session.current_goal = None # Completed
            session.goal_step = 0
            return (
                "**Step 4: Contact & Finalization** 📞\n\n"
                "Please bring your gathered documents to the Parish Office (Mon-Fri, 8 AM - 5 PM) to finalize the booking. "
                "You can reach the parish secretary directly at **+254 700 123 456**.\n\n"
                "May God bless your family as you prepare for this beautiful sacrament!"
            )

    # 3. Process active Donations Workflow
    elif session.current_goal == "donation":
        session.current_goal = None # Completed
        session.goal_step = 0
        if "mpesa" in normalized or "m-pesa" in normalized or "1" in normalized:
            return (
                "💵 **M-Pesa Payment Details**\n\n"
                "• **Paybill Number**: `400200` (Cooperative Bank)\n"
                "• **Account Number**: `St. Joseph` (Specify donation type e.g., sadaka, tithe)\n\n"
                "Simply copy the Paybill and account details using the clipboard button on your screen. Thank you for your support! 🙏"
            )
        elif "bank" in normalized or "transfer" in normalized or "2" in normalized:
            return (
                "🏦 **Bank Account Details**\n\n"
                "• **Bank**: Cooperative Bank of Kenya\n"
                "• **Branch**: Ruiru Branch\n"
                "• **Account Name**: St. Joseph's Catholic Church Ruiru\n"
                "• **Account Number**: `01129092490000`\n\n"
                "May God reward your generosity abundantly!"
            )
        else:
            return (
                "🏢 **In-Person Contributions**\n\n"
                "You are welcome to drop your tithes and donations directly at the parish secretary's office "
                "from Monday to Friday between 8:00 AM and 5:00 PM.\n\n"
                "Thank you for building our sanctuary together!"
            )

    return None


PARISH_GRAPH = {
    "baptism": {
        "coordinator": "Baptism Coordinator (+254 700 111 222)",
        "requirements": "Copy of Birth Certificate, Sponsor Letter",
        "schedule": "First Sunday of every month"
    },
    "marriage": {
        "coordinator": "Marriage Coordinator (+254 700 333 444)",
        "requirements": "Baptism certificates, 6 months preparation class",
        "schedule": "Saturdays by appointment"
    }
}

def query_knowledge_graph(text: str) -> Optional[str]:
    text = text.lower().strip()
    
    # Dynamically overlay published content items over baseline graph
    import os
    import json
    local_graph = dict(PARISH_GRAPH)
    content_file = "admin_content.json"
    if os.path.exists(content_file):
        try:
            with open(content_file, "r") as f:
                items = json.load(f)
                for item in items:
                    if item.get("status") == "Published" and item.get("category") == "sacraments":
                        title = item.get("title", "").lower()
                        data = item.get("content_data", {})
                        service_key = None
                        if "baptism" in title:
                            service_key = "baptism"
                        elif "marriage" in title or "matrimony" in title:
                            service_key = "marriage"
                            
                        if service_key:
                            local_graph[service_key] = {
                                "coordinator": data.get("coordinator", local_graph[service_key].get("coordinator", "")),
                                "requirements": data.get("requirements", local_graph[service_key].get("requirements", "")),
                                "schedule": data.get("schedule", local_graph[service_key].get("schedule", ""))
                            }
        except Exception:
            pass

    for service, nodes in local_graph.items():
        if service in text:
            for attr, value in nodes.items():
                if attr in text:
                    return f"According to our parish directory, the {service} {attr} is: {value}."
    return None

def calculate_trust_score(result_source: str, confidence: float, is_fallback: bool) -> int:
    if is_fallback:
        return 65
    if result_source in ["cache", "context_memory"]:
        return 98
    if result_source == "classifier":
        return int(confidence * 100)
    return 90

def evaluate_response_integrity(answer: str) -> str:
    if "[insert" in answer.lower():
        return answer.replace("[Insert Date]", "this Saturday").replace("[Insert Link]", "the parish portal")
    return answer

