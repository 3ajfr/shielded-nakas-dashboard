"""BTC price and Shielded-number helpers.

Public market data only. No alerts, no saved state, no messaging.
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
                data = json.load(r)
            for key in path:
                data = data[key]
            if float(data) > 0:
                _BTC_USD = float(data)
                return _BTC_USD
        except Exception:
            continue
    return None


def btc(sats: int | float) -> str:
    text = f"{sats / SATS_PER_BTC:.8f}".rstrip("0").rstrip(".") + " BTC"
    px = btc_usd()
    if px:
        text += f" (~${sats / SATS_PER_BTC * px:,.0f})"
    return text


def shielded_num(ins: dict) -> int | None:
    for trait in ins.get("traits") or []:
        if trait.get("trait_type") == "Shielded #":
            try:
                return int(trait.get("value"))
            except (TypeError, ValueError):
                return None
    shielded = ins.get("shielded") or {}
    try:
        return int(shielded.get("assetId"))
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
    value = ins.get("askPrice")
    if value is not None:
        try:
            return int(value)
        except (TypeError, ValueError):
            pass
    shielded = ins.get("shielded") or {}
    try:
        return int(shielded.get("price"))
    except (TypeError, ValueError):
        return None
