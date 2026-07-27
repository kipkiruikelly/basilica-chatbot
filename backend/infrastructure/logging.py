import json
import logging
import time
from flask import g, request

logger = logging.getLogger("basilica")
logger.setLevel(logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def log_event(event_type: str, data: dict, level: str = "info"):
    """Logs structured JSON event information."""
    correlation_id = "system_startup"
    try:
        # Only accessible inside an active Flask application/request thread
        correlation_id = getattr(g, "correlation_id", "unknown")
    except RuntimeError:
        pass

    payload = {
        "timestamp": time.time(),
        "event_type": event_type,
        "correlation_id": correlation_id,
        **data
    }
    log_msg = json.dumps(payload)
    if level == "error":
        logger.error(log_msg)
    elif level == "warning":
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

