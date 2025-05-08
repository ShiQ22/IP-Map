# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User
from app.schemas.users import UserRead, UserCreate, UserUpdate
from app.utils.security import require_admin

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=list[UserRead], dependencies=[Depends(require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User))
    return q.scalars().all()

@router.post("/", response_model=UserRead, dependencies=[Depends(require_admin)])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    usr = User(**payload.dict())
    db.add(usr)
    await db.commit()
    await db.refresh(usr)
    return usr

@router.put("/{id}", response_model=UserRead, dependencies=[Depends(require_admin)])
async def update_user(id: int, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.id == id))
    usr = q.scalars().first()
    if not usr:
        raise HTTPException(404, "User not found")
    for field, val in payload.dict(exclude_unset=True).items():
        setattr(usr, field, val)
    await db.commit()
    await db.refresh(usr)
    return usr

@router.delete("/{id}", dependencies=[Depends(require_admin)])
async def delete_user(id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.id == id))
    usr = q.scalars().first()
    if not usr:
        raise HTTPException(404, "User not found")
    await db.delete(usr)
    await db.commit()
    return {"detail": "User deleted"}
