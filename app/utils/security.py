# app/utils/security.py

from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models import Admin, RoleEnum

# Password hashing
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# JWT creation & decoding
def create_access_token(data: dict, expires_minutes: int = 60) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# Token extraction from header or cookie
bearer_scheme = HTTPBearer(auto_error=False)

async def get_token(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> str:
    # 1) Authorization header
    if creds and creds.scheme.lower() == "bearer":
        return creds.credentials

    # 2) HttpOnly cookie fallback
    cookie = request.cookies.get(settings.cookie_name)
    if cookie and cookie.startswith("Bearer "):
        return cookie.split(" ", 1)[1]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


# Load the Admin ORM instance
async def get_current_user(
    token: str = Depends(get_token),
    db: AsyncSession = Depends(get_db)
) -> Admin:
    """
    Decode JWT, fetch the Admin from DB, and return it.
    """
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    stmt = select(Admin).where(Admin.id == int(user_id))
    result = await db.execute(stmt)
    user: Admin | None = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# Dependency: any authenticated user (viewer or admin)
async def require_viewer_or_admin(
    user: Admin = Depends(get_current_user)
) -> Admin:
    return user


# Dependency: only allow role="admin"
async def require_admin(
    user: Admin = Depends(get_current_user)
) -> Admin:
    if user.role.value != RoleEnum.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return user


# New dependency: returns the Admin ORM for full access (including .username)
async def get_current_admin(
    user: Admin = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Admin:
    """
    Ensures current user is admin, then returns the Admin record.
    """
    # `user` already validated; fetch fresh from DB for full fields
    admin = await db.get(Admin, user.id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found",
        )
    return admin
