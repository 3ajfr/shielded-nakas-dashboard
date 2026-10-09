#!/usr/bin/env python3
"""Build the static Shielded Nakas market dashboard.

Read-only GETs only. Writes site/index.html (Plotly from the CDN, data inlined)
and appends the live floor to data/floor_history.csv.
"""
from __future__ import annotations

import csv
import json
import statistics
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


def in_filter(f: str, tier: str, sub: str) -> bool:
    if f == "all":
        return True
    if f == "hi":
        return tier in ("Legendary", "Epic")
    return sub == f


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
    floors = {}
    listed_n = {}
    for f in FILTERS:
        asks = sorted(x["ask"] for x in live if in_filter(f, x["tier"], x["sub"]))
        floors[f] = asks[0] if asks else None
        listed_n[f] = len(asks)

    DATA.mkdir(parents=True, exist_ok=True)
    new = not HIST.exists()
    with HIST.open("a", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new:
            w.writerow(HIST_COLS)
        w.writerow([
            now.isoformat(timespec="seconds"),
            pfmt(now),
            floors["all"] or "",
            floors["hi"] or "",
            floors["sub100"] or "",
            floors["sub1k"] or "",
            listed_n["all"],
            usd or "",
        ])
    hist = []
    with HIST.open(newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                dt = parse_utc(r["ts_utc"])
            except Exception:
                continue
            row = {"t": pfmt(dt), "ts": dt.timestamp()}
            for f in FILTERS:
                v = r.get(f"floor_{f}")
                row[f] = int(v) if v not in (None, "") else None
            hist.append(row)
    hist.sort(key=lambda r: r["ts"])
    first_real_ts = hist[0]["ts"] if hist else now.timestamp()

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

    # Before the first recorded live floor: hourly lowest sale, dust excluded.
    approx = {}
    for f in FILTERS:
        per = {}
        for r in rows:
            if r["ts"] >= first_real_ts or r["p"] < ASK_MIN or not in_filter(f, r["tier"], r["sub"]):
                continue
            per[r["h1"]] = min(per.get(r["h1"], 10**18), r["p"])
        approx[f] = [{"t": k, "v": v} for k, v in sorted(per.items())]

    t24, t48 = now.timestamp() - 86400, now.timestamp() - 2 * 86400
    stats = {}
    for f in FILTERS:
        sel = [r for r in rows if in_filter(f, r["tier"], r["sub"])]
        d1 = [r["p"] for r in sel if r["ts"] >= t24]
        d0 = [r["p"] for r in sel if t48 <= r["ts"] < t24]
        m1 = statistics.median(d1) if d1 else None
        m0 = statistics.median(d0) if d0 else None
        stats[f] = {
            "floor": floors[f],
            "listed": listed_n[f],
            "vol24": sum(d1),
            "n24": len(d1),
            "med24": m1,
            "medPrev": m0,
            "chg": (m1 / m0 - 1) if (m1 and m0) else None,
        }

    data = {
        "generatedUtc": now.isoformat(timespec="seconds"),
        "generatedParis": pfmt(now),
        "btcUsd": usd,
        "trades": rows,
        "floorHist": hist,
        "floorApprox": approx,
        "stats": stats,
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
        "floor": floors["all"],
        "floorBtc": btc(floors["all"]) if floors["all"] else None,
        "listed": listed_n["all"],
        "btcUsd": usd,
        "histRows": len(hist),
        "approxHours": len(approx["all"]),
        "supply": len(inscriptions),
        "index": str(out),
        "bytes": out.stat().st_size,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
