"""
Authentication API routes for user registration, login, and management.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.services.auth_service import auth_service
from app.api.deps import get_current_user
from app.domain.entities.user import User


router = APIRouter(prefix="/api/auth", tags=["auth"])


# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "player@example.com",
                "password": "strongpassword123"
            }
        }


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User information response (without sensitive data)."""
    user_id: str
    email: str
    role: str
    is_active: bool
    created_at: str
    last_login: Optional[str]


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, response: Response):
    """
    Register a new user account.
    
    Creates a new user with email and password, sets authentication cookie.
    """
    # Validate password length
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Create user
    try:
        user = await auth_service.create_user(
            email=request.email,
            password=request.password
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
    
    # Generate JWT token
    token = auth_service.create_access_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role
    )
    
    # Set authentication cookie
    auth_service.set_auth_cookie(response, token)
    
    # Update last login
    await auth_service.update_last_login(user.user_id)
    
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.post("/login", response_model=UserResponse)
async def login(request: LoginRequest, response: Response):
    """
    Login with email and password.
    
    Authenticates user and sets authentication cookie.
    """
    # Authenticate user
    user = await auth_service.authenticate_user(request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Generate JWT token
    token = auth_service.create_access_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role
    )
    
    # Set authentication cookie
    auth_service.set_auth_cookie(response, token)
    
    # Update last login
    await auth_service.update_last_login(user.user_id)
    user.update_last_login()  # Update in-memory object too
    
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.post("/logout")
async def logout(response: Response):
    """
    Logout the current user.
    
    Clears authentication cookies.
    """
    auth_service.clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Returns user profile without sensitive data.
    """
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )
