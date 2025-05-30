# app/services/scanner.py

import asyncio
import datetime
import ipaddress
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import nmap
import socket
import re
import sys

from manuf import MacParser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from sqlalchemy.dialects.mysql import insert as mysql_insert


from app.models import (
    LiveMonitor,
    History,
    IP,            
    OwnerType,     
    User,          
    Device,        
    Server         
)
HISTORY_RETENTION_DAYS = 14

# Build one parser instance (built‐in OUI data auto‐loaded)
_mac_parser = MacParser()

# Precompile MAC regex
_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def ping_host(ip: str, timeout: int = 1) -> bool:
    return subprocess.run(
        ["ping", "-c", "1", "-W", str(timeout), ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ).returncode == 0


def get_arp_mac(ip: str) -> str | None:
    try:
        out = subprocess.check_output(["arp", "-n", ip], stderr=subprocess.DEVNULL).decode()
    except Exception:
        return None
    m = re.search(r"(([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})", out)
    return m.group(1).upper() if m else None


def nmap_probe(ips: list[str]) -> dict[str, dict]:
    nm = nmap.PortScanner()
    nm.scan(
        hosts=" ".join(ips),
        arguments=(
            "-sn -PR -n -T4 "
            "--max-retries 1 --host-timeout 200ms "
            "-r --privileged"
        )
    )
    results: dict[str, dict] = {}
    for host in nm.all_hosts():
        info = nm[host]
        mac = info.get("addresses", {}).get("mac")
        results[host] = {
            "status":     "Up",
            "hostname":   info.hostname() or None,
            "mac_address": mac,
            "raw_vendor": info.get("vendor", {}) or {}
        }
    return results


async def scan_cidr(cidr: str, db: AsyncSession) -> None:
    now_dt  = datetime.datetime.utcnow()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    net   = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(h) for h in net.hosts()]
    results: dict[str, dict] = {}

        # 1) Parallel ping + ARP
    with ThreadPoolExecutor(max_workers=80) as ex:
        futures = {ex.submit(ping_host, ip): ip for ip in hosts}
        for f in as_completed(futures):
            ip = futures[f]
            up = False
            try:
                up = f.result()
            except:
                pass
            rec = results.setdefault(ip, {})
            rec["status"]       = "Up" if up else "Down"
            rec["last_checked"] = now_str if up else rec.get("last_checked", now_str)
            mac = get_arp_mac(ip)
            if mac:
                rec["mac_address"] = mac

        # 2) Nmap fallback
    down_ips = [ip for ip, d in results.items() if d["status"] == "Down"]
    if down_ips:
        nm_data = nmap_probe(down_ips)
        for ip, info in nm_data.items():
            rec = results.setdefault(ip, {})
            rec.update(info)
            rec.setdefault("status", "Up")
            rec.setdefault("last_checked", now_str)

    # 2.5) Override hostname from DB assignment if present
    for ip, rec in results.items():
        if rec.get("status") != "Up":
            continue

        row    = await db.execute(select(IP).where(IP.ip_address == ip))
        ip_rec = row.scalars().first()
        if not ip_rec:
            continue

        if ip_rec.owner_type == OwnerType.user:
            user = await db.get(User, ip_rec.owner_id)
            rec["hostname"] = user.username if user else None
        elif ip_rec.owner_type == OwnerType.device:
            dev = await db.get(Device, ip_rec.owner_id)
            rec["hostname"] = dev.hostname if dev else None
        elif ip_rec.owner_type == OwnerType.server:
            srv = await db.get(Server, ip_rec.owner_id)
            rec["hostname"] = srv.server_name if srv else None

    # 3) Parallel reverse‐DNS for any still‐missing Up hosts
    to_lookup = [
        ip for ip, rec in results.items()
        if rec["status"] == "Up" and not rec.get("hostname")
    ]
    if to_lookup:
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(socket.gethostbyaddr, ip): ip for ip in to_lookup}
            for fut in as_completed(futures, timeout=5):
                ip = futures[fut]
                try:
                    results[ip]["hostname"] = fut.result(timeout=0.1)[0]
                except:
                    pass

    # 3.5) Ensure every Up host has a hostname key
    for rec in results.values():
        if rec.get("status") == "Up" and not rec.get("hostname"):
            rec["hostname"] = "Unknown"

    # 4) Upsert into live_monitor and insert into history
    for ip, rec in results.items():
        status_     = rec.get("status", "Down")
        mac_addr    = rec.get("mac_address")
        raw_vendors = rec.get("raw_vendor", {})

        # Vendor resolution
        if raw_vendors:
            vendor = next(iter(raw_vendors.values()), "Unknown")
        elif mac_addr and _MAC_RE.match(mac_addr):
            try:
                vendor = _mac_parser.get_manuf(mac_addr) or "Unknown"
            except:
                vendor = "Unknown"
        else:
            vendor = "Unknown"

        # use .get() with default to avoid KeyError
        hostname     = rec.get("hostname", "Unknown")
        last_checked = now_str
        last_up      = now_str if status_ == "Up" else None

        # live_monitor upsert
        ins = mysql_insert(LiveMonitor.__table__).values(
            ip           = ip,
            hostname     = hostname,
            mac_address  = mac_addr or "N/A",
            vendor       = vendor,
            status       = status_,
            last_checked = last_checked,
            last_up      = last_up,
        )
        up = ins.on_duplicate_key_update({
            "hostname":     ins.inserted.hostname,
            "mac_address":  ins.inserted.mac_address,
            "vendor":       ins.inserted.vendor,
            "status":       ins.inserted.status,
            "last_checked": ins.inserted.last_checked,
            "last_up":      ins.inserted.last_up,
        })
        await db.execute(up)

        # history insert
        hist = mysql_insert(History.__table__).values(
            ip          = ip,
            hostname    = hostname,
            mac_address = mac_addr or "N/A",
            vendor      = vendor,
            status      = status_,
            scan_time   = last_checked,
        )
        await db.execute(hist)


async def prune_history(db: AsyncSession) -> None:
    """
    Remove history records older than HISTORY_RETENTION_DAYS.
    Runs as its own transaction to avoid deadlocks.
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=HISTORY_RETENTION_DAYS)
    await db.execute(
        delete(History)
        .where(History.scan_time < cutoff)
    )
    await db.commit()




    # 5) Prune old history
    

    await db.commit()

async def scan_nets(nets: list[str], db: AsyncSession) -> None:
    for cidr in nets:
        await scan_cidr(cidr, db)
        await asyncio.sleep(0.5)

    # 6) Prune old history in its own transaction
    await prune_history(db)
