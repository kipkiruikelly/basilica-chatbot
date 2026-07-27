from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time

@dataclass
class User:
    id: str
    username: str
    password_hash: str
    role: str  # "Super Administrator", "Parish Administrator", "Priest", "Secretary", "Ministry Leader", "Read Only"
    status: str = "Active"  # "Active", "Suspended"
    mfa_secret: Optional[str] = None
    mfa_enabled: bool = False
    created_at: float = field(default_factory=time.time)

@dataclass
class ContentItem:
    id: str
    title: str
    category: str  # "mass_schedule", "confessions", "sacraments", "events", "announcements", "donations", "contacts", "bulletins", "faqs", "emergency_notices", "static_pages", "knowledge_base"
    content_data: Dict[str, Any]
    status: str = "Draft"  # "Draft", "Pending Review", "Approved", "Scheduled", "Published", "Archived", "Soft-Deleted"
    version: int = 1
    created_by: str = "system"
    created_at: float = field(default_factory=time.time)
    updated_by: str = "system"
    updated_at: float = field(default_factory=time.time)
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None
    published_by: Optional[str] = None
    published_at: Optional[float] = None
    scheduled_for: Optional[float] = None  # Timestamp for future publish
    expiry_date: Optional[float] = None    # Timestamp for auto-archive
    change_summary: Optional[str] = None
    change_notes: Optional[str] = None
    comments: List[Dict[str, Any]] = field(default_factory=list)  # Threaded discussions: [{"user": "...", "text": "...", "timestamp": ...}]

@dataclass
class VersionHistory:
    content_id: str
    version: int
    title: str
    content_data: Dict[str, Any]
    status: str
    updated_by: str
    updated_at: float
    change_notes: Optional[str]
    change_summary: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None

# Role-Based Access Matrix
ROLE_PERMISSIONS = {
    "Super Administrator": ["Publishing", "Editing", "Deleting", "Viewing analytics", "Managing users", "Approving"],
    "Parish Administrator": ["Publishing", "Editing", "Deleting", "Viewing analytics", "Managing users", "Approving"],
    "Priest": ["Publishing", "Editing", "Viewing analytics", "Approving"],
    "Secretary": ["Editing", "Viewing analytics"],
    "Ministry Leader": ["Editing"],
    "Content Editor": ["Editing"],
    "Volunteer": ["Editing"],
    "Registered Parishioner": [],
    "Guest": [],
    "Read Only": ["Viewing analytics"]
}
