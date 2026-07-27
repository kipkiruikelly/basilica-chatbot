import re
import urllib.parse


# Vocabulary and synonyms mapper to bridge dialect differences
SWAHILI_KEYWORD_MAP = {
    "misa": "mass times",
    "sadaka": "donations",
    "faini": "donations",
    "utoaji": "donations",
    "michango": "donations",
    "paybill": "donations",
    "ubatizo": "baptism sacraments",
    "kipaimara": "sacraments",
    "komunyo": "sacraments",
    "ndoa": "sacraments",
    "kitubio": "confession schedule",
    "ungama": "confession schedule",
    "matukio": "events",
    "sherehe": "events",
    "mawasiliano": "contact info",
    "simu": "contact info",
    "ramani": "contact info",
    "viongozi": "staff directory",
    "padri": "staff directory",
    "paroko": "staff directory",
    "historia": "parish history",
    "maswali": "general faq",
    "jambo": "greeting",
    "mambo": "greeting",
    "habari": "greeting",
    "salamu": "greeting",
    "asante": "thanks",
    "shukran": "thanks",
    "kwaheri": "goodbye",
    "tutaonana": "goodbye",
    "niaje": "greeting",
}


def clean_text(text: str) -> str:
    """Standard text cleaning pipeline."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s?']", "", text)
    text = re.sub(r"\?+", "?", text)
    text = re.sub(r"\s+", " ", text)
    return text


def detect_language_and_enrich(text: str) -> dict:
    """
    Detects if query contains Swahili keywords or other localized synonyms,
    and returns a structured dict with metadata and normalized/enriched keywords.
    """
    cleaned = clean_text(text)
    words = cleaned.split()
    
    detected_swahili = []
    enriched_terms = []
    
    for word in words:
        if word in SWAHILI_KEYWORD_MAP:
            detected_swahili.append(word)
            enriched_terms.append(SWAHILI_KEYWORD_MAP[word])
            
    is_swahili = len(detected_swahili) > 0
    
    # Simple rule-based spell correction of very common parish typos
    cleaned = re.sub(r"\bconfesion\b", "confession", cleaned)
    cleaned = re.sub(r"\bbaptsim\b", "baptism", cleaned)
    cleaned = re.sub(r"\bmas times\b", "mass times", cleaned)
    cleaned = re.sub(r"\bofice\b", "office", cleaned)
    
    # If Swahili term was mapped to English keyword, inject it subtly to help the TF-IDF
    if enriched_terms:
        cleaned += " " + " ".join(enriched_terms)
        
    return {
        "text": cleaned,
        "is_swahili": is_swahili,
        "detected_terms": detected_swahili
    }


def generate_google_calendar_link(title: str, date_range: str, details: str, location: str) -> str:
    base_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    params = {
        "text": title,
        "dates": date_range,
        "details": details,
        "location": location
    }
    return f"{base_url}&{urllib.parse.urlencode(params)}"


def generate_outlook_calendar_link(title: str, start_dt: str, end_dt: str, details: str, location: str) -> str:
    base_url = "https://outlook.live.com/calendar/0/deeplink/compose?path=/calendar/action/compose&rru=addevent"
    params = {
        "subject": title,
        "startdt": start_dt,
        "enddt": end_dt,
        "body": details,
        "location": location
    }
    return f"{base_url}&{urllib.parse.urlencode(params)}"


def generate_ical_content(title: str, start_dt: str, end_dt: str, details: str, location: str) -> str:
    return (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//Basilica Parish Assistant//EN\n"
        "BEGIN:VEVENT\n"
        f"SUMMARY:{title}\n"
        f"DTSTART:{start_dt.replace('-', '').replace(':', '')}\n"
        f"DTEND:{end_dt.replace('-', '').replace(':', '')}\n"
        f"DESCRIPTION:{details}\n"
        f"LOCATION:{location}\n"
        "END:VEVENT\n"
        "END:VCALENDAR"
    )


def detect_unknown_input(text: str) -> bool:
    """Robust Unknown Input Detector to identify keyboard smashing, repeated letters, 

    numbers-only, punctuation-only, and other non-linguistic gibberish.
    """
    cleaned = text.strip().lower()
    if not cleaned:
        return True
    
    # 1. Punctuation only or numeric/special chars only
    if re.match(r"^[^\w\s]+$", cleaned) or re.match(r"^[\d\s\W]+$", cleaned):
        return True
        
    # 2. Repeated single characters (e.g. xxxxxxxx, aaaaaaa)
    if re.match(r"^(.)\1{4,}$", cleaned):
        return True

    return False




