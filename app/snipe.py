# app/snipe.py
import httpx
from functools import lru_cache
from typing import Optional

from app.config import settings

# Cache up to 1024 recent lookups in memory:
@lru_cache(maxsize=1024)
def get_hardware_id(asset_tag: str) -> Optional[int]:
    """
    Look up the numeric hardware ID for a given asset_tag in Snipe-IT.
    Returns the ID if found, or None if not.
    """
    url = f"{settings.SNIPE_API}/hardware"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {settings.SNIPE_TOKEN}",
    }
    params = {
        "search": asset_tag,
        "limit": 1,
        "page": 1
    }

    # Use a sync client for simplicity; calls are fast and infrequent.
    with httpx.Client() as client:
        resp = client.get(url, headers=headers, params=params, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()

    # The API returns {"total": N, "rows": [ ... ]}
    if data.get("total", 0) >= 1:
        return data["rows"][0]["id"]
    return None
