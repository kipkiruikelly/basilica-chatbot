import hmac
import hashlib
import json
import base64
import time
from functools import wraps
from typing import Optional, List
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from backend.domain.admin_models import ROLE_PERMISSIONS

SECRET_KEY = "basilica_cathedral_nav_key_2026"

def hash_password(password: str) -> str:
    return generate_password_hash(password)

def verify_password(password: str, pw_hash: str) -> bool:
    return check_password_hash(pw_hash, password)

def generate_token(payload: dict) -> str:
    """Generates an enterprise-grade secure custom JWT-like signed HMAC-SHA256 token."""
    payload["exp"] = time.time() + 7200  # Token expires in 2 hours
    payload_json = json.dumps(payload).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").replace("=", "")
    
    signature = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").replace("=", "")
    
    return f"{payload_b64}.{signature_b64}"

def verify_token(token: str) -> Optional[dict]:
    """Verifies HMAC signature, checks expiration, and returns payload."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature_b64 = parts[0], parts[1]
        
        # Verify HMAC signature
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").replace("=", "")
        
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            return None
            
        # Pad and decode base64 payload
        rem = len(payload_b64) % 4
        padded_b64 = payload_b64 + ("=" * (4 - rem) if rem > 0 else "")
        payload_json = base64.urlsafe_b64decode(padded_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)
        
        # Enforce expiry
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except Exception:
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            return jsonify({"error": "Authentication token missing or invalid"}), 401
            
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Token is invalid, modified, or expired"}), 401
            
        g.user_id = payload.get("id")
        g.username = payload.get("username")
        g.role = payload.get("role")
        return f(*args, **kwargs)
    return decorated

def require_permission(permission: str):
    """Asserts that the authenticated user's role has the required permission."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            role = getattr(g, "role", "Read Only")
            permissions = ROLE_PERMISSIONS.get(role, [])
            if permission not in permissions:
                return jsonify({"error": f"Unauthorized. Role '{role}' lacks permission: '{permission}'"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
