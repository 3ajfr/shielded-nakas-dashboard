"""Hedonic fair-value model for Shielded Nakas (stdlib only).

log(sale / M(t)) = b0 + tier + Shielded# bucket (+ log-number slope for sub10/sub100) + log(rank) + trait values
  M(t) = market level at sale time = median of the previous WINDOW completed sales (no look-ahead).
Fit: weighted ridge regression (recent sales weigh more), per-feature penalty -> sparse trait values
shrink toward 0 (empirical-Bayes-like). Trait values with < MIN_N sales are dropped (premium 0).
Prediction: M_now * exp(x.b), then clamped >= floor, blended down toward the cheapest comparable
live listing (same sub bucket + tier), and capped for sanity.
"""
from __future__ import annotations
import math, statistics
from datetime import datetime

WINDOW = 40          # sales in the rolling market level
MIN_N = 3            # min sales for a trait value to get its own premium
LAMBDA = 10.0        # ridge strength (in "sales" units) for trait/tier/sub dummies (tuned by time-split backtest)
HALF_LIFE_D = 4.0    # recency weighting of training sales
TRAITS = ("Body", "Outfit", "Hair And Headwear", "Eyes", "Mouth", "Hoodie")
SUBS = ("sub10", "sub100", "sub1k")          # reference: sub10k
RARE_COUNT = 60      # a trait value held by <= this many Nakas is 'rare' (listing-floor signal applies)
OWN_SALE_W = 0.35    # max weight of the item's own last sale (decays with age)
TRAIT_FLOOR_W = 0.75 # value a rare-trait item at >= this share of its trait's cheapest live listing
TIERS = ("Legendary", "Epic", "Rare", "Uncommon")  # reference: Common


def _ts(t):
    s = t.get("completedAt") or t.get("createdAt") or ""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _num(ins):
    for t in ins.get("traits") or []:
        if t.get("trait_type") == "Shielded #":
            try: return int(t.get("value"))
            except Exception: return None
    return None


def _sub(n):
    if n is None: return "sub10k"
    return "sub10" if n < 10 else "sub100" if n < 100 else "sub1k" if n < 1000 else "sub10k"


def _rare(ins):
    """[(trait key, count)] for trait values held by <= RARE_COUNT Nakas (uses collection-wide counts)."""
    out = []
    for t in ins.get("traits") or []:
        if t.get("trait_type") in TRAITS and t.get("count") and int(t["count"]) <= RARE_COUNT:
            out.append((f"{t['trait_type']}={t['value']}", int(t["count"])))
    return out


def _traits(ins):
    return {t["trait_type"]: str(t["value"]) for t in ins.get("traits") or [] if t.get("trait_type") in TRAITS}


def market_levels(trades):
    """M(t) for each trade using only earlier trades; returns list aligned with trades (None for warm-up)."""
    out, hist = [], []
    for t in trades:
        out.append(statistics.median(hist[-WINDOW:]) if len(hist) >= 10 else None)
        hist.append(t["salePrice"])
    return out


class Model:
    def __init__(self):
        self.cols = []; self.beta = []; self.vocab = set()

    def _x(self, ins):
        x = {"b0": 1.0}
        tier = ins.get("rarityTier") or "Common"
        if tier in TIERS: x["tier:" + tier] = 1.0
        n = _num(ins); sub = _sub(n)
        if sub in SUBS: x["sub:" + sub] = 1.0
        if sub in ("sub10", "sub100") and n is not None:
            x["lognum:" + sub] = math.log10(n + 1) - (0.5 if sub == "sub10" else 1.5)  # centered in bucket
        r = ins.get("rarityRank") or 1700
        x["logrank"] = math.log(max(1, r)) - math.log(1700)
        rc = min((c for _, c in _rare(ins)), default=None)
        x["rare:logcount"] = (math.log(RARE_COUNT / rc) if rc else 0.0)   # 0 if no rare trait, grows as trait gets rarer
        for k, v in _traits(ins).items():
            f = f"t:{k}={v}"
            if f in self.vocab: x[f] = 1.0
        return x

    def fit(self, rows):
        """rows: list of (ins, y=log(price/M), weight)."""
        cnt = {}
        for ins, _, _ in rows:
            for k, v in _traits(ins).items():
                cnt[f"t:{k}={v}"] = cnt.get(f"t:{k}={v}", 0) + 1
        self.vocab = {f for f, c in cnt.items() if c >= MIN_N}
        X = [self._x(ins) for ins, _, _ in rows]
        cols = sorted({c for x in X for c in x}); idx = {c: i for i, c in enumerate(cols)}; p = len(cols)
        A = [[0.0] * p for _ in range(p)]; bvec = [0.0] * p
        for x, (_, y, w) in zip(X, rows):
            it = [(idx[c], v) for c, v in x.items()]
            for i, vi in it:
                bvec[i] += w * vi * y
                Ai = A[i]
                for j, vj in it: Ai[j] += w * vi * vj
        for c, i in idx.items():
            if c == "b0": A[i][i] += 1e-6
            elif c in ("logrank", "rare:logcount") or c.startswith("lognum:"): A[i][i] += 1.0
            else: A[i][i] += LAMBDA
        self.cols = cols; self.beta = _solve(A, bvec)
        return self

    def predict_rel(self, ins):
        x = self._x(ins); b = dict(zip(self.cols, self.beta))
        return math.exp(sum(b.get(c, 0.0) * v for c, v in x.items()))

    def coef(self):
        return dict(zip(self.cols, self.beta))


def _solve(A, b):
    n = len(b); M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c])); M[c], M[piv] = M[piv], M[c]
        d = M[c][c] or 1e-12
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c] / d; Mr = M[r]; Mc = M[c]
                for k in range(c, n + 1): Mr[k] -= f * Mc[k]
    return [M[i][n] / (M[i][i] or 1e-12) for i in range(n)]


def training_rows(trades, by_id, levels, now_ts=None, upto=None):
    now_ts = now_ts or (_ts(trades[-1]) if trades else 0)
    rows = []
    for k, (t, m) in enumerate(zip(trades, levels)):
        if upto is not None and k >= upto: break
        ins = by_id.get(t["inscriptionId"])
        if not ins or not m: continue
        y = math.log(t["salePrice"] / m)
        if abs(y) > 3: continue  # drop absurd prints (x20)
        w = 0.5 ** ((now_ts - _ts(t)) / 86400 / HALF_LIFE_D)
        rows.append((ins, y, w))
    return rows


def fair_values(ins_list, trades, live, floor):
    """Returns {inscriptionId: fair_sats}. trades sorted ascending, completed only. live: {id: ask}."""
    by_id = {i["inscriptionId"]: i for i in ins_list}
    lv = market_levels(trades)
    model = Model().fit(training_rows(trades, by_id, lv))
    m_now = statistics.median([t["salePrice"] for t in trades[-WINDOW:]]) if trades else (floor or 0)
    # cheapest comparable live listing per (sub, tier)
    comp = {}
    for iid, a in live.items():
        i = by_id.get(iid)
        if not i: continue
        key = (_sub(_num(i)), i.get("rarityTier") or "Common")
        comp.setdefault(key, []).append((a, iid))
    for v in comp.values(): v.sort()
    tfloor = {}   # rare trait -> sorted [(ask, id)]
    for iid, a in live.items():
        i = by_id.get(iid)
        if i:
            for k, _ in _rare(i): tfloor.setdefault(k, []).append((a, iid))
    for v in tfloor.values(): v.sort()
    b = model.coef()
    subb = lambda s: b.get("sub:" + s, 0.0)
    # rare-trait SALES evidence: last sales of items sharing the trait, normalized by market level at the time
    # and by Shielded # bucket premium -> "relative value of the trait" (needs >= 2 sales to count)
    tsales = {}
    for t, m in zip(trades, lv):
        i = by_id.get(t["inscriptionId"])
        if not i or not m: continue
        for k, _ in _rare(i):
            tsales.setdefault(k, []).append(t["salePrice"] / m / math.exp(subb(_sub(_num(i)))))
    trel = {k: statistics.median(v[-5:]) for k, v in tsales.items() if len(v) >= 2}
    # the item's own last sale (normalized to today's market level), weight fades with age
    last = {}
    now_ts = _ts(trades[-1]) if trades else 0
    for t, m in zip(trades, lv):
        if m: last[t["inscriptionId"]] = (t["salePrice"] * m_now / m, (now_ts - _ts(t)) / 86400)
    max_sale = {}
    for t in trades:
        i = by_id.get(t["inscriptionId"])
        if i: s = _sub(_num(i)); max_sale[s] = max(max_sale.get(s, 0), t["salePrice"])
    out = {}
    for i in ins_list:
        iid = i["inscriptionId"]; sub = _sub(_num(i)); key = (sub, i.get("rarityTier") or "Common")
        f = m_now * model.predict_rel(i)
        if iid in last:
            p_, age = last[iid]
            w = OWN_SALE_W * 0.5 ** (age / HALF_LIFE_D)
            f = math.exp((1 - w) * math.log(f) + w * math.log(max(1, p_)))
        rare = _rare(i)
        # strong signal: cheapest live listing sharing a rare trait (excluding itself), adjusted for Shielded # bucket
        for k, _cnt in rare:
            if k not in trel: continue           # listing asks only count when the trait has real sales behind it
            ev = m_now * trel[k]                 # trait value for a sub10k piece at today's market level
            f = max(f, 0.8 * ev * math.exp(subb(sub)))
            hit = next(((a, j) for a, j in tfloor.get(k, []) if j != iid), None)
            if hit:
                hs = _sub(_num(by_id[hit[1]]))
                base = min(hit[0] / math.exp(subb(hs)), 1.5 * ev)   # ignore wishful asks far above sales evidence
                f = max(f, TRAIT_FLOOR_W * base * math.exp(subb(sub)))
        c = next((a for a, j in comp.get(key, []) if j != iid), None)
        if c and f > c and not rare:  # don't value far above the cheapest comparable you can buy right now
            f = min(c + 0.25 * (f - c), 1.25 * c)
        if floor: f = max(f, floor)
        cap = max(50 * (floor or 0), 1.5 * max_sale.get(sub, 0))
        if cap: f = min(f, cap)
        out[iid] = int(round(f))
    return out, model


