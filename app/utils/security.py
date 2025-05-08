from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta

from app.config import settings

# allow header OR cookie
bearer_scheme = HTTPBearer(auto_error=False)
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def create_access_token(data: dict, expires_minutes: int = 60) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_token(request: Request, creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    """
    Try extracting a Bearer token from:
      1) Authorization header
      2) 'access_token' HTTP-only cookie
    """
    # 1) Authorization header
    if creds and creds.scheme.lower() == "bearer":
        return creds.credentials

    # 2) cookie fallback
    cookie = request.cookies.get("access_token")
    if cookie and cookie.startswith("Bearer "):
        return cookie.split(" ", 1)[1]

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def get_current_user(token: str = Depends(get_token)) -> dict:
    """
    Decode the JWT and return its payload (including 'sub' and 'role').
    """
    return decode_access_token(token)


async def require_viewer_or_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    Guard: any authenticated user (role 'admin' or 'user') may proceed.
    """
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    Guard: only admin may proceed.
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
