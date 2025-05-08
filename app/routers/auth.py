from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Admin
from app.utils.security import (
    verify_password,
    create_access_token
)

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
    Authenticates an admin, returns a JWT in JSON AND
    sets the same token in a secure HTTP-only cookie.
    """
    stmt = select(Admin).where(Admin.username == form_data.username)
    result = await db.execute(stmt)
    user: Admin | None = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # create a JWT with sub=user.id and role=user.role.value
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    # set it in a httponly cookie so browser will send it automatically
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        secure=False,      # set to True under HTTPS
        max_age=60 * 60 * 24,
        samesite="lax",
    )

    return {"access_token": token}
