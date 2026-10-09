"""Rarity helpers — API fields are source of truth (no image recalculation)."""
from __future__ import annotations

from typing import Any

# Spec: important traits for comparables (exclude Shielded #; Tier is separate)
IMPORTANT_TRAITS = ("Body", "Outfit", "Hair And Headwear", "Eyes", "Mouth")
# Hoodie appears instead of Outfit/Hair on some Nakas — treat as important too
EXTRA_IMPORTANT = ("Hoodie",)
TIER_TRAIT = "Tier"
EXCLUDE_TRAITS = {"Shielded #"}


def trait_map(inscription: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for t in inscription.get("traits") or []:
        tt = t.get("trait_type")
        if not tt or tt in EXCLUDE_TRAITS:
            continue
        val = t.get("value")
        if val is None:
            continue
        out[str(tt)] = str(val)
    return out


def important_traits(inscription: dict) -> dict[str, str]:
    tm = trait_map(inscription)
    keys = list(IMPORTANT_TRAITS) + list(EXTRA_IMPORTANT)
    return {k: tm[k] for k in keys if k in tm}


def rarity_fields(inscription: dict) -> dict[str, Any]:
    return {
        "rarityRank": inscription.get("rarityRank"),
        "rarityScore": _num(inscription.get("rarityScore")),
        "rarityTier": inscription.get("rarityTier") or "Unknown",
    }


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def naka_number(inscription: dict) -> int | None:
    v = inscription.get("inscriptionNumber")
    if isinstance(v, int):
        return v
    sh = inscription.get("shielded") or {}
    if isinstance(sh.get("assetId"), int):
        return sh["assetId"]
    name = inscription.get("name") or ""
    if "#" in name:
        try:
            return int(name.rsplit("#", 1)[-1].strip())
        except ValueError:
            return None
    return None
