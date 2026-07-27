import re
import uuid
import time
from flask import request, g, jsonify
from collections import defaultdict
from backend.infrastructure.logging import log_event

# In-memory Rate Limiting: max 60 requests per minute per IP address
# Structure: { ip_address: (tokens, last_leak_time) }
RATE_LIMIT_TOKENS = 60
LEAK_RATE_PER_SECOND = 1.0  # leak 1 token per second
ip_token_buckets = defaultdict(lambda: (float(RATE_LIMIT_TOKENS), time.time()))

def sanitize_input(text: str) -> str:
    """Basic XSS mitigation and request sanitization."""
    # Strip HTML tags
    clean = re.sub(r"<[^>]*>", "", text)
    return clean

def register_middlewares(app):
    @app.before_request
    def before_request_func():
        # Inject correlation IDs (Request IDs) for log tracing
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        g.correlation_id = correlation_id
        g.start_time = time.time()
        
        # Simple token-bucket rate limiting
        client_ip = request.remote_addr or "unknown_ip"
        now = time.time()
        tokens, last_update = ip_token_buckets[client_ip]
        
        # Leak tokens based on elapsed time
        elapsed = now - last_update
        tokens = min(RATE_LIMIT_TOKENS, tokens + (elapsed * LEAK_RATE_PER_SECOND))
        
        if tokens < 1.0:
            log_event("rate_limit_exceeded", {"client_ip": client_ip}, "warning")
            return jsonify({
                "error": "Too many requests. Please slow down and try again.",
                "correlation_id": correlation_id
            }), 429
            
        ip_token_buckets[client_ip] = (tokens - 1.0, now)

        # Sanitize incoming JSON payload if present
        if request.is_json:
            data = request.get_json(silent=True)
            if data and "question" in data:
                data["question"] = sanitize_input(data["question"])

    @app.after_request
    def after_request_func(response):
        # Log latency & request outcomes
        elapsed_ms = (time.time() - g.start_time) * 1000
        log_event("request_latency", {
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "latency_ms": round(elapsed_ms, 2),
            "client_ip": request.remote_addr
        })
        
        # Add correlation ID header to the response
        response.headers["X-Correlation-ID"] = getattr(g, "correlation_id", "none")
        return response
