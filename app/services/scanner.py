# app/services/scanner.py

import datetime
import ipaddress
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import nmap
import socket
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from app.models import LiveMonitor, History
from app.database import get_db

# how many days to keep in history
HISTORY_RETENTION_DAYS = 14

def ping_host(ip: str, timeout: int = 1) -> bool:
    """Return True if the host responds to a single ping."""
    return subprocess.run(
        ["ping", "-c", "1", "-W", str(timeout), ip],
        stdout=subprocess.DEVNULL
    ).returncode == 0

def get_arp_mac(ip: str) -> str | None:
    """Try to parse the local ARP cache for MAC."""
    out = subprocess.check_output(["arp", "-n", ip], stderr=subprocess.DEVNULL).decode()
    m = re.search(r"(([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})", out)
    return m.group(1).upper() if m else None

def nmap_probe(ips: list[str]) -> dict[str, dict]:
    """Run a light Nmap scan on the list of IPs, return status/vendor."""
    nm = nmap.PortScanner()
    nm.scan(hosts=" ".join(ips), arguments="-sn -PR --version-light")
    results = {}
    for host in nm.all_hosts():
        info = nm[host]
        results[str(host)] = {
            "status": "Up",
            "vendor": info["vendor"] or {},
            "hostname": info.hostname() or None
        }
    return results

async def scan_cidr(
    cidr: str,
    db: AsyncSession
) -> None:
    """
    Scan one CIDR block, update live_monitor and history tables.
    """
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(h) for h in net.hosts()]

    # 1) Parallel ping + ARP
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=80) as ex:
        futures = { ex.submit(ping_host, ip): ip for ip in hosts }
        for f in as_completed(futures):
            ip = futures[f]
            up = f.result()
            rec = results.setdefault(ip, {})
            rec["status"] = "Up" if up else rec.get("status", "Down")
            if up:
                rec["last_checked"] = now
            # ARP
            mac = get_arp_mac(ip)
            if mac:
                rec["mac_address"] = mac

    # 2) Nmap fallback for any still-down hosts
    down_ips = [ip for ip,d in results.items() if d["status"] == "Down"]
    if down_ips:
        nm_data = nmap_probe(down_ips)
        for ip, info in nm_data.items():
            rec = results.setdefault(ip, {})
            rec.update(info)
            rec.setdefault("last_checked", now)
            if info["status"] == "Up":
                rec["status"] = "Up"

    # 3) Write to DB
    for ip, d in results.items():
        status       = d.get("status", "Down")
        mac_address  = d.get("mac_address", "N/A")
        vendor       = next(iter(d.get("vendor", {}).values()), "Unknown")
        hostname     = d.get("hostname") or "Unknown"
        last_checked = now

        # upsert live_monitor
        await db.execute(
            insert(LiveMonitor)
            .values(
                ip=ip,
                hostname=hostname,
                mac_address=mac_address,
                vendor=vendor,
                status=status,
                last_checked=last_checked,
                last_up=(last_checked if status=="Up" else None)
            )
            .on_conflict_do_update(
                index_elements=[LiveMonitor.ip],
                set_={
                    "hostname": hostname,
                    "mac_address": mac_address,
                    "vendor": vendor,
                    "status": status,
                    "last_checked": last_checked,
                    # only bump last_up if newly Up
                    "last_up": 
                      insert(LiveMonitor).excluded.last_up
                      if status=="Up" 
                      else LiveMonitor.last_up
                }
            )
        )

        # insert history row
        await db.execute(
            insert(History).values(
                ip=ip,
                hostname=hostname,
                mac_address=mac_address,
                vendor=vendor,
                status=status,
                scan_time=last_checked
            )
        )

    # 4) prune old history
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=HISTORY_RETENTION_DAYS)
    await db.execute(
        delete(History)
        .where(History.scan_time < cutoff)
    )

async def scan_nets(nets: list[str], db: AsyncSession):
    """
    Orchestrate scanning of multiple CIDRs in series,
    so we avoid blasting the network all at once.
    """
    for cidr in nets:
        await scan_cidr(cidr, db)
        # small pause between blocks to smooth traffic
        await asyncio.sleep(0.5)
