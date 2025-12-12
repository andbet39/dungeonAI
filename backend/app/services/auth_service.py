"""
Authentication service for user management, password hashing, and JWT tokens.
"""
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Response, HTTPException, status

from app.config.settings import settings
from app.domain.entities.user import User
from app.db.mongodb import mongodb_manager


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Handles user authentication, password hashing, and JWT token management."""

    def __init__(self):
        self.db = mongodb_manager
        self.collection_name = "users"

    # Password Hashing
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    # JWT Token Management
    @staticmethod
    def create_access_token(user_id: str, email: str, role: str) -> str:
        """Create a JWT access token."""
        expire = datetime.utcnow() + timedelta(days=settings.auth.jwt_expire_days)
        to_encode = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": expire
        }
        return jwt.encode(
            to_encode,
            settings.auth.jwt_secret_key,
            algorithm=settings.auth.jwt_algorithm
        )

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.auth.jwt_secret_key,
                algorithms=[settings.auth.jwt_algorithm]
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

    # Cookie Management
    @staticmethod
    def set_auth_cookie(response: Response, token: str):
        """Set httpOnly authentication cookie."""
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=settings.auth.jwt_expire_days * 24 * 60 * 60,  # Convert days to seconds
            path="/"
        )

    @staticmethod
    def set_player_token_cookie(response: Response, player_token: str):
        """Set httpOnly player token cookie."""
        response.set_cookie(
            key="player_token",
            value=player_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=settings.auth.jwt_expire_days * 24 * 60 * 60,
            path="/"
        )

    @staticmethod
    def clear_auth_cookies(response: Response):
        """Clear authentication cookies."""
        response.delete_cookie(key="access_token", path="/")
        response.delete_cookie(key="player_token", path="/")

    # User CRUD Operations
    async def create_user(self, email: str, password: str, role: str = "user") -> User:
        """Create a new user account."""
        if not self.db.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not available"
            )

        # Check if email already exists
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user
        password_hash = self.hash_password(password)
        user = User.create(email=email, password_hash=password_hash, role=role)

        # Insert into database
        collection = self.db.get_collection(self.collection_name)
        await collection.insert_one(user.to_dict())

        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        if not self.db.is_connected:
            return None

        collection = self.db.get_collection(self.collection_name)
        user_data = await collection.find_one({"email": email.lower().strip()})

        if user_data:
            return User.from_dict(user_data)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by user_id."""
        if not self.db.is_connected:
            return None

        collection = self.db.get_collection(self.collection_name)
        user_data = await collection.find_one({"user_id": user_id})

        if user_data:
            return User.from_dict(user_data)
        return None

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

    async def update_last_login(self, user_id: str):
        """Update user's last login timestamp."""
        if not self.db.is_connected:
            return

        collection = self.db.get_collection(self.collection_name)
        await collection.update_one(
            {"user_id": user_id},
            {"$set": {"last_login": datetime.utcnow().isoformat()}}
        )


# Global auth service instance
auth_service = AuthService()
