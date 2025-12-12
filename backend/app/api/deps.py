"""
API dependencies for dependency injection.
"""
from typing import Generator, Optional
from fastapi import Cookie, Depends, HTTPException, status

from ..core import game_manager, game_loop
from ..services import ai_service, storage_service, monster_service
from ..services.auth_service import auth_service
from ..domain.entities.user import User


def get_game_manager():
    """Get the game manager instance."""
    return game_manager


def get_game_loop():
    """Get the game loop instance."""
    return game_loop


def get_ai_service():
    """Get the AI service instance."""
    return ai_service


def get_storage_service():
    """Get the storage service instance."""
    return storage_service


def get_monster_service():
    """Get the monster service instance."""
    return monster_service


async def get_current_user(
    access_token: Optional[str] = Cookie(None)
) -> User:
    """
    Get the currently authenticated user from JWT cookie.
    
    Args:
        access_token: JWT token from httpOnly cookie
        
    Returns:
        User object
        
    Raises:
        HTTPException: If not authenticated or user not found
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Decode token
    payload = auth_service.decode_token(access_token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Get user from database
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require the current user to have admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if admin
        
    Raises:
        HTTPException: If not admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
