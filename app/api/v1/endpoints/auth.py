"""Authentication endpoints."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, UserUpdate, PasswordChange
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    verify_refresh_token,
    get_current_user,
)
from app.core.rate_limit import limiter, get_rate_limit
from app.core.exceptions import AuthenticationError, DuplicateError
from app.config import settings

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit("auth_register"))
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        Created user
        
    Raises:
        DuplicateError: If email already exists
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise DuplicateError("Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
@limiter.limit(get_rate_limit("auth_login"))
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email and password.
    
    Args:
        form_data: OAuth2 password form (username=email, password)
        db: Database session
        
    Returns:
        Access and refresh tokens
        
    Raises:
        AuthenticationError: If credentials are invalid
    """
    # Get user by email
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationError("Incorrect email or password")
    
    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        raise AuthenticationError("Incorrect email or password")
    
    # Check if user is active
    if not user.is_active:
        raise AuthenticationError("User account is inactive")
    
    # Create tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
    }


@router.post("/refresh", response_model=Token)
@limiter.limit(get_rate_limit("auth_refresh"))
async def refresh_token(
    request: Request,
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_token: Refresh token
        db: Database session
        
    Returns:
        New access and refresh tokens
        
    Raises:
        AuthenticationError: If refresh token is invalid
    """
    # Verify refresh token
    payload = verify_refresh_token(refresh_token)
    user_id = payload.get("sub")
    
    # Get user
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationError("User not found")
    
    if not user.is_active:
        raise AuthenticationError("User account is inactive")
    
    # Create new tokens
    new_access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user data
    """
    return current_user


@router.put("/me", response_model=UserResponse)
@limiter.limit(get_rate_limit("default"))
async def update_current_user(
    request: Request,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user profile information.
    
    Args:
        user_data: User update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated user data
        
    Raises:
        DuplicateError: If email already exists
    """
    # Check if email is being changed and if it's already in use
    if user_data.email is not None and user_data.email != current_user.email:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise DuplicateError("Email already in use")
        current_user.email = user_data.email
    
    # Update user fields
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.phone is not None:
        current_user.phone = user_data.phone
    if user_data.company is not None:
        current_user.company = user_data.company
    if user_data.position is not None:
        current_user.position = user_data.position
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.post("/change-password")
@limiter.limit(get_rate_limit("default"))
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user's password.
    
    Args:
        password_data: Password change data (current and new password)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        AuthenticationError: If current password is incorrect
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise AuthenticationError("Current password is incorrect")
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    
    await db.commit()
    
    return {"message": "Password changed successfully"}
