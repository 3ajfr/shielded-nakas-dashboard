#!/usr/bin/env python3
"""Build the static Shielded Nakas market dashboard.

Read-only GETs only. Writes site/index.html (Plotly from the CDN, data inlined)
and appends the live floor to data/floor_history.csv.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from api import fetch_inscriptions, fetch_listings, fetch_trades, merge_live_prices
from market import ASK_MIN, ask_sats, btc, btc_usd, shielded_num, sub_bucket
from rarity import rarity_fields

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"
HIST = DATA / "floor_history.csv"
TEMPLATE = ROOT / "dashboard_template.html"
PARIS = ZoneInfo("Europe/Paris")
TIER_KEYS = ("all", "hi", "Legendary", "Epic", "Rare", "Uncommon", "Common")
SUB_KEYS = ("all", "sub10", "sub100", "sub1k", "sub10k")
RANK_KEYS = ("all", "10", "50", "100", "500", "1000")
HIST_COLS = [
    "ts_utc",
    "ts_paris",
    "floor_all",
    "floor_hi",
    "floor_sub100",
    "floor_sub1k",
    "listed_live",
    "btc_usd",
    "floors_json",
]
LEGACY_FLOOR_KEYS = {
    "floor_all": "all|all|all",
    "floor_hi": "hi|all|all",
    "floor_sub100": "all|sub100|all",
    "floor_sub1k": "all|sub1k|all",
}


def floor_key(tier: str, sub: str, rank: str) -> str:
    return f"{tier}|{sub}|{rank}"


def match_slice(tier: str, sub: str, rank: int | None, ft: str, fs: str, fr: str) -> bool:
    if ft == "hi":
        if tier not in ("Legendary", "Epic"):
            return False
    elif ft != "all" and tier != ft:
        return False
    if fs != "all" and sub != fs:
        return False
    if fr != "all":
        if rank is None or rank > int(fr):
            return False
    return True


def slice_floors(live: list[dict]) -> dict[str, int]:
    """Lowest ask for every rareté × numéro × rang combination that has a listing."""
    best: dict[str, int] = {}
    for item in live:
        tier, sub, rank, ask = item["tier"], item["sub"], item["rank"], item["ask"]
        for ft in TIER_KEYS:
            if ft == "hi":
                if tier not in ("Legendary", "Epic"):
                    continue
            elif ft != "all" and tier != ft:
                continue
            for fs in SUB_KEYS:
                if fs != "all" and sub != fs:
                    continue
                for fr in RANK_KEYS:
                    if fr != "all" and (rank is None or rank > int(fr)):
                        continue
                    k = floor_key(ft, fs, fr)
                    cur = best.get(k)
                    if cur is None or ask < cur:
                        best[k] = ask
    return best


def parse_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def pfmt(dt: datetime) -> str:
    return dt.astimezone(PARIS).strftime("%Y-%m-%d %H:%M")


def bucket_keys(dt: datetime) -> dict:
    p = dt.astimezone(PARIS)
    h1 = p.replace(minute=0, second=0, microsecond=0)
    h4 = h1.replace(hour=(h1.hour // 4) * 4)
    d1 = h1.replace(hour=0)
    f = "%Y-%m-%d %H:%M"
    return {"h1": h1.strftime(f), "h4": h4.strftime(f), "d1": d1.strftime(f)}


def js_json(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return (
        raw.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def main() -> int:
    now = datetime.now(timezone.utc)
    usd = btc_usd()
    # Always hit the network. Traits and tiers come from the inscriptions API.
    ins_payload = fetch_inscriptions(refresh=True)
    inscriptions = ins_payload.get("inscriptions") or []
    by_id = {i.get("inscriptionId"): i for i in inscriptions}
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
        rf = rarity_fields(ins)
        n = shielded_num(ins)
        live.append({
            "ask": ask,
            "tier": rf.get("rarityTier") or "",
            "sub": sub_bucket(n),
            "rank": rf.get("rarityRank"),
            "num": n,
        })
    floors = slice_floors(live)
    listed_all = sum(1 for x in live if match_slice(x["tier"], x["sub"], x["rank"], "all", "all", "all"))

    DATA.mkdir(parents=True, exist_ok=True)
    previous: list[dict] = []
    if HIST.exists():
        with HIST.open(newline="") as fh:
            previous = list(csv.DictReader(fh))
    previous.append({
        "ts_utc": now.isoformat(timespec="seconds"),
        "ts_paris": pfmt(now),
        "floor_all": floors.get("all|all|all") or "",
        "floor_hi": floors.get("hi|all|all") or "",
        "floor_sub100": floors.get("all|sub100|all") or "",
        "floor_sub1k": floors.get("all|sub1k|all") or "",
        "listed_live": listed_all,
        "btc_usd": usd or "",
        "floors_json": json.dumps(floors, separators=(",", ":")),
    })
    with HIST.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HIST_COLS, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for record in previous:
            writer.writerow({col: record.get(col, "") for col in HIST_COLS})

    hist = []
    for record in previous:
        try:
            dt = parse_utc(record["ts_utc"])
        except Exception:
            continue
        merged_floors: dict[str, int] = {}
        for col, key in LEGACY_FLOOR_KEYS.items():
            v = record.get(col)
            if v not in (None, ""):
                merged_floors[key] = int(v)
        raw = record.get("floors_json") or ""
        if raw:
            try:
                for k, v in json.loads(raw).items():
                    if v not in (None, ""):
                        merged_floors[k] = int(v)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        hist.append({"t": pfmt(dt), "ts": dt.timestamp(), "floors": merged_floors})
    hist.sort(key=lambda r: r["ts"])

    rows = []
    for t in trades:
        if t.get("status") != "completed":
            continue
        ts = t.get("completedAt") or t.get("createdAt")
        try:
            dt = parse_utc(ts)
            p = int(t.get("salePrice"))
        except Exception:
            continue
        ins = by_id.get(t.get("inscriptionId")) or {}
        rf = rarity_fields(ins) if ins else {}
        n = shielded_num(ins) if ins else None
        rows.append({
            "ts": dt.timestamp(),
            "t": pfmt(dt),
            "p": p,
            "tier": rf.get("rarityTier") or "?",
            "sub": sub_bucket(n),
            "num": n,
            "rank": rf.get("rarityRank"),
            **bucket_keys(dt),
        })
    rows.sort(key=lambda r: r["ts"])

    # One point per filter only when its floor changes, so the page stays small
    # while data/floor_history.csv keeps every snapshot.
    series: dict[str, list] = {}
    prev: dict[str, int | None] = {}
    for row in hist:
        cur = row["floors"]
        for k in set(prev) | set(cur):
            v = cur.get(k)
            if prev.get(k) != v:
                series.setdefault(k, []).append({"t": row["t"], "ts": row["ts"], "v": v})
                prev[k] = v

    data = {
        "generatedUtc": now.isoformat(timespec="seconds"),
        "generatedParis": pfmt(now),
        "btcUsd": usd,
        "trades": rows,
        "live": [{"ask": x["ask"], "tier": x["tier"], "sub": x["sub"], "rank": x["rank"]} for x in live],
        "floorSeries": series,
        "supply": len(inscriptions),
        "range": [rows[0]["t"], rows[-1]["t"]] if rows else None,
    }
    html = TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", js_json(data))
    if "__DATA__" in html:
        raise SystemExit("template placeholder __DATA__ was not replaced")
    SITE.mkdir(parents=True, exist_ok=True)
    tmp = SITE / "index.html.tmp"
    tmp.write_text(html, encoding="utf-8")
    out = SITE / "index.html"
    tmp.replace(out)
    print(json.dumps({
        "ok": True,
        "trades": len(rows),
        "range": data["range"],
        "floor": floors.get("all|all|all"),
        "floorBtc": btc(floors["all|all|all"]) if floors.get("all|all|all") else None,
        "listed": listed_all,
        "btcUsd": usd,
        "histRows": len(hist),
        "floorKeys": len(floors),
        "supply": len(inscriptions),
        "index": str(out),
        "bytes": out.stat().st_size,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
