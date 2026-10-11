#!/usr/bin/env python3
"""Watch: CALL Legendary/Epic near floor, or any steal listing vs robust floor."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from api import fetch_inscriptions, fetch_listings, merge_live_prices
from rarity import naka_number, rarity_fields

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
STATE = OUT / "watch_state.json"
TG = Path("/home/box/sand-data/agents/042db9d8-156f-4521-a54d-b20969335650/memory/telegram_send.py")

CALL_TIERS = {"Legendary", "Epic"}
FLOOR_MULT = 1.05  # Leg/Epic ask <= floor * 1.05
STEAL_MULT = 0.85  # any ask <= robust_floor * 0.85 = misprice / steal
ASK_MIN, ASK_MAX = 5_000, 5_000_000
SATS_PER_BTC = 100_000_000


_BTC_USD: float | None = None
_BTC_USD_DONE = False


def btc_usd() -> float | None:
    """Live BTC/USD (mempool.space, fallback CoinGecko); None if unavailable."""
    global _BTC_USD, _BTC_USD_DONE
    if _BTC_USD_DONE:
        return _BTC_USD
    _BTC_USD_DONE = True
    import urllib.request
    for url, path in (
        ("https://mempool.space/api/v1/prices", ("USD",)),
        ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", ("bitcoin", "usd")),
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
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


# Shielded # sub buckets: CALL if ask <= floor * mult (global floor)
SUB_MULT = {"sub10": 5.0, "sub100": 1.5, "sub1k": 1.05}
SUB_STEAL = 0.85  # any sub listing <= 85% of its bucket's 2nd-cheapest ask


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


def _ask(ins: dict) -> int | None:
    for key in ("askPrice",):
        v = ins.get(key)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    sh = ins.get("shielded") or {}
    try:
        return int(sh.get("price"))
    except (TypeError, ValueError):
        return None


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"called": {}, "last_top": []}


def save_state(st: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))


def send_tg(text: str) -> dict | None:
    if not TG.exists():
        return None
    try:
        r = subprocess.run(
            [sys.executable, str(TG), text],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            return json.loads(r.stdout.strip() or "{}")
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": (r.stderr or r.stdout)[:300]}


def main() -> int:
    payload = fetch_inscriptions(refresh=False)
    try:
        listings = fetch_listings(refresh=True)
    except Exception:
        listings = []
    inscriptions = merge_live_prices(payload.get("inscriptions") or [], listings)

    listed = []
    for ins in inscriptions:
        if not ins.get("isListed"):
            continue
        # Live-only: skip listings that vanished from the live endpoint
        if listings and (ins.get("_staleListing") or ins.get("_cancelling")):
            continue
        ask = _ask(ins)
        if ask is None or ask < ASK_MIN or ask > ASK_MAX:
            continue
        rf = rarity_fields(ins)
        rank = rf.get("rarityRank")
        if rank is None:
            continue
        listed.append(
            {
                "inscriptionId": ins.get("inscriptionId") or "",
                "naka": naka_number(ins),
                "name": ins.get("name") or "",
                "ask": ask,
                "ask_btc": btc(ask),
                "rarityRank": int(rank),
                "rarityScore": rf.get("rarityScore"),
                "rarityTier": rf.get("rarityTier") or "",
                "shieldedNum": shielded_num(ins),
                "sub": sub_bucket(shielded_num(ins)),
                "pending": bool(ins.get("pendingBuy") or (ins.get("shielded") or {}).get("pending")),
            }
        )

    if not listed:
        print(json.dumps({"call": False, "reason": "no_listings"}))
        return 0

    asks_sorted = sorted(x["ask"] for x in listed)
    floor = asks_sorted[0]
    floor_btc = btc(floor)
    # Robust floor = 2nd-cheapest (so a steal doesn't redefine "floor"),
    # else previous floor from state, else current floor.
    st = load_state()
    prev_floor = st.get("floor")
    if len(asks_sorted) >= 2:
        robust_floor = asks_sorted[1]
    elif isinstance(prev_floor, (int, float)) and prev_floor > 0:
        robust_floor = int(prev_floor)
    else:
        robust_floor = floor

    for x in listed:
        x["value_score"] = (10000 - min(x["rarityRank"], 9999)) / max(x["ask"] / floor, 0.01)

    hi_tier = [x for x in listed if x["rarityTier"] in CALL_TIERS]
    top_ranks = sorted(hi_tier, key=lambda x: (x["rarityRank"], x["ask"]))[:15]
    if not top_ranks:
        top_ranks = sorted(listed, key=lambda x: (x["rarityRank"], x["ask"]))[:15]
    top_value = sorted(hi_tier or listed, key=lambda x: -x["value_score"])[:10]

    near_floor = floor * FLOOR_MULT
    steal_ceil = robust_floor * STEAL_MULT

    triggers: list[dict] = []
    seen_ids: set[str] = set()

    # 1) Steal: any rank, ask well under robust floor (likely misprice)
    for x in listed:
        if x["ask"] <= steal_ceil:
            t = dict(x)
            t["reason"] = "steal"
            t["discount_vs_robust"] = round(1 - x["ask"] / robust_floor, 4)
            triggers.append(t)
            seen_ids.add(x["inscriptionId"])

    # 2) Legendary/Epic at/near floor
    for x in listed:
        if x["inscriptionId"] in seen_ids:
            continue
        if x["rarityTier"] in CALL_TIERS and x["ask"] <= near_floor:
            t = dict(x)
            t["reason"] = "hi_tier_floor"
            triggers.append(t)
            seen_ids.add(x["inscriptionId"])

    # 3) Shielded # sub buckets
    sub_floors: dict[str, dict] = {}
    for b in ("sub10", "sub100", "sub1k", "sub10k"):
        asks = sorted(x["ask"] for x in listed if x["sub"] == b)
        sub_floors[b] = {
            "listed": len(asks),
            "floor": asks[0] if asks else None,
            "robust": asks[1] if len(asks) >= 2 else (asks[0] if asks else None),
        }
    for x in listed:
        if x["inscriptionId"] in seen_ids:
            continue
        b = x["sub"]
        hit = None
        if b in SUB_MULT and x["ask"] <= floor * SUB_MULT[b]:
            hit = "sub_floor"
        elif b in SUB_MULT:
            rb = sub_floors[b]["robust"]
            if rb and sub_floors[b]["listed"] >= 2 and x["ask"] <= rb * SUB_STEAL:
                hit = "sub_steal"
        if hit:
            t = dict(x)
            t["reason"] = hit
            triggers.append(t)
            seen_ids.add(x["inscriptionId"])

    # User 2026-10-08: ignore listings with a pending purchase (likely already being bought)
    triggers = [t for t in triggers if not t.get("pending")]

    order = {"steal": 0, "sub_steal": 1, "sub_floor": 2, "hi_tier_floor": 3}
    triggers.sort(key=lambda x: (order.get(x["reason"], 9), x["ask"], x["rarityRank"]))

    called = st.get("called") or {}
    new_calls = []
    for t in triggers:
        key = f"{t['inscriptionId']}:{t['ask']}:{t['reason']}"
        if key in called:
            continue
        new_calls.append(t)
        called[key] = datetime.now(timezone.utc).isoformat()

    if len(called) > 200:
        items = sorted(called.items(), key=lambda kv: kv[1])[-200:]
        called = dict(items)

    st["called"] = called
    st["floor"] = floor
    st["floor_btc"] = floor_btc
    st["robust_floor"] = robust_floor
    st["listed"] = len(listed)
    st["hi_tier_listed"] = len(hi_tier)
    st["last_top"] = top_ranks[:10]
    st["checkedAt"] = datetime.now(timezone.utc).isoformat()
    save_state(st)

    OUT.mkdir(parents=True, exist_ok=True)
    snap = {
        "checkedAt": st["checkedAt"],
        "floor": floor,
        "floor_btc": floor_btc,
        "robust_floor": robust_floor,
        "robust_floor_btc": btc(robust_floor),
        "steal_ceil": steal_ceil,
        "steal_ceil_btc": btc(steal_ceil),
        "listed": len(listed),
        "hi_tier_listed": len(hi_tier),
        "near_floor": near_floor,
        "near_floor_btc": btc(near_floor),
        "triggers_active": triggers,
        "new_calls": new_calls,
        "top_ranks": top_ranks[:10],
        "top_value": top_value[:10],
        "sub_floors": {k: dict(v, floor_btc=btc(v["floor"]) if v["floor"] else None) for k, v in sub_floors.items()},
        "best_subs": {
            b: sorted([x for x in listed if x["sub"] == b], key=lambda x: (x["ask"], x["shieldedNum"] or 0))[:5]
            for b in ("sub10", "sub100", "sub1k")
        },
    }
    (OUT / "watch_latest.json").write_text(json.dumps(snap, indent=2))

    lines = [
        f"floor={floor_btc} robust={btc(robust_floor)} steal≤{btc(steal_ceil)} "
        f"listed={len(listed)} leg+epic={len(hi_tier)} "
        f"triggers={len(triggers)} new_calls={len(new_calls)}",
        "TOP Legendary/Epic listés:",
    ]
    for i, x in enumerate(top_ranks[:8], 1):
        lines.append(
            f"  {i}. #{x['naka']} rank #{x['rarityRank']} ({x['rarityTier']}) ask {x['ask_btc']}"
        )
    for b in ("sub10", "sub100", "sub1k", "sub10k"):
        f = sub_floors[b]
        lines.append(f"  {b}: listed {f['listed']} floor {btc(f['floor']) if f['floor'] else '-'}")
    print("\n".join(lines))

    if new_calls:
        steals = [t for t in new_calls if t["reason"] == "steal"]
        hi = [t for t in new_calls if t["reason"] == "hi_tier_floor"]
        parts = []
        if steals:
            parts.append("🚨 CALL Shielded Nakas — listing anormalement bas vs floor")
            parts.append(
                f"Floor actuel {floor_btc} · floor robuste {btc(robust_floor)} · "
                f"seuil steal ≤{btc(steal_ceil)} (−15%+)"
            )
            parts.append("")
            for t in steals:
                pct = int(round((t.get("discount_vs_robust") or 0) * 100))
                parts.append(
                    f"#{t['naka']} · rank #{t['rarityRank']} · {t['rarityTier']} · "
                    f"ask {t['ask_btc']} (−{pct}% vs robuste)"
                    + (" · pending" if t["pending"] else "")
                )
                if t["inscriptionId"]:
                    parts.append(f"https://ordinals.com/content/{t['inscriptionId']}")
                parts.append("")
        subs = [t for t in new_calls if t["reason"] in ("sub_floor", "sub_steal")]
        if subs:
            parts.append("🚨 CALL Shielded Nakas — Shielded # sub à snipe")
            parts.append(
                f"Floor {floor_btc} · seuils sub10 ≤{btc(floor*SUB_MULT['sub10'])}, "
                f"sub100 ≤{btc(floor*SUB_MULT['sub100'])}, sub1k ≤{btc(floor*SUB_MULT['sub1k'])}"
            )
            parts.append("")
            for t in subs:
                why = "steal vs floor du sub" if t["reason"] == "sub_steal" else "proche floor"
                parts.append(
                    f"#{t['naka']} · Shielded #{t['shieldedNum']} ({t['sub']}) · rank #{t['rarityRank']} "
                    f"{t['rarityTier']} · ask {t['ask_btc']} · {why}"
                    + (" · pending" if t["pending"] else "")
                )
                if t["inscriptionId"]:
                    parts.append(f"https://ordinals.com/content/{t['inscriptionId']}")
                parts.append("")
        if hi:
            parts.append("🚨 CALL Shielded Nakas — Legendary/Epic au floor")
            parts.append(f"Floor ~{floor_btc} · seuil ≤{btc(near_floor)}")
            parts.append("")
            for t in hi:
                parts.append(
                    f"#{t['naka']} · rank #{t['rarityRank']} · {t['rarityTier']} · "
                    f"ask {t['ask_btc']}"
                    + (" · pending" if t["pending"] else "")
                )
                if t["inscriptionId"]:
                    parts.append(f"https://ordinals.com/content/{t['inscriptionId']}")
                parts.append("")
        parts.append("Meilleurs Legendary/Epic listés:")
        for x in top_ranks[:5]:
            parts.append(
                f"#{x['naka']} rank #{x['rarityRank']} · ask {x['ask_btc']} · {x['rarityTier']}"
            )
        text = "\n".join(parts).strip()
        tg = send_tg(text)
        print(json.dumps({"call": True, "n": len(new_calls), "telegram": tg}))
        (OUT / "watch_call.txt").write_text(text)
        return 0

    print(
        json.dumps(
            {
                "call": False,
                "floor_btc": floor_btc,
                "robust_floor_btc": btc(robust_floor),
                "listed": len(listed),
                "hi_tier_listed": len(hi_tier),
                "active_triggers": len(triggers),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
