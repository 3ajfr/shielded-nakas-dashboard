"""Price and Shielded-number helpers for the market dashboard.

Read-only. No alerts, no saved state, no messaging.
"""
from __future__ import annotations

import json
import urllib.request

ASK_MIN = 5_000
SATS_PER_BTC = 100_000_000

_BTC_USD: float | None = None
_BTC_USD_DONE = False


def btc_usd() -> float | None:
    """Live BTC/USD (mempool.space, fallback CoinGecko); None if unavailable."""
    global _BTC_USD, _BTC_USD_DONE
    if _BTC_USD_DONE:
        return _BTC_USD
    _BTC_USD_DONE = True
    for url, path in (
        ("https://mempool.space/api/v1/prices", ("USD",)),
        ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", ("bitcoin", "usd")),
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "shielded-nakas-dashboard/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                d = json.load(r)
            for k in path:
                d = d[k]
            if float(d) > 0:
                _BTC_USD = float(d)
                return _BTC_USD
        except Exception:
            continue
    return None


def btc(sats: int | float) -> str:
    s = f"{sats / SATS_PER_BTC:.8f}".rstrip("0").rstrip(".") + " BTC"
    px = btc_usd()
    if px:
        s += f" (~${sats / SATS_PER_BTC * px:,.0f})"
    return s


def shielded_num(ins: dict) -> int | None:
    for t in ins.get("traits") or []:
        if t.get("trait_type") == "Shielded #":
            try:
                return int(t.get("value"))
            except (TypeError, ValueError):
                return None
    sh = ins.get("shielded") or {}
    try:
        return int(sh.get("assetId"))
    except (TypeError, ValueError):
        return None


def sub_bucket(n: int | None) -> str:
    if n is None:
        return "?"
    if n < 10:
        return "sub10"
    if n < 100:
        return "sub100"
    if n < 1000:
        return "sub1k"
    return "sub10k"


def ask_sats(ins: dict) -> int | None:
    v = ins.get("askPrice")
    if v is not None:
        try:
            return int(float(v))
        except (TypeError, ValueError):
            pass
    sh = ins.get("shielded") or {}
    try:
        return int(float(sh.get("price")))
    except (TypeError, ValueError):
        return None
