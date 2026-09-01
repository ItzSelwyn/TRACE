import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def create_access_token(data: dict) -> str:
    """Create a JWT access token with expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode JWT and return the authenticated User from the database when available.

    In the local demo environment we allow anonymous access so the dashboard and vehicle
    trace frontend can query the API without a user login flow.
    """
    if token is None and settings.ALLOW_ANON_DEMO:
        return User(
            user_id=uuid.uuid4(),
            name="Demo User",
            email="demo@trace.local",
            password_hash="",
            role="operator",
            created_at=datetime.now(timezone.utc),
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
    except Exception:
        user = None

    if user is not None:
        return user

    role = payload.get("role", "operator")
    if role not in {"operator", "analyst", "admin"}:
        raise credentials_exception

    try:
        parsed_user_id = uuid.UUID(str(user_id))
    except ValueError:
        raise credentials_exception

    return User(
        user_id=parsed_user_id,
        name="Authenticated User",
        email=f"{parsed_user_id}@localhost",
        password_hash="",
        role=role,
        created_at=datetime.now(timezone.utc),
    )


def require_role(*roles: str) -> Callable:
    """Return a FastAPI dependency that checks the current user has one of the allowed roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user
    return role_checker
