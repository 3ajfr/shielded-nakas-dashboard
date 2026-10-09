#!/usr/bin/env python3
"""Build the static Shielded Nakas dashboard.

Read-only GETs. Writes site/index.html and appends data/floor_history.csv.
Plotly is loaded from a CDN by the page. Paths are relative to this file.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from api import fetch_inscriptions, fetch_listings, fetch_trades, merge_live_prices
from market import ASK_MIN, btc, btc_usd, ask_sats, shielded_num, sub_bucket
from rarity import rarity_fields

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"
HIST = DATA / "floor_history.csv"
TEMPLATE = ROOT / "dashboard_template.html"
PARIS = ZoneInfo("Europe/Paris")
FILTERS = ("all", "hi", "sub100", "sub1k")
HIST_COLS = [
    "ts_utc",
    "ts_paris",
    "floor_all",
    "floor_hi",
    "floor_sub100",
    "floor_sub1k",
    "listed_live",
    "btc_usd",
]


def in_filter(name: str, tier: str, sub: str) -> bool:
    if name == "all":
        return True
    if name == "hi":
        return tier in ("Legendary", "Epic")
    return sub == name


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def pfmt(dt: datetime) -> str:
    return dt.astimezone(PARIS).strftime("%Y-%m-%d %H:%M")


def bucket_keys(dt: datetime) -> dict[str, str]:
    local = dt.astimezone(PARIS)
    hour = local.replace(minute=0, second=0, microsecond=0)
    h4 = hour.replace(hour=(hour.hour // 4) * 4)
    day = hour.replace(hour=0)
    fmt = "%Y-%m-%d %H:%M"
    return {"h1": hour.strftime(fmt), "h4": h4.strftime(fmt), "d1": day.strftime(fmt)}


def approx_floor(rows: list[dict], first_real_ts: float, name: str) -> list[dict]:
    """Hourly lowest sale before real floor history. Sales under ASK_MIN sats are excluded."""
    per: dict[str, int] = {}
    for row in rows:
        if row["ts"] >= first_real_ts or row["p"] < ASK_MIN or not in_filter(name, row["tier"], row["sub"]):
            continue
        per[row["h1"]] = min(per.get(row["h1"], 10**18), row["p"])
    return [{"t": key, "v": value} for key, value in sorted(per.items())]


def _self_check() -> None:
    assert sub_bucket(0) == "sub10"
    assert sub_bucket(9) == "sub10"
    assert sub_bucket(10) == "sub100"
    assert sub_bucket(99) == "sub100"
    assert sub_bucket(100) == "sub1k"
    assert sub_bucket(999) == "sub1k"
    assert sub_bucket(1000) == "sub10k"
    assert sub_bucket(None) == "?"
    assert in_filter("all", "Common", "sub10k")
    assert in_filter("hi", "Legendary", "sub10k")
    assert in_filter("hi", "Epic", "sub1k")
    assert not in_filter("hi", "Rare", "sub100")
    assert in_filter("sub100", "Rare", "sub100")
    assert not in_filter("sub1k", "Rare", "sub100")
    rows = [
        {"ts": 1, "h1": "a", "p": 1000, "tier": "Rare", "sub": "sub1k"},
        {"ts": 2, "h1": "a", "p": 8000, "tier": "Rare", "sub": "sub1k"},
        {"ts": 3, "h1": "a", "p": 9000, "tier": "Legendary", "sub": "sub100"},
        {"ts": 10, "h1": "b", "p": 7000, "tier": "Epic", "sub": "sub1k"},
    ]
    assert approx_floor(rows, 5, "all") == [{"t": "a", "v": 8000}]
    assert approx_floor(rows, 5, "hi") == [{"t": "a", "v": 9000}]
    assert approx_floor(rows, 5, "sub100") == [{"t": "a", "v": 9000}]
    assert approx_floor(rows, 5, "sub1k") == [{"t": "a", "v": 8000}]
    assert ask_sats({"askPrice": "550000"}) == 550000
    assert ask_sats({"shielded": {"price": 12000}}) == 12000
    assert shielded_num({"traits": [{"trait_type": "Shielded #", "value": "42"}]}) == 42


def _load_history() -> list[dict]:
    hist = []
    if not HIST.exists():
        return hist
    with HIST.open(newline="") as fh:
        for record in csv.DictReader(fh):
            try:
                dt = parse_utc(record["ts_utc"])
            except (TypeError, ValueError):
                continue
            row = {"t": pfmt(dt), "ts": dt.timestamp()}
            for name in FILTERS:
                raw = record.get(f"floor_{name}")
                row[name] = int(raw) if raw not in (None, "") else None
            hist.append(row)
    hist.sort(key=lambda row: row["ts"])
    return hist


def _append_history(now: datetime, floors: dict, listed_all: int, usd: float | None) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    new = not HIST.exists() or HIST.stat().st_size == 0
    with HIST.open("a", newline="") as fh:
        writer = csv.writer(fh)
        if new:
            writer.writerow(HIST_COLS)
        writer.writerow(
            [
                now.isoformat(timespec="seconds"),
                pfmt(now),
                floors["all"] if floors["all"] is not None else "",
                floors["hi"] if floors["hi"] is not None else "",
                floors["sub100"] if floors["sub100"] is not None else "",
                floors["sub1k"] if floors["sub1k"] is not None else "",
                listed_all,
                usd if usd is not None else "",
            ]
        )


def main() -> int:
    _self_check()
    now = datetime.now(timezone.utc)
    usd = btc_usd()
    ins_payload = fetch_inscriptions(refresh=True)
    inscriptions = ins_payload.get("inscriptions") or []
    by_id = {item.get("inscriptionId"): item for item in inscriptions}
    listings = fetch_listings(refresh=True)
    trades = fetch_trades(refresh=True)

    merged = merge_live_prices(inscriptions, listings)
    live = []
    for ins in merged:
        if not ins.get("isListed") or ins.get("_staleListing") or ins.get("_cancelling"):
            continue
        ask = ask_sats(ins)
        if ask is None or ask < ASK_MIN:
            continue
        fields = rarity_fields(ins)
        number = shielded_num(ins)
        live.append(
            {
                "ask": ask,
                "tier": fields.get("rarityTier") or "",
                "sub": sub_bucket(number),
            }
        )
    floors: dict[str, int | None] = {}
    listed_n: dict[str, int] = {}
    for name in FILTERS:
        asks = sorted(item["ask"] for item in live if in_filter(name, item["tier"], item["sub"]))
        floors[name] = asks[0] if asks else None
        listed_n[name] = len(asks)

    _append_history(now, floors, listed_n["all"], usd)
    hist = _load_history()
    first_real_ts = hist[0]["ts"] if hist else now.timestamp()

    rows = []
    for trade in trades:
        if trade.get("status") != "completed":
            continue
        stamp = trade.get("completedAt") or trade.get("createdAt")
        try:
            dt = parse_utc(stamp)
            price = int(trade.get("salePrice"))
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        ins = by_id.get(trade.get("inscriptionId")) or {}
        fields = rarity_fields(ins) if ins else {}
        number = shielded_num(ins) if ins else None
        rows.append(
            {
                "ts": dt.timestamp(),
                "t": pfmt(dt),
                "p": price,
                "tier": fields.get("rarityTier") or "?",
                "sub": sub_bucket(number),
                **bucket_keys(dt),
            }
        )
    rows.sort(key=lambda row: row["ts"])

    approx = {name: approx_floor(rows, first_real_ts, name) for name in FILTERS}
    for series in approx.values():
        for point in series:
            if point["v"] < ASK_MIN:
                raise SystemExit("approximation included a sale under 5000 sats")

    t24 = now.timestamp() - 86400
    t48 = now.timestamp() - 2 * 86400
    stats = {}
    for name in FILTERS:
        selected = [row for row in rows if in_filter(name, row["tier"], row["sub"])]
        day = [row["p"] for row in selected if row["ts"] >= t24]
        prev = [row["p"] for row in selected if t48 <= row["ts"] < t24]
        med_day = statistics.median(day) if day else None
        med_prev = statistics.median(prev) if prev else None
        stats[name] = {
            "floor": floors[name],
            "listed": listed_n[name],
            "vol24": sum(day),
            "n24": len(day),
            "med24": med_day,
            "medPrev": med_prev,
            "chg": (med_day / med_prev - 1) if (med_day and med_prev) else None,
        }

    client_trades = [
        {"t": row["t"], "p": row["p"], "tier": row["tier"], "sub": row["sub"], "h1": row["h1"], "h4": row["h4"], "d1": row["d1"]}
        for row in rows
    ]
    client_hist = [{key: row[key] for key in ("t", *FILTERS)} for row in hist]
    data = {
        "generatedUtc": now.isoformat(timespec="seconds"),
        "generatedParis": pfmt(now),
        "btcUsd": usd,
        "trades": client_trades,
        "floorHist": client_hist,
        "floorApprox": approx,
        "stats": stats,
        "supply": len(inscriptions),
        "range": [rows[0]["t"], rows[-1]["t"]] if rows else None,
    }
    payload = (
        json.dumps(data, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    template = TEMPLATE.read_text()
    if "__DATA__" not in template:
        raise SystemExit("dashboard_template.html is missing __DATA__")
    html = template.replace("__DATA__", payload)
    if "__DATA__" in html or "telegram" in html.lower():
        raise SystemExit("generated page failed sanity checks")
    for needle in ("APPROXIMATION", 'content="300"', "plotly", "Legendary+Epic", "Europe/Paris"):
        if needle not in html:
            raise SystemExit(f"generated page is missing {needle}")

    SITE.mkdir(parents=True, exist_ok=True)
    index = SITE / "index.html"
    tmp = SITE / "index.html.tmp"
    tmp.write_text(html)
    tmp.replace(index)
    summary = {
        "ok": True,
        "index": "site/index.html",
        "bytes": index.stat().st_size,
        "trades": len(rows),
        "range": data["range"],
        "floor": floors["all"],
        "floor_btc": btc(floors["all"]) if floors["all"] else None,
        "listed": listed_n["all"],
        "supply": len(inscriptions),
        "btcUsd": usd,
        "histRows": len(hist),
        "approxHours": len(approx["all"]),
        "stats24": {name: {"n": stats[name]["n24"], "vol": stats[name]["vol24"]} for name in FILTERS},
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
