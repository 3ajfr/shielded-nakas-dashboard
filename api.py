"""HTTP clients for the public Shielded Nakas secondary-market APIs.

No API key. Responses are cached next to this file under cache/ (gitignored).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE_SECONDARY = "https://backend-secondary-market-production.up.railway.app/api/secondary"
BASE_SHIELDED = "https://shielded-mint-server-production.up.railway.app/api/shielded"
SLUG = "shielded-nakas-mupv6wja"

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"

DEFAULT_TIMEOUT = 60
MAX_RETRIES = 6
BACKOFF = 1.5


def _get(url: str, timeout: float = DEFAULT_TIMEOUT) -> Any:
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "shielded-nakas-dashboard/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSON from {url}: {exc}") from exc
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in (429, 500, 502, 503, 504):
                sleep = BACKOFF ** attempt
                if exc.code == 429:
                    sleep = max(sleep, 5.0)
                time.sleep(sleep)
                continue
            raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_err = exc
            time.sleep(BACKOFF ** attempt)
            continue
    raise RuntimeError(f"Failed after retries: {url} ({last_err})")


def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{name}.json"


def load_cache(name: str) -> Any | None:
    path = _cache_path(name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def save_cache(name: str, data: Any) -> None:
    _cache_path(name).write_text(json.dumps(data, separators=(",", ":")))


def fetch_collection(refresh: bool = False) -> dict:
    if not refresh:
        cached = load_cache("collection")
        if cached is not None:
            return cached
    data = _get(f"{BASE_SECONDARY}/collections/{SLUG}")
    save_cache("collection", data)
    return data


def fetch_inscriptions(refresh: bool = False) -> dict:
    """Returns {inscriptions, total, listed}. The API currently returns the full set."""
    if not refresh:
        cached = load_cache("inscriptions")
        if cached is not None:
            return cached
    payload = _get(f"{BASE_SECONDARY}/collections/{SLUG}/inscriptions")
    if not isinstance(payload, dict) or "data" not in payload:
        raise RuntimeError("Unexpected inscriptions payload")
    data = payload["data"]
    inscriptions = list(data.get("inscriptions") or [])
    seen: set[str] = set()
    unique = []
    for item in inscriptions:
        iid = item.get("inscriptionId")
        if iid and iid in seen:
            continue
        if iid:
            seen.add(iid)
        unique.append(item)
    out = {
        "inscriptions": unique,
        "total": data.get("total", len(unique)),
        "listed": data.get("listed", sum(1 for item in unique if item.get("isListed"))),
        "fetchedAt": time.time(),
    }
    save_cache("inscriptions", out)
    return out


def fetch_trades(refresh: bool = False) -> list[dict]:
    if not refresh:
        cached = load_cache("trades")
        if cached is not None:
            return cached
    payload = _get(f"{BASE_SECONDARY}/trades/collection/{SLUG}")
    if isinstance(payload, dict):
        trades = payload.get("data") or payload.get("trades") or payload.get("items") or []
    elif isinstance(payload, list):
        trades = payload
    else:
        trades = []
    seen: set[str] = set()
    unique = []
    for trade in trades:
        tid = trade.get("id") or f"{trade.get('txId')}-{trade.get('inscriptionId')}-{trade.get('salePrice')}"
        if tid in seen:
            continue
        seen.add(tid)
        unique.append(trade)
    save_cache("trades", unique)
    return unique


def fetch_listings(refresh: bool = True) -> list[dict]:
    """Live listings cross-check. Default refresh=True (prices change often)."""
    if not refresh:
        cached = load_cache("listings")
        if cached is not None:
            return cached
    payload = _get(f"{BASE_SHIELDED}/listings")
    if isinstance(payload, list):
        listings = payload
    elif isinstance(payload, dict):
        listings = payload.get("data") or payload.get("listings") or []
    else:
        listings = []
    save_cache("listings", listings)
    return listings


def merge_live_prices(inscriptions: list[dict], listings: list[dict] | None) -> list[dict]:
    """Overlay live listing prices onto inscription records when available.

    Listings that disappeared from the live feed are tagged _staleListing.
    Listings flagged cancelling are tagged _cancelling. The dashboard excludes both from the floor.
    """
    if not listings:
        return inscriptions
    by_id = {}
    for listing in listings:
        iid = listing.get("inscriptionId")
        if not iid:
            continue
        try:
            price = int(float(listing.get("price")))
        except (TypeError, ValueError):
            continue
        by_id[iid] = {
            "askPrice": price,
            "pending": bool(listing.get("pending")),
            "cancelling": bool(listing.get("cancelling")),
            "tickets": listing.get("tickets"),
            "saleFee": listing.get("saleFee"),
            "assetId": listing.get("assetId"),
        }
    out = []
    for ins in inscriptions:
        row = dict(ins)
        live = by_id.get(ins.get("inscriptionId"))
        if live:
            row["isListed"] = True
            row["askPrice"] = live["askPrice"]
            row["pendingBuy"] = live["pending"]
            shielded = dict(row.get("shielded") or {})
            shielded.update(
                {
                    "price": live["askPrice"],
                    "pending": live["pending"],
                    "tickets": live.get("tickets", shielded.get("tickets")),
                    "saleFee": _safe_int(live.get("saleFee"), shielded.get("saleFee")),
                    "assetId": live.get("assetId", shielded.get("assetId")),
                }
            )
            row["shielded"] = shielded
            if live.get("cancelling"):
                row["_cancelling"] = True
        out.append(row)
    live_ids = set(by_id)
    if live_ids:
        for row in out:
            if row.get("isListed") and row.get("inscriptionId") not in live_ids:
                row["_staleListing"] = True
    return out


def _safe_int(value, default=None):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
