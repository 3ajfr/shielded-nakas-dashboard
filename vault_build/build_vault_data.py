#!/usr/bin/env python3
"""Server-side data step for 'The Vault'. Uses the official Ord Dropz API key from
.env.orddropz (never published) and writes precomputed public JSON to dashboard/vault/data.json.
Cost per run: 1 unit (/listings). Collection metadata comes from cached secondary API."""
from __future__ import annotations
import json, os, statistics, urllib.request, csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from api import fetch_inscriptions, fetch_trades
from watch_floor_rank import btc_usd, shielded_num, sub_bucket

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "vault"; OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://shielded-public-api-production.up.railway.app"
SUB_BONUS = {"sub10": 2.0, "sub100": 1.0, "sub1k": 0.5, "sub10k": 0.0}

def key():
    k = os.environ.get("ORDDROPZ_API_KEY")
    if not k:
        for line in (ROOT / ".env.orddropz").read_text().splitlines():
            if line.startswith("ORDDROPZ_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"')
    return k

BUDGET_FILE = ROOT / "out" / "api_budget.json"
DAILY_CAP = 500  # hard guard, well under the 5000/day limit

def spend(units: int):
    """Persist a per-UTC-day unit counter; refuse if the call would exceed DAILY_CAP."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try: b = json.loads(BUDGET_FILE.read_text())
    except Exception: b = {}
    if b.get("day") != day: b = {"day": day, "used": 0}
    if b["used"] + units > DAILY_CAP:
        raise SystemExit(f"API budget guard: {b['used']}/{DAILY_CAP} units used today (UTC), refusing call")
    b["used"] += units
    BUDGET_FILE.parent.mkdir(exist_ok=True); BUDGET_FILE.write_text(json.dumps(b))

def official_listings():
    # exactly ONE /listings call (1 unit) per run; /state (20 units) is never used
    spend(1)
    req = urllib.request.Request(BASE + "/listings", headers={"x-api-key": key(), "User-Agent": "nakas-vault"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def rsi(vals, n=14):
    if len(vals) <= n: return None
    g = [max(0, b - a) for a, b in zip(vals, vals[1:])]; l = [max(0, a - b) for a, b in zip(vals, vals[1:])]
    ag, al = sum(g[:n]) / n, sum(l[:n]) / n
    for i in range(n, len(g)):
        ag = (ag * (n - 1) + g[i]) / n; al = (al * (n - 1) + l[i]) / n
    return 100.0 if al == 0 else round(100 - 100 / (1 + ag / al), 1)

def main():
    usd = btc_usd() or 0
    ins = fetch_inscriptions(refresh=False).get("inscriptions") or []
    lst = official_listings()
    live = {l["inscriptionId"]: int(l["price"]) for l in lst
            if not l.get("pending") and not l.get("cancelling") and int(l.get("price") or 0) >= 1000}
    trades = [t for t in fetch_trades(refresh=True) if t.get("status") == "completed" and t.get("salePrice")]
    trades.sort(key=lambda t: t.get("completedAt") or t.get("createdAt") or "")
    by_id = {i["inscriptionId"]: i for i in ins}
    asks = sorted(live.values()); floor = asks[0] if asks else None
    # fair value: median of last 60 sales of same tier, adjusted by sub bucket premium vs all
    recent = trades[-400:]
    def med(xs): return statistics.median(xs) if xs else None
    meta = {}
    for t in recent:
        i = by_id.get(t["inscriptionId"]); 
        if not i: continue
        meta.setdefault(("tier", i.get("rarityTier")), []).append(t["salePrice"])
        meta.setdefault(("sub", sub_bucket(shielded_num(i))), []).append(t["salePrice"])
    allmed = med([t["salePrice"] for t in recent]) or floor or 1
    rows = []
    for i in ins:
        n = shielded_num(i); sub = sub_bucket(n); tier = i.get("rarityTier") or "Common"
        tm = med(meta.get(("tier", tier), [])[-60:]) or allmed
        sm = med(meta.get(("sub", sub), [])[-60:]) or allmed
        fair = int(max(tm, sm, floor or 0) * (1.0 if tm >= sm else 1.0))
        ask = live.get(i["inscriptionId"])
        snipe = bool(ask and (ask <= 0.75 * fair or (floor and len(asks) > 1 and ask <= 0.8 * asks[1] and ask == floor)))
        rows.append({"id": i["inscriptionId"], "no": int((i.get("name") or "#0").split("#")[-1]),
                     "rank": i.get("rarityRank"), "tier": tier, "num": n, "sub": sub,
                     "traits": {t["trait_type"]: t["value"] for t in i.get("traits") or []
                                if t["trait_type"] not in ("Shielded #",)},
                     "ask": ask, "fair": fair, "snipe": snipe})
    rows.sort(key=lambda r: r["no"])
    # price series from trades (daily) + floor history
    daily = {}
    for t in trades:
        d = (t.get("completedAt") or t["createdAt"])[:10]
        daily.setdefault(d, []).append(t["salePrice"])
    series = [{"d": d, "med": int(statistics.median(v)), "lo": min(v), "hi": max(v), "vol": sum(v), "n": len(v)}
              for d, v in sorted(daily.items())]
    hourly = {}
    for t in trades[-600:]:
        hourly.setdefault((t.get("completedAt") or t["createdAt"])[:13], []).append(t["salePrice"])
    hp = [int(statistics.median(v)) for _, v in sorted(hourly.items())]
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    vol24 = sum(t["salePrice"] for t in trades if (t.get("completedAt") or t["createdAt"]) >= since)
    n24 = sum(1 for t in trades if (t.get("completedAt") or t["createdAt"]) >= since)
    last_sales = [{"no": by_id.get(t["inscriptionId"], {}).get("name", "").split("#")[-1], "p": t["salePrice"],
                   "at": t.get("completedAt") or t["createdAt"]} for t in trades[-12:]][::-1]
    listed = [r for r in rows if r["ask"]]
    snipes = sorted([r for r in listed if r["snipe"]], key=lambda r: r["ask"] / r["fair"])
    best = (snipes or sorted(listed, key=lambda r: r["ask"] / r["fair"]))[:1]
    # floor history (repo data/floor_history.csv written by the pages workflow), daily close + 24h-ago value
    fh = {}; ago = None
    for hp_ in (ROOT.parent / "data" / "floor_history.csv", ROOT / "out" / "floor_history.csv"):
        if hp_.exists():
            for r in csv.DictReader(hp_.open()):
                try: v = int(float(r["floor_all"])); ts = r["ts_utc"]
                except Exception: continue
                fh[ts[:10]] = v
                if ts <= (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(): ago = v
            break
    for s_ in series:
        s_["floor"] = fh.get(s_["d"]); s_["floorSrc"] = "ask" if s_["d"] in fh else "lowsale"
        if s_["floor"] is None: s_["floor"] = s_["lo"]
    if series: series[-1]["floor"] = floor; series[-1]["floorSrc"] = "ask"
    if ago is None and len(series) > 1: ago = series[-2]["floor"]
    data = {"generatedAt": datetime.now(timezone.utc).isoformat(), "btcUsd": usd, "floor": floor,
            "floor2": asks[1] if len(asks) > 1 else None, "listed": len(listed), "total": len(rows),
            "vol24": vol24, "floor24hAgo": ago, "sales24": n24, "rsi": rsi(hp), "series": series[-30:], "lastSales": last_sales,
            "nakaOfDay": best[0]["no"] if best else None, "subBonus": SUB_BONUS,
            "source": "Ord Dropz Shielded public API (/listings) + secondary market trades", "items": rows}
    (OUT / "data.json").write_text(json.dumps(data, separators=(",", ":")))
    print(f"ok items={len(rows)} listed={len(listed)} floor={floor} snipes={len(snipes)} rsi={data['rsi']}")

if __name__ == "__main__":
    main()
