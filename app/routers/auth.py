# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Admin
from app.utils.security import verify_password, create_access_token
from app.config import settings  # To drive secure flag, cookie domain, etc.

router = APIRouter(prefix="/auth", tags=["auth"])


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=Token, include_in_schema=False)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate an admin user.
    - Returns a JSON payload with an access_token.
    - Also sets the token in a secure, HTTP-only cookie.
    """
    # 1. Fetch the admin record
    stmt = select(Admin).where(Admin.username == form_data.username)
    result = await db.execute(stmt)
    user: Admin | None = result.scalars().first()

    # 2. Verify credentials
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # 3. Create the JWT
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    # 4. Set it in a secure, HttpOnly cookie
        # After generating `token` in login():
    response.set_cookie(
        key=settings.cookie_name,
        value=f"Bearer {token}",     # include the "Bearer " prefix
        httponly=True,
        secure=settings.cookie_secure,
        max_age=settings.cookie_max_age,
        path="/",                     # ensure cookie is sent on all paths
        samesite="lax",
        domain=settings.cookie_domain or None
    )


    # 5. Return the token in the JSON body too
    return {"access_token": token}
