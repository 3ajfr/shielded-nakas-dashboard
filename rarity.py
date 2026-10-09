"""Rarity helpers — API fields are source of truth (no image recalculation)."""
from __future__ import annotations

from typing import Any

# Important traits for comparables (exclude Shielded #; Tier is separate).
IMPORTANT_TRAITS = ("Body", "Outfit", "Hair And Headwear", "Eyes", "Mouth")
# Hoodie appears instead of Outfit/Hair on some Nakas — treat as important too.
EXTRA_IMPORTANT = ("Hoodie",)
TIER_TRAIT = "Tier"
EXCLUDE_TRAITS = {"Shielded #"}


def trait_map(inscription: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for trait in inscription.get("traits") or []:
        name = trait.get("trait_type")
        if not name or name in EXCLUDE_TRAITS:
            continue
        value = trait.get("value")
        if value is None:
            continue
        out[str(name)] = str(value)
    return out


def important_traits(inscription: dict) -> dict[str, str]:
    traits = trait_map(inscription)
    keys = list(IMPORTANT_TRAITS) + list(EXTRA_IMPORTANT)
    return {key: traits[key] for key in keys if key in traits}


def rarity_fields(inscription: dict) -> dict[str, Any]:
    return {
        "rarityRank": inscription.get("rarityRank"),
        "rarityScore": _num(inscription.get("rarityScore")),
        "rarityTier": inscription.get("rarityTier") or "Unknown",
    }


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
