# app/routers/devices.py

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.snipe import get_hardware_id
from app.database import get_db
from app.models import Device, Admin, IP, OwnerType
from app.schemas.devices import DeviceCreate, DeviceRead
from app.utils.security import (
    require_admin,
    require_viewer_or_admin,
    get_current_admin,
)
import csv, io
from fastapi import UploadFile, File, status, Depends
from typing import List
from app.config import settings
router = APIRouter(prefix="/devices", tags=["devices"])


# ─────────── Distinct-list endpoints ───────────
@router.get(
    "/accounts",
    response_model=list[str],
    dependencies=[Depends(require_viewer_or_admin)],
    summary="List distinct account names",
)
async def list_accounts(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Device.account_name).distinct())
    return [r[0] for r in rows.all()]


@router.get(
    "/locations",
    response_model=list[str],
    dependencies=[Depends(require_viewer_or_admin)],
    summary="List distinct locations",
)
async def list_locations(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Device.location).distinct())
    return [r[0] for r in rows.all()]


# ─────────── helper functions ───────────
async def _get_ip_row(db: AsyncSession, dev_id: int) -> IP | None:
    return (
        await db.execute(
            select(IP).where(
                IP.owner_type == OwnerType.device,
                IP.owner_id == dev_id,
            )
        )
    ).scalars().first()


async def _enrich(dev: Device, db: AsyncSession) -> DeviceRead:
    # 1) Fetch the IP child record
    ip = await _get_ip_row(db, dev.id)

    # 2) Look up the admin who last updated *that* IP row
    admin = None
    if ip and ip.updated_by:
        admin = await db.get(Admin, ip.updated_by)

    # 3) Build the Base DeviceRead from the Device itself
    base = DeviceRead.from_orm(dev)

    # 4) Overlay IP fields plus the IP’s updated_by username and updated_at timestamp
    return base.copy(update={
        "device_type":         ip.device_type        if ip else None,
        "ip_address":          ip.ip_address         if ip else None,
        "mac_address":         ip.mac_address        if ip else None,
        "asset_tag":           ip.asset_tag          if ip else None,
        "updated_by_username": admin.username        if admin else None,
        # use the IP row’s updated_at so every IP change bumps this
        "updated_at":          ip.updated_at         if ip else dev.updated_at,
    })



# ─────────── routes ───────────
@router.get(
    "/",
    response_model=list[DeviceRead],
    dependencies=[Depends(require_viewer_or_admin)],
)
async def list_devices(db: AsyncSession = Depends(get_db)):
    # 1) fetch raw Device rows
    rows = (await db.execute(select(Device))).scalars().all()

    out = []
    for d in rows:
        enriched = await _enrich(d, db)

        # 1) grab the IP row so we can cache/peek its snipe_id
        ip = await _get_ip_row(db, d.id)

        # 2) if we haven’t cached it yet, look it up now and persist
        if ip and ip.snipe_id is None:
            hw = get_hardware_id(ip.asset_tag or "")
            if hw:
                ip.snipe_id = hw
                await db.commit()
        # 3) now either way read it
        hw_id = ip.snipe_id if ip else None

        # 4) build the URL from that cached value
        item = enriched.dict()
        item["snipe_url"] = (
            f"{settings.SNIPE_UI}/hardware/{hw_id}"
            if hw_id else None
        )

        out.append(item)


    return out


@router.get(
    "/{dev_id}",
    response_model=DeviceRead,
    dependencies=[Depends(require_viewer_or_admin)],
)
async def get_device(
    dev_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
):
    dev = await db.get(Device, dev_id)
    if not dev:
        raise HTTPException(404, "Device not found")
    return await _enrich(dev, db)


@router.post(
    "/",
    response_model=DeviceRead,
    dependencies=[Depends(require_admin)],
)
async def create_device(
    payload: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    # ⏺ duplicate-IP check
    ip_str = str(payload.ip_address)
    dup = await db.execute(select(IP).where(IP.ip_address == ip_str))
    if (d := dup.scalars().first()):
        # load the other device to get its hostname
        other_dev = await db.get(Device, d.owner_id)
        name = other_dev.hostname if other_dev else f"{d.owner_type} #{d.owner_id}"
        raise HTTPException(400, f"IP {d.ip_address} already assigned to {name}")

    # 1) core record
    dev = Device(
        account_name=payload.account_name,
        location=payload.location,
        hostname=payload.hostname,
        updated_by=admin.id,
    )
    db.add(dev)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "Hostname already exists")
    await db.refresh(dev)

    # 2) IP row
    ip = IP(
        owner_type=OwnerType.device,
        owner_id=dev.id,
        device_type=payload.device_type,
        ip_address=ip_str,
        mac_address=payload.mac_address,
        asset_tag=payload.asset_tag,
        updated_by=admin.id,
    )
    db.add(ip)
    await db.commit()

    return await _enrich(dev, db)


@router.put(
    "/{dev_id}",
    response_model=DeviceRead,
    dependencies=[Depends(require_admin)],
)
async def update_device(
    dev_id: int,
    payload: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    dev = await db.get(Device, dev_id)
    if not dev:
        raise HTTPException(404, "Device not found")

    # ⏺ duplicate-IP check (skip if unchanged)
    new_ip = str(payload.ip_address)
    existing = await _get_ip_row(db, dev_id)
    if not (existing and existing.ip_address == new_ip):
        dup = await db.execute(select(IP).where(IP.ip_address == new_ip))
        if (d := dup.scalars().first()):
            other_dev = await db.get(Device, d.owner_id)
            name = other_dev.hostname if other_dev else f"{d.owner_type} #{d.owner_id}"
            raise HTTPException(400, f"IP {d.ip_address} already assigned to {name}")

    # update Device
    dev.account_name = payload.account_name
    dev.location     = payload.location
    dev.hostname     = payload.hostname
    dev.updated_by   = admin.id

    # update/create IP row
    ip = existing or IP(owner_type=OwnerType.device, owner_id=dev.id)
    if not existing:
        db.add(ip)
    ip.device_type  = payload.device_type
    ip.ip_address   = new_ip
    ip.mac_address  = payload.mac_address
    ip.asset_tag    = payload.asset_tag
    ip.updated_by   = admin.id

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "Hostname already exists")

    # 1) make sure our Device object is fresh
    await db.refresh(dev)

    # 2) grab the IP row so we can cache/peek its snipe_id
    ip = await _get_ip_row(db, dev.id)

    # 3) if not yet cached, look it up now and persist

    hw = get_hardware_id(ip.asset_tag or "")
    if hw:
        ip.snipe_id = hw
        await db.commit()
        await db.refresh(ip)

    # 4) now read whichever snipe_id we have
    hw_id = ip.snipe_id if ip else None

    # 5) enrich the device and inject the same snipe_url field
    enriched = await _enrich(dev, db)
    data = enriched.dict()
    data["snipe_url"] = (
        f"{settings.SNIPE_UI}/hardware/{hw_id}"
        if hw_id else None
    )

    return data

@router.delete(
    "/{dev_id}",
    status_code=204,
    dependencies=[Depends(require_admin)],
)
async def delete_device(dev_id: int, db: AsyncSession = Depends(get_db)):
    dev = await db.get(Device, dev_id)
    if not dev:
        raise HTTPException(404, "Device not found")

    # remove child IP first
    await db.execute(
        delete(IP).where(
            IP.owner_type == OwnerType.device,
            IP.owner_id == dev_id,
        )
    )
    await db.delete(dev)
    await db.commit()

@router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="Bulk-import devices from CSV"
)
async def import_devices(
    file: UploadFile  = File(...),
    db:   AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin),
) -> List[DeviceRead]:
    """
    Expect a CSV with columns:
    account_name, location, device_type, hostname, ip_address,
    optional: mac_address, asset_tag
    """
    text   = (await file.read()).decode()
    reader = csv.DictReader(io.StringIO(text))
    created: list[Device] = []

    for row in reader:
        # skip rows missing any required field
        if not (row.get("account_name") and row.get("location")
                and row.get("device_type") and row.get("hostname")
                and row.get("ip_address")):
            continue

        # 1) create Device
        dev = Device(
            account_name = row["account_name"].strip(),
            location     = row["location"].strip(),
            hostname     = row["hostname"].strip(),
            updated_by   = admin.id,
        )
        db.add(dev)
        await db.flush()   # gives dev.id

        # 2) create its IP row
        ip = IP(
            owner_type  = OwnerType.device,
            owner_id    = dev.id,
            device_type = row["device_type"].strip(),
            ip_address  = row["ip_address"].strip(),
            mac_address = row.get("mac_address","").strip() or None,
            asset_tag   = row.get("asset_tag","").strip()   or None,
            updated_by  = admin.id,
        )
        db.add(ip)

        created.append(dev)

    await db.commit()
    # return the enriched list
    return [await _enrich(d, db) for d in created]
