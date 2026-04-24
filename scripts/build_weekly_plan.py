#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from inventory import load_inventory_state, recipe_inventory_support
from paths import FoodBrainPaths, resolve_data_root, write_atomic

EFFORT_ORDER = {"easy": 0, "moderate": 1, "involved": 2}
FRICTION_ORDER = {"low": 0, "medium": 1, "high": 2}
PROTEIN_SPLIT_CHARS = [",", "/"]
SOON_REPEAT_DAYS = 14
RECENT_WINDOW_DAYS = 28

PRESETS: dict[str, dict[str, Any]] = {
    "balanced": {
        "label": "Balanced week",
        "description": "Default practical week: mostly trusted, low-friction dinners with one slot for something slightly more interesting.",
        "target_mix": {
            "effort_max_counts": {"involved": 0, "moderate_plus": 1},
            "friction_max_counts": {"high": 0, "medium_plus": 2},
            "cost_max_counts": {"expensive": 0},
            "aspirational_max": 0,
            "testing_max": 1,
            "wants_side_max": 2,
        },
        "weights": {
            "base": 40,
            "easy": 8,
            "moderate": 2,
            "involved": -18,
            "low_friction": 9,
            "medium_friction": 2,
            "high_friction": -18,
            "cheap": 8,
            "medium_cost": 3,
            "expensive": -20,
            "trusted": 7,
            "testing": 1,
            "aspirational": -20,
            "family_table": 4,
            "crowd_friendly": 2,
            "small_table": -1,
            "self_contained": 7,
            "wants_side": -2,
            "needs_protein": -4,
            "sale_trigger": 1,
            "hosting": 0,
            "comfort_food": 1,
            "repeat_protein_penalty": -12,
            "repeat_protein_after_first": -8,
            "second_side_dependent_penalty": -4,
            "third_side_dependent_penalty": -8,
            "second_medium_friction_penalty": -4,
            "second_moderate_penalty": -4,
            "second_testing_penalty": -6,
            "history_exact_repeat_soon": -18,
            "history_exact_repeat_recent": -10,
            "history_recent_protein_dominant": -10,
            "history_recent_protein_present": -4,
            "history_recent_role_dominant": -6,
            "history_recent_role_present": -2,
            "history_long_gap_bonus": 5,
        },
    },
    "easy": {
        "label": "Easy week",
        "description": "Bias hard toward low-effort, low-friction, proven weeknight dinners.",
        "target_mix": {
            "effort_max_counts": {"involved": 0, "moderate_plus": 0},
            "friction_max_counts": {"high": 0, "medium_plus": 1},
            "cost_max_counts": {"expensive": 0},
            "aspirational_max": 0,
            "testing_max": 1,
            "wants_side_max": 2,
        },
        "weights": {
            "base": 40,
            "easy": 12,
            "moderate": -8,
            "involved": -30,
            "low_friction": 14,
            "medium_friction": -6,
            "high_friction": -30,
            "cheap": 9,
            "medium_cost": 2,
            "expensive": -20,
            "trusted": 8,
            "testing": 0,
            "aspirational": -25,
            "family_table": 4,
            "crowd_friendly": 1,
            "small_table": -1,
            "self_contained": 8,
            "wants_side": -3,
            "needs_protein": -5,
            "sale_trigger": 1,
            "hosting": -2,
            "comfort_food": 1,
            "repeat_protein_penalty": -12,
            "repeat_protein_after_first": -8,
            "second_side_dependent_penalty": -5,
            "third_side_dependent_penalty": -10,
            "second_medium_friction_penalty": -8,
            "second_moderate_penalty": -10,
            "second_testing_penalty": -8,
            "history_exact_repeat_soon": -20,
            "history_exact_repeat_recent": -12,
            "history_recent_protein_dominant": -10,
            "history_recent_protein_present": -4,
            "history_recent_role_dominant": -6,
            "history_recent_role_present": -2,
            "history_long_gap_bonus": 4,
        },
    },
    "cheap": {
        "label": "Cheap week",
        "description": "Prioritize cheap dinners and keep friction low enough that the savings still feel real.",
        "target_mix": {
            "effort_max_counts": {"involved": 0, "moderate_plus": 1},
            "friction_max_counts": {"high": 0, "medium_plus": 2},
            "cost_max_counts": {"expensive": 0},
            "aspirational_max": 0,
            "testing_max": 1,
            "wants_side_max": 2,
        },
        "weights": {
            "base": 40,
            "easy": 8,
            "moderate": 1,
            "involved": -18,
            "low_friction": 10,
            "medium_friction": 1,
            "high_friction": -20,
            "cheap": 16,
            "medium_cost": 0,
            "expensive": -30,
            "trusted": 6,
            "testing": 0,
            "aspirational": -20,
            "family_table": 4,
            "crowd_friendly": 1,
            "small_table": -1,
            "self_contained": 5,
            "wants_side": -2,
            "needs_protein": -6,
            "sale_trigger": 3,
            "hosting": -2,
            "comfort_food": 1,
            "repeat_protein_penalty": -10,
            "repeat_protein_after_first": -7,
            "second_side_dependent_penalty": -3,
            "third_side_dependent_penalty": -6,
            "second_medium_friction_penalty": -5,
            "second_moderate_penalty": -4,
            "second_testing_penalty": -6,
            "history_exact_repeat_soon": -18,
            "history_exact_repeat_recent": -10,
            "history_recent_protein_dominant": -8,
            "history_recent_protein_present": -3,
            "history_recent_role_dominant": -5,
            "history_recent_role_present": -2,
            "history_long_gap_bonus": 4,
        },
    },
    "low-carb": {
        "label": "Low-carb week",
        "description": "Stay inside the low-carb lane while still balancing variety and avoiding an annoying week.",
        "require_diet_mode": "low-carb",
        "target_mix": {
            "effort_max_counts": {"involved": 0, "moderate_plus": 1},
            "friction_max_counts": {"high": 0, "medium_plus": 2},
            "cost_max_counts": {"expensive": 0},
            "aspirational_max": 1,
            "testing_max": 1,
            "wants_side_max": 2,
        },
        "weights": {
            "base": 40,
            "easy": 8,
            "moderate": 2,
            "involved": -18,
            "low_friction": 8,
            "medium_friction": 1,
            "high_friction": -18,
            "cheap": 8,
            "medium_cost": 3,
            "expensive": -20,
            "trusted": 6,
            "testing": 1,
            "aspirational": -10,
            "family_table": 3,
            "crowd_friendly": 1,
            "small_table": -1,
            "self_contained": 7,
            "wants_side": -1,
            "needs_protein": -8,
            "sale_trigger": 1,
            "hosting": -1,
            "comfort_food": 1,
            "repeat_protein_penalty": -12,
            "repeat_protein_after_first": -8,
            "second_side_dependent_penalty": -2,
            "third_side_dependent_penalty": -4,
            "second_medium_friction_penalty": -4,
            "second_moderate_penalty": -4,
            "second_testing_penalty": -5,
            "history_exact_repeat_soon": -20,
            "history_exact_repeat_recent": -12,
            "history_recent_protein_dominant": -10,
            "history_recent_protein_present": -4,
            "history_recent_role_dominant": -4,
            "history_recent_role_present": -1,
            "history_long_gap_bonus": 4,
        },
    },
    "hosting-friendly": {
        "label": "Hosting-friendly week",
        "description": "Allow one bigger or more special dinner, but still avoid stacking multiple high-friction projects.",
        "target_mix": {
            "effort_max_counts": {"involved": 1, "moderate_plus": 2},
            "friction_max_counts": {"high": 1, "medium_plus": 2},
            "cost_max_counts": {"expensive": 1},
            "aspirational_max": 1,
            "testing_max": 2,
            "wants_side_max": 3,
        },
        "weights": {
            "base": 40,
            "easy": 4,
            "moderate": 4,
            "involved": -6,
            "low_friction": 5,
            "medium_friction": 3,
            "high_friction": -8,
            "cheap": 3,
            "medium_cost": 4,
            "expensive": -8,
            "trusted": 5,
            "testing": 2,
            "aspirational": -4,
            "family_table": 4,
            "crowd_friendly": 7,
            "small_table": -3,
            "self_contained": 4,
            "wants_side": -1,
            "needs_protein": -6,
            "sale_trigger": 1,
            "hosting": 8,
            "comfort_food": 2,
            "repeat_protein_penalty": -10,
            "repeat_protein_after_first": -6,
            "second_side_dependent_penalty": -2,
            "third_side_dependent_penalty": -4,
            "second_medium_friction_penalty": -3,
            "second_moderate_penalty": -2,
            "second_testing_penalty": -3,
            "history_exact_repeat_soon": -14,
            "history_exact_repeat_recent": -8,
            "history_recent_protein_dominant": -8,
            "history_recent_protein_present": -3,
            "history_recent_role_dominant": -4,
            "history_recent_role_present": -1,
            "history_long_gap_bonus": 5,
        },
    },
}


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def load_household_preferences(paths: FoodBrainPaths) -> dict[str, Any]:
    return load_json_if_exists(paths.household_dir / "preferences.json")


def planner_defaults(paths: FoodBrainPaths) -> tuple[str, int, bool]:
    planning = load_household_preferences(paths).get("planning", {})
    preset = planning.get("default_preset", "balanced")
    dinners_per_week = planning.get("default_dinners_per_week", 3)
    prioritize_inventory = planning.get("prioritize_inventory")
    legacy_prioritize_inventory = planning.get("prioritize_freezer_inventory")
    if preset not in PRESETS:
        preset = "balanced"
    if not isinstance(dinners_per_week, int) or dinners_per_week < 1:
        dinners_per_week = 3
    if not isinstance(prioritize_inventory, bool):
        prioritize_inventory = legacy_prioritize_inventory if isinstance(legacy_prioritize_inventory, bool) else False
    return preset, dinners_per_week, prioritize_inventory


def load_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing catalog: {path}. Run build_recipe_query_index.py first.")
    return json.loads(path.read_text())


def protein_family(recipe: dict[str, Any]) -> str:
    raw = (recipe.get("core_protein") or "").lower()
    if not raw:
        return "other"
    bits = [raw]
    for char in PROTEIN_SPLIT_CHARS:
        next_bits = []
        for bit in bits:
            next_bits.extend(part.strip() for part in bit.split(char))
        bits = next_bits
    families = [bit for bit in bits if bit]
    if any(bit in {"beef", "steak"} for bit in families):
        return "beef"
    if any(bit in {"chicken"} for bit in families):
        return "chicken"
    if any(bit in {"pork", "sausage", "tenderloin", "chops"} for bit in families):
        return "pork"
    if any(bit in {"shrimp"} for bit in families):
        return "shrimp"
    if any(bit in {"fish", "cod", "salmon"} for bit in families):
        return "fish"
    if any(bit in {"pasta", "tomato", "broccoli"} for bit in families):
        return "non-protein-base"
    return families[0]


def primary_structural_role(recipe: dict[str, Any]) -> str:
    roles = recipe.get("structural_role") or []
    return roles[0] if roles else "unknown"


def side_recipe_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["slug"]: r for r in payload["recipes"] if "side" in r["meal_type"]}


def dinner_candidates(payload: dict[str, Any], preset: dict[str, Any], include_aspirational: bool) -> list[dict[str, Any]]:
    dinners = [r for r in payload["recipes"] if "dinner" in r["meal_type"]]
    if preset.get("require_diet_mode"):
        dinners = [r for r in dinners if preset["require_diet_mode"] in r.get("diet_modes", [])]
    if not include_aspirational:
        dinners = [r for r in dinners if r.get("status") != "aspirational"]
    return dinners


def parse_date(raw: str) -> date | None:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def load_history_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line == "[]":
            continue
        event = json.loads(line)
        event_date = parse_date(event.get("date"))
        if event_date is None:
            continue
        event["parsed_date"] = event_date
        events.append(event)
    events.sort(key=lambda item: (item["parsed_date"], item.get("event_type", ""), item.get("recipe_slug", "")))
    return events


def history_event_weight(event: dict[str, Any]) -> float:
    return 1.0 if event.get("event_type") == "made" else 0.7


def build_history_context(events: list[dict[str, Any]], recipes_by_slug: dict[str, dict[str, Any]]) -> dict[str, Any]:
    dinner_events: list[dict[str, Any]] = []
    for event in events:
        if event.get("meal_slot") != "dinner":
            continue
        recipe = recipes_by_slug.get(event.get("recipe_slug", ""))
        if not recipe or "dinner" not in recipe.get("meal_type", []):
            continue
        dinner_events.append({**event, "recipe": recipe, "event_weight": history_event_weight(event)})

    if not dinner_events:
        return {
            "has_history": False,
            "event_count": 0,
            "recent_event_count": 0,
            "last_recipe_dates": {},
            "recent_protein_counts": Counter(),
            "recent_role_counts": Counter(),
            "recent_events": [],
        }

    latest_date = max(event["parsed_date"] for event in dinner_events)
    recent_events = [event for event in dinner_events if (latest_date - event["parsed_date"]).days <= RECENT_WINDOW_DAYS]

    last_recipe_dates: dict[str, date] = {}
    for event in dinner_events:
        last_recipe_dates[event["recipe_slug"]] = event["parsed_date"]

    recent_protein_counts: Counter[str] = Counter()
    recent_role_counts: Counter[str] = Counter()
    for event in recent_events:
        recent_protein_counts[protein_family(event["recipe"])] += event["event_weight"]
        recent_role_counts[primary_structural_role(event["recipe"])] += event["event_weight"]

    return {
        "has_history": True,
        "event_count": len(dinner_events),
        "recent_event_count": len(recent_events),
        "anchor_date": latest_date,
        "last_recipe_dates": last_recipe_dates,
        "recent_protein_counts": recent_protein_counts,
        "recent_role_counts": recent_role_counts,
        "recent_events": [
            {
                "date": event["parsed_date"].isoformat(),
                "event_type": event.get("event_type"),
                "event_weight": event["event_weight"],
                "recipe_slug": event.get("recipe_slug"),
                "title": event["recipe"]["title"],
            }
            for event in recent_events[-8:]
        ],
    }


def history_summary_for_output(history: dict[str, Any]) -> dict[str, Any] | None:
    if not history.get("has_history"):
        return None
    return {
        "anchor_date": history["anchor_date"].isoformat(),
        "event_count": history["event_count"],
        "recent_event_count": history["recent_event_count"],
        "recent_protein_counts": {key: round(value, 2) for key, value in sorted(history["recent_protein_counts"].items())},
        "recent_role_counts": {key: round(value, 2) for key, value in sorted(history["recent_role_counts"].items())},
        "recent_events": history["recent_events"],
    }


def score_recipe(
    recipe: dict[str, Any],
    selected: list[dict[str, Any]],
    preset: dict[str, Any],
    history: dict[str, Any] | None = None,
    inventory_state: dict[str, Any] | None = None,
    prioritize_inventory: bool = False,
) -> tuple[int, list[str], dict[str, Any] | None]:
    weights = preset["weights"]
    score = weights["base"]
    reasons: list[str] = []
    penalties: list[str] = []

    def apply(delta: int, if_reason: str | None = None, if_penalty: str | None = None) -> None:
        nonlocal score
        score += delta
        if delta > 0 and if_reason:
            reasons.append(if_reason)
        elif delta < 0 and if_penalty:
            penalties.append(if_penalty)

    effort = recipe["cooking_effort"]
    friction = recipe["ingredient_friction"]
    cost = recipe["cost"]
    status = recipe["status"]
    serving = recipe["serving_profile"]
    flags = recipe["composition_flags"]
    contexts = set(recipe.get("context_occasion", []))

    apply(weights.get("easy", 0) if effort == "easy" else 0, "easy to cook")
    apply(weights.get("moderate", 0) if effort == "moderate" else 0, "moderate effort but still reasonable")
    apply(weights.get("involved", 0) if effort == "involved" else 0, if_penalty="involved cooking project")

    apply(weights.get("low_friction", 0) if friction == "low" else 0, "low ingredient friction")
    apply(weights.get("medium_friction", 0) if friction == "medium" else 0, "ingredient list is manageable")
    apply(weights.get("high_friction", 0) if friction == "high" else 0, if_penalty="high ingredient friction")

    apply(weights.get("cheap", 0) if cost == "cheap" else 0, "cheap dinner")
    apply(weights.get("medium_cost", 0) if cost == "medium" else 0, "normal medium-cost dinner")
    apply(weights.get("expensive", 0) if cost == "expensive" else 0, if_penalty="expensive for a routine week")

    apply(weights.get("trusted", 0) if status == "trusted" else 0, "trusted house recipe")
    apply(weights.get("testing", 0) if status == "testing" else 0, "testing recipe but still plausible")
    apply(weights.get("aspirational", 0) if status == "aspirational" else 0, if_penalty="aspirational / less proven")

    apply(weights.get("family_table", 0) if serving == "family-table" else 0, "good family-table fit")
    apply(weights.get("crowd_friendly", 0) if serving == "crowd-friendly" else 0, "scales well")
    apply(weights.get("small_table", 0) if serving == "small-table" else 0, if_penalty="smaller-scale dinner")

    apply(weights.get("self_contained", 0) if flags.get("mostly_self_contained") else 0, "self-contained dinner")
    apply(weights.get("wants_side", 0) if flags.get("wants_side_pairing") else 0, if_penalty="needs side support")
    apply(weights.get("needs_protein", 0) if flags.get("needs_protein_pairing") else 0, if_penalty="needs protein pairing to feel complete")

    apply(weights.get("sale_trigger", 0) if "sale-trigger" in contexts else 0, "nice sale-trigger option")
    apply(weights.get("hosting", 0) if "hosting" in contexts else 0, "hosting-friendly")
    apply(weights.get("comfort_food", 0) if "comfort-food" in contexts else 0, "comfort-food lane")

    protein = protein_family(recipe)
    selected_proteins = [protein_family(item) for item in selected]
    repeats = selected_proteins.count(protein)
    if repeats >= 1:
        apply(weights.get("repeat_protein_penalty", 0), if_penalty=f"repeats {protein}")
        if repeats >= 2:
            apply(weights.get("repeat_protein_after_first", 0), if_penalty=f"would make {protein} dominate the week")

    side_dependent_count = sum(1 for item in selected if item["composition_flags"].get("wants_side_pairing"))
    if flags.get("wants_side_pairing") and side_dependent_count >= 1:
        apply(weights.get("second_side_dependent_penalty", 0), if_penalty="would stack another side-dependent dinner")
    if flags.get("wants_side_pairing") and side_dependent_count >= 2:
        apply(weights.get("third_side_dependent_penalty", 0), if_penalty="too many dinners needing side support")

    medium_friction_count = sum(1 for item in selected if FRICTION_ORDER[item["ingredient_friction"]] >= FRICTION_ORDER["medium"])
    if FRICTION_ORDER[friction] >= FRICTION_ORDER["medium"] and medium_friction_count >= 1:
        apply(weights.get("second_medium_friction_penalty", 0), if_penalty="would make the week more shop-annoying")

    moderate_plus_count = sum(1 for item in selected if EFFORT_ORDER[item["cooking_effort"]] >= EFFORT_ORDER["moderate"])
    if EFFORT_ORDER[effort] >= EFFORT_ORDER["moderate"] and moderate_plus_count >= 1:
        apply(weights.get("second_moderate_penalty", 0), if_penalty="would stack another non-easy dinner")

    testing_count = sum(1 for item in selected if item["status"] == "testing")
    if status == "testing" and testing_count >= 1:
        apply(weights.get("second_testing_penalty", 0), if_penalty="already have a testing meal in the week")

    if history and history.get("has_history"):
        last_seen = history["last_recipe_dates"].get(recipe["slug"])
        if last_seen:
            gap_days = (history["anchor_date"] - last_seen).days
            if gap_days <= SOON_REPEAT_DAYS:
                apply(weights.get("history_exact_repeat_soon", 0), if_penalty=f"made or planned too recently ({gap_days}d ago)")
            elif gap_days <= RECENT_WINDOW_DAYS:
                apply(weights.get("history_exact_repeat_recent", 0), if_penalty=f"still fairly recent ({gap_days}d ago)")
        else:
            apply(weights.get("history_long_gap_bonus", 0), if_reason="has not shown up recently")

        protein_count = history["recent_protein_counts"].get(protein, 0)
        if protein_count >= 2.2:
            apply(weights.get("history_recent_protein_dominant", 0), if_penalty=f"recent history already leans {protein}")
        elif protein_count >= 0.7:
            apply(weights.get("history_recent_protein_present", 0), if_penalty=f"recent history already includes {protein}")

        role = primary_structural_role(recipe)
        role_count = history["recent_role_counts"].get(role, 0)
        if role_count >= 2.2:
            apply(weights.get("history_recent_role_dominant", 0), if_penalty=f"recent history already leans {role}")
        elif role_count >= 0.7:
            apply(weights.get("history_recent_role_present", 0), if_penalty=f"recent history already includes {role}")

    inventory_support = None
    if inventory_state:
        inventory_support = recipe_inventory_support(recipe, inventory_state, prioritize_inventory=prioritize_inventory)
        if inventory_support["total_bonus"] > 0:
            apply(
                inventory_support["total_bonus"],
                if_reason=inventory_support["matches"][0]["explanation"],
            )

    return score, reasons + penalties, inventory_support


def can_add(recipe: dict[str, Any], selected: list[dict[str, Any]], preset: dict[str, Any], target: int) -> bool:
    mix = preset.get("target_mix", {})
    simulated = selected + [recipe]

    involved_count = sum(1 for item in simulated if item["cooking_effort"] == "involved")
    moderate_plus_count = sum(1 for item in simulated if EFFORT_ORDER[item["cooking_effort"]] >= EFFORT_ORDER["moderate"])
    if involved_count > mix.get("effort_max_counts", {}).get("involved", target):
        return False
    if moderate_plus_count > mix.get("effort_max_counts", {}).get("moderate_plus", target):
        return False

    high_friction_count = sum(1 for item in simulated if item["ingredient_friction"] == "high")
    medium_plus_friction_count = sum(1 for item in simulated if FRICTION_ORDER[item["ingredient_friction"]] >= FRICTION_ORDER["medium"])
    if high_friction_count > mix.get("friction_max_counts", {}).get("high", target):
        return False
    if medium_plus_friction_count > mix.get("friction_max_counts", {}).get("medium_plus", target):
        return False

    expensive_count = sum(1 for item in simulated if item["cost"] == "expensive")
    if expensive_count > mix.get("cost_max_counts", {}).get("expensive", target):
        return False

    aspirational_count = sum(1 for item in simulated if item["status"] == "aspirational")
    testing_count = sum(1 for item in simulated if item["status"] == "testing")
    wants_side_count = sum(1 for item in simulated if item["composition_flags"].get("wants_side_pairing"))

    if aspirational_count > mix.get("aspirational_max", target):
        return False
    if testing_count > mix.get("testing_max", target):
        return False
    if wants_side_count > mix.get("wants_side_max", target):
        return False
    return True


def choose_side(recipe: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any] | None:
    intel = payload.get("pairing_intelligence", {}).get(recipe["slug"], {})
    side_matches = intel.get("recipe_side_matches", [])
    sides = side_recipe_map(payload)
    for match in side_matches:
        side = sides.get(match["slug"])
        if side:
            return {
                "slug": side["slug"],
                "title": side["title"],
                "path": side["path"],
                "reason": "; ".join(match.get("reasons", [])[:2]) or "pairing metadata overlap",
            }
    return None


def choose_protein_add_on(recipe: dict[str, Any], payload: dict[str, Any]) -> str | None:
    intel = payload.get("pairing_intelligence", {}).get(recipe["slug"], {})
    proteins = intel.get("protein_pairings", [])
    return proteins[0]["label"] if proteins else None


def explain_recipe(
    recipe: dict[str, Any],
    payload: dict[str, Any],
    score: int,
    reasons: list[str],
    history: dict[str, Any] | None = None,
    inventory_support: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flags = recipe["composition_flags"]
    side = choose_side(recipe, payload) if flags.get("wants_side_pairing") else None
    protein_add_on = choose_protein_add_on(recipe, payload) if flags.get("needs_protein_pairing") else None

    if flags.get("needs_protein_pairing"):
        composition = {
            "kind": "needs-protein-pairing",
            "note": f"This is a base dinner, so pair it with {protein_add_on or 'a simple protein'} to make it feel complete.",
            "protein_add_on": protein_add_on,
            "side": side,
        }
    elif flags.get("mostly_self_contained"):
        composition = {
            "kind": "self-contained",
            "note": "This reads as a self-contained dinner this week; no extra side is required.",
            "protein_add_on": None,
            "side": None,
        }
    elif flags.get("wants_side_pairing"):
        composition = {
            "kind": "wants-side",
            "note": f"Treat this as a main that wants a side{(': ' + side['title']) if side else ''}.",
            "protein_add_on": None,
            "side": side,
        }
    else:
        composition = {
            "kind": "flexible",
            "note": "This can stand as dinner without mandatory extras, but a side would be optional.",
            "protein_add_on": None,
            "side": None,
        }

    last_seen = None
    if history and history.get("has_history"):
        raw = history["last_recipe_dates"].get(recipe["slug"])
        last_seen = raw.isoformat() if raw else None

    return {
        "slug": recipe["slug"],
        "title": recipe["title"],
        "path": recipe["path"],
        "score": score,
        "protein_family": protein_family(recipe),
        "primary_structural_role": primary_structural_role(recipe),
        "effort": recipe["cooking_effort"],
        "ingredient_friction": recipe["ingredient_friction"],
        "cost": recipe["cost"],
        "status": recipe["status"],
        "serving_profile": recipe["serving_profile"],
        "context": recipe.get("context_occasion", []),
        "last_seen": last_seen,
        "reasons": reasons[:8],
        "composition": composition,
        "inventory_support": inventory_support or {"total_bonus": 0, "matches": []},
    }


def summarize_plan(picks: list[dict[str, Any]]) -> dict[str, Any]:
    proteins = Counter(pick["protein_family"] for pick in picks)
    roles = Counter(pick["primary_structural_role"] for pick in picks)
    inventory_supported = [pick for pick in picks if pick.get("inventory_support", {}).get("total_bonus", 0) > 0]
    return {
        "protein_variety": dict(sorted(proteins.items())),
        "role_mix": dict(sorted(roles.items())),
        "effort_mix": dict(sorted(Counter(pick["effort"] for pick in picks).items())),
        "friction_mix": dict(sorted(Counter(pick["ingredient_friction"] for pick in picks).items())),
        "cost_mix": dict(sorted(Counter(pick["cost"] for pick in picks).items())),
        "status_mix": dict(sorted(Counter(pick["status"] for pick in picks).items())),
        "self_contained_count": sum(1 for pick in picks if pick["composition"]["kind"] == "self-contained"),
        "needs_side_count": sum(1 for pick in picks if pick["composition"]["kind"] == "wants-side"),
        "needs_protein_pairing_count": sum(1 for pick in picks if pick["composition"]["kind"] == "needs-protein-pairing"),
        "inventory_supported_count": len(inventory_supported),
        "inventory_bonus_total": sum(pick.get("inventory_support", {}).get("total_bonus", 0) for pick in inventory_supported),
    }


def build_plan(
    payload: dict[str, Any],
    preset_name: str,
    dinners_per_week: int,
    include_aspirational: bool = False,
    history_path: Path | None = None,
    ignore_history: bool = False,
    inventory_state: dict[str, Any] | None = None,
    prioritize_inventory: bool = False,
) -> dict[str, Any]:
    preset = PRESETS[preset_name]
    candidates = dinner_candidates(payload, preset, include_aspirational=include_aspirational)
    recipes_by_slug = {recipe["slug"]: recipe for recipe in payload["recipes"]}
    history = None
    if not ignore_history and history_path is not None:
        history = build_history_context(load_history_events(history_path), recipes_by_slug)

    selected: list[dict[str, Any]] = []
    picks: list[dict[str, Any]] = []

    while len(selected) < dinners_per_week:
        ranked: list[tuple[int, str, dict[str, Any], list[str], dict[str, Any] | None]] = []
        for recipe in candidates:
            if recipe in selected:
                continue
            if not can_add(recipe, selected, preset, dinners_per_week):
                continue
            score, reasons, inventory_support = score_recipe(
                recipe,
                selected,
                preset,
                history=history,
                inventory_state=inventory_state,
                prioritize_inventory=prioritize_inventory,
            )
            ranked.append((score, recipe["title"], recipe, reasons, inventory_support))

        if not ranked:
            break

        ranked.sort(key=lambda item: (-item[0], item[1]))
        score, _, recipe, reasons, inventory_support = ranked[0]
        selected.append(recipe)
        picks.append(explain_recipe(recipe, payload, score, reasons, history=history, inventory_support=inventory_support))

    return {
        "preset": preset_name,
        "preset_label": preset["label"],
        "description": preset["description"],
        "dinners_per_week": dinners_per_week,
        "picked_count": len(picks),
        "history_summary": history_summary_for_output(history) if history else None,
        "inventory_summary": {
            "mode": "prioritized" if prioritize_inventory else "light",
            "prioritize_inventory": prioritize_inventory,
            "active_item_count": len(inventory_state.get("items", [])) if inventory_state else 0,
            "available_item_count": len([item for item in inventory_state.get("items", []) if float(item.get("quantity", {}).get("amount", 0) or 0) > 0]) if inventory_state else 0,
            "supported_pick_count": sum(1 for pick in picks if pick.get("inventory_support", {}).get("total_bonus", 0) > 0),
        },
        "summary": summarize_plan(picks),
        "picks": picks,
    }


def render_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [f"# {plan['preset_label']}", "", plan["description"], ""]
    lines.append(f"- Target dinners: {plan['dinners_per_week']}")
    lines.append(f"- Picked dinners: {plan['picked_count']}")
    lines.append(f"- Protein variety: {json.dumps(plan['summary']['protein_variety'], sort_keys=True)}")
    lines.append(f"- Role mix: {json.dumps(plan['summary']['role_mix'], sort_keys=True)}")
    lines.append(f"- Effort mix: {json.dumps(plan['summary']['effort_mix'], sort_keys=True)}")
    lines.append(f"- Friction mix: {json.dumps(plan['summary']['friction_mix'], sort_keys=True)}")
    inventory_summary = plan.get("inventory_summary") or {}
    lines.append(f"- Inventory items available: {inventory_summary.get('available_item_count', 0)}")
    lines.append(f"- Picks helped by inventory: {inventory_summary.get('supported_pick_count', 0)}")
    history_summary = plan.get("history_summary")
    if history_summary:
        lines.append(f"- History anchor date: {history_summary['anchor_date']}")
        lines.append(f"- Recent dinner events considered: {history_summary['recent_event_count']}")
        lines.append(f"- Recent protein counts: {json.dumps(history_summary['recent_protein_counts'], sort_keys=True)}")
        lines.append(f"- Recent role counts: {json.dumps(history_summary['recent_role_counts'], sort_keys=True)}")
    lines.append("")
    for idx, pick in enumerate(plan["picks"], start=1):
        lines.append(f"## Dinner {idx} — {pick['title']}")
        lines.append(f"- Why it made the cut: {'; '.join(pick['reasons'])}")
        lines.append(
            f"- Planning profile: {pick['effort']} effort, {pick['ingredient_friction']} friction, {pick['cost']} cost, {pick['status']}, {pick['serving_profile']}, role={pick['primary_structural_role']}"
        )
        if pick.get("last_seen"):
            lines.append(f"- Last seen in history: {pick['last_seen']}")
        lines.append(f"- Composition: {pick['composition']['note']}")
        inventory_support = pick.get('inventory_support', {})
        if inventory_support.get('total_bonus', 0) > 0:
            lines.append(
                "- Inventory support: "
                + "; ".join(
                    f"{match['explanation']} ({match['match_reason']})"
                    for match in inventory_support.get('matches', [])[:2]
                )
            )
        if pick['composition'].get('protein_add_on'):
            lines.append(f"- Protein add-on: {pick['composition']['protein_add_on']}")
        side = pick['composition'].get('side')
        if side:
            lines.append(f"- Suggested side: {side['title']} — {side['reason']}")
        lines.append(f"- Recipe: `{pick['path']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_example_bundle(
    payload: dict[str, Any],
    dinners_per_week: int,
    history_path: Path | None,
    ignore_history: bool,
    inventory_state: dict[str, Any] | None,
    prioritize_inventory: bool,
) -> dict[str, Any]:
    return {
        name: build_plan(
            payload,
            name,
            dinners_per_week,
            history_path=history_path,
            ignore_history=ignore_history,
            inventory_state=inventory_state,
            prioritize_inventory=prioritize_inventory,
        )
        for name in PRESETS
    }


def write_outputs(
    paths: FoodBrainPaths,
    payload: dict[str, Any],
    dinners_per_week: int,
    history_path: Path | None,
    ignore_history: bool,
    inventory_state: dict[str, Any] | None,
    prioritize_inventory: bool,
) -> None:
    paths.ensure_runtime_dirs()
    bundle = build_example_bundle(payload, dinners_per_week, history_path, ignore_history, inventory_state, prioritize_inventory)
    write_atomic(paths.generated_planner_dir / "weekly-plans.json", json.dumps(bundle, indent=2) + "\n")

    overview_lines = ["# Kitchen Compass Weekly Planner v1 — Example Plans", ""]
    for name, plan in bundle.items():
        file_name = f"{name}.md"
        write_atomic(paths.planner_views_dir / file_name, render_plan_markdown(plan))
        overview_lines.append(f"- [{plan['preset_label']}](./{file_name})")
    overview_lines.append("")
    write_atomic(paths.planner_views_dir / "README.md", "\n".join(overview_lines))


def build_parser() -> argparse.ArgumentParser:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument(
        "--data-root",
        help="Household data root. Defaults to ./kitchen-compass-data, except when run from the installed skill root it defaults to ../kitchen-compass-data so household data stays outside the skill.",
    )
    pre_parser.add_argument("--verbose", action="store_true", help="Print the resolved data root to stderr.")
    pre_args, _ = pre_parser.parse_known_args()
    paths = FoodBrainPaths.from_root(resolve_data_root(pre_args.data_root, verbose=pre_args.verbose))
    default_preset, default_dinners_per_week, default_prioritize_inventory = planner_defaults(paths)

    parser = argparse.ArgumentParser(description="Build lean weekly dinner plans from the portable Kitchen Compass query catalog.", parents=[pre_parser])
    parser.add_argument("--preset", choices=sorted(PRESETS), default=default_preset)
    parser.add_argument("--dinners-per-week", type=int, default=default_dinners_per_week)
    parser.add_argument("--include-aspirational", action="store_true", help="Allow aspirational dinners into the candidate pool.")
    parser.add_argument("--json", action="store_true", help="Print plan JSON instead of markdown.")
    parser.add_argument("--write-views", action="store_true", help="Write example planner outputs for all presets under generated/planner/.")
    parser.add_argument("--history-file", help="Override the meal history JSONL path.")
    parser.add_argument("--ignore-history", action="store_true", help="Disable history-aware scoring for this run.")
    inventory_group = parser.add_mutually_exclusive_group()
    inventory_group.add_argument("--prioritize-inventory", dest="prioritize_inventory", action="store_true", help="Increase the weight of strong inventory matches without overriding hard planner constraints.")
    inventory_group.add_argument("--no-prioritize-inventory", dest="prioritize_inventory", action="store_false", help="Keep inventory as a light planning nudge.")
    parser.set_defaults(prioritize_inventory=default_prioritize_inventory)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = FoodBrainPaths.from_root(resolve_data_root(args.data_root, verbose=args.verbose))
    payload = load_catalog(paths.generated_query_dir / "recipe-catalog.json")
    history_path = Path(args.history_file).expanduser().resolve() if args.history_file else paths.history_file
    inventory_state = load_inventory_state(paths)

    if args.write_views:
        write_outputs(paths, payload, args.dinners_per_week, history_path, args.ignore_history, inventory_state, args.prioritize_inventory)

    plan = build_plan(
        payload,
        args.preset,
        args.dinners_per_week,
        include_aspirational=args.include_aspirational,
        history_path=history_path,
        ignore_history=args.ignore_history,
        inventory_state=inventory_state,
        prioritize_inventory=args.prioritize_inventory,
    )
    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        print(render_plan_markdown(plan))


if __name__ == "__main__":
    main()
