"""
User entity for authentication and account management.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class User:
    """User account with authentication credentials."""
    user_id: str
    email: str
    password_hash: str
    role: str = "user"  # "user" or "admin"
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_login: Optional[str] = None

    @classmethod
    def create(cls, email: str, password_hash: str, role: str = "user") -> "User":
        """Create a new user with generated ID."""
        return cls(
            user_id=str(uuid.uuid4()),
            email=email.lower().strip(),
            password_hash=password_hash,
            role=role
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "password_hash": self.password_hash,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_login": self.last_login
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create user from dictionary."""
        return cls(
            user_id=data["user_id"],
            email=data["email"],
            password_hash=data["password_hash"],
            role=data.get("role", "user"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            last_login=data.get("last_login")
        )

    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow().isoformat()

    def __repr__(self) -> str:
        return f"User(user_id={self.user_id}, email={self.email}, role={self.role})"
