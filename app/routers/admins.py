# app/routers/admins.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update

from app.database import get_db
from app.models import Admin
from app.schemas.admins import AdminCreate, AdminPasswordUpdate
from app.utils.security import require_admin, hash_password

router = APIRouter(
    prefix="/api/admins",
    tags=["admins"],
    dependencies=[Depends(require_admin)]
)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_admin(
    admin_in: AdminCreate,
    db: AsyncSession = Depends(get_db)
):
    # Prevent duplicate usernames
    existing = (await db
        .execute(select(Admin).where(Admin.username == admin_in.username))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_admin = Admin(
        username=admin_in.username,
        password=hash_password(admin_in.password)
    )
    db.add(new_admin)
    await db.commit()
    return {"id": new_admin.id, "username": new_admin.username}


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    # Prevent self-deletion
    if current_admin.id == admin_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    res = await db.execute(delete(Admin).where(Admin.id == admin_id))
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    await db.commit()


@router.put("/{admin_id}/password")
async def change_password(
    admin_id: int,
    pw_update: AdminPasswordUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        update(Admin)
        .where(Admin.id == admin_id)
        .values(password=hash_password(pw_update.password))
    )
    res = await db.execute(stmt)
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    await db.commit()
    return {"message": "Password updated"}
