from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt
import bcrypt
import asyncio

from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.user import UserCreate, UserLogin, UserOut, Token
from app.security_utils import (
    check_login_attempt, record_failed_login, record_successful_login
)

router = APIRouter()
settings = get_settings()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _create_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user.id, "role": user.role.value, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    # Rate limiting disabled in DEBUG mode (local development)
    if not settings.DEBUG:
        # Get limiter from app state (set in main.py)
        limiter = request.app.state.limiter
        
        # Check rate limit: 5 registrations per minute per IP
        try:
            limiter.try_request("5/minute", request)
        except Exception:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 5 registrations per minute.")
    
    # Check duplicates
    existing = await db.execute(
        select(User).where((User.email == data.email) | (User.username == data.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email or username already registered")

    user = User(
        email=data.email,
        username=data.username,
        hashed_password=_hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.flush()

    # Auto-create wallet
    wallet = Wallet(user_id=user.id, balance=0.0)
    db.add(wallet)
    await db.flush()

    return user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with exponential backoff and progressive delays.
    Failed attempts trigger increasing delays: 1s → 2s → 4s → 8s → 16s
    After 3 failures, account is locked for 15 minutes.
    Rate limiting disabled in DEBUG mode (local development).
    """
    # Rate limiting disabled in DEBUG mode (local development)
    if not settings.DEBUG:
        # Get limiter from app state (set in main.py)
        limiter = request.app.state.limiter
        
        # Check rate limit: 5 login attempts per minute per IP (application-level)
        try:
            limiter.try_request("5/minute", request)
        except Exception:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 5 login attempts per minute.")
    
    # Get client IP for progressive delay tracking
    client_ip = request.client.host if request.client else "unknown"
    
    # Check for account lockout and get progressive delay
    is_allowed, delay_info = await check_login_attempt(data.username, client_ip)
    if not is_allowed:
        raise HTTPException(status_code=429, detail=delay_info)
    
    # Apply progressive delay with exponential backoff if needed
    if delay_info and "wait" in delay_info:
        # Extract delay from message like "Progressive delay: wait 2.0s before retry"
        try:
            delay_str = delay_info.split("wait ")[1].split("s")[0]
            delay = float(delay_str)
            await asyncio.sleep(delay)
        except (IndexError, ValueError):
            pass
    
    # Verify credentials
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user or not _verify_password(data.password, user.hashed_password):
        # Record failed attempt
        await record_failed_login(data.username, client_ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Reset failed attempts on successful login
    await record_successful_login(data.username, client_ip)

    token = _create_token(user)
    return Token(access_token=token, role=user.role, user_id=user.id)
