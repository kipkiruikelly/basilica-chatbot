from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class User:
    id: str
    username: str
    password_hash: str
    role: str  # "Super Administrator", "Parish Administrator", "Priest", "Secretary", "Ministry Leader", "Content Editor", "Volunteer", "Registered Parishioner", "Guest", "Read Only"
    status: str = "Active"  # "Active", "Suspended", "Locked"
    mfa_secret: Optional[str] = None
    mfa_enabled: bool = False
    failed_attempts: int = 0
    locked_until: float = 0.0
    created_at: float = field(default_factory=float)

@dataclass
class UserProfile:
    user_id: str
    first_name: str = ""
    middle_name: Optional[str] = ""
    last_name: str = ""
    preferred_name: Optional[str] = ""
    gender: str = "Unknown"
    date_of_birth: Optional[str] = ""
    national_id: Optional[str] = ""
    phone_number: str = ""
    email_address: str = ""
    preferred_language: str = "English"
    time_zone: str = "UTC"

@dataclass
class ChurchProfile:
    user_id: str
    parish: str = "St. Joseph Cathedral"
    small_christian_community: str = ""
    ministry_membership: List[str] = field(default_factory=list)
    sacraments_received: List[str] = field(default_factory=list)
    baptism_date: Optional[str] = ""
    confirmation_date: Optional[str] = ""
    marriage_status: str = "Single"
    volunteer_status: str = "Inactive"

@dataclass
class Address:
    user_id: str
    country: str = "Kenya"
    county: str = "Nairobi"
    city: str = "Nairobi"
    postal_code: str = ""
    physical_address: str = ""

@dataclass
class Preferences:
    user_id: str
    dark_mode: bool = True
    notification_preferences: str = "Email"  # "Email", "SMS", "None"
    language: str = "English"
    accessibility_settings: dict = field(default_factory=dict)
    ai_memory_consent: bool = True

@dataclass
class DeviceSession:
    session_id: str
    user_id: str
    ip_address: str = ""
    browser: str = "Chrome"
    os: str = "macOS"
    last_login: float = 0.0
    is_active: bool = True

@dataclass
class RefreshToken:
    token_string: str
    user_id: str
    expires_at: float
    revoked: bool = False
