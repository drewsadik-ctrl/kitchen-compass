# Kitchen Compass

Meal planning, outsourced.

You have 20-ish dinners you actually cook. The problem isn't that you need more recipes. It's that every Sunday you have to pick which four or five to do this week, and somehow you end up with chicken three nights in a row, two dishes that each demand their own side, and a recipe you also made last Tuesday.

Kitchen Compass does the picking for you. Give it your recipes, tell it what kind of week you want (easy, cheap, balanced, a little special for company), and it builds the week: varied proteins, reasonable effort spread across the weeknights, side suggestions where they fit, and nothing you just made. Every pick comes with a short explanation so you can see *why* it's in the plan, and swap it out if the reason doesn't land.

It learns from what you cook. It remembers what's in your freezer if you tell it. And if you shop the same grocery store each week, it can help you triage the circular without opening the flyer yourself.

The goal isn't the fanciest week. It's the week that actually works.

## Quickstart

```bash
git clone https://github.com/drewsadik-ctrl/kitchen-compass.git
cd kitchen-compass
python3 scripts/setup_household.py --data-root ~/kitchen-compass-data
python3 scripts/build_recipe_query_index.py --data-root ~/kitchen-compass-data
python3 scripts/build_weekly_plan.py --data-root ~/kitchen-compass-data --preset balanced
```

That's a working plan against the shipped sample household. Swap the sample recipes in `~/kitchen-compass-data/recipes/` for your own, rebuild the index, and you're planning real weeks.

## What a plan looks like

Real output from the sample household on the balanced preset:

```
# Balanced week

Default practical week: mostly trusted, low-friction dinners with one slot
for something slightly more interesting.

- Target dinners: 3
- Picked dinners: 3
- Protein variety: {"beef": 1, "chicken": 1, "pork": 1}
- Effort mix: {"easy": 3}
- Friction mix: {"low": 3}

## Dinner 1 — Burger Bowls
- Why it made the cut: easy to cook; low ingredient friction; trusted house
  recipe; good family-table fit; self-contained dinner
- Composition: self-contained dinner this week; no extra side is required.

## Dinner 2 — Slow Cooker Garlic Parmesan Chicken
- Why it made the cut: easy to cook; low ingredient friction; trusted house
  recipe; good family-table fit; self-contained dinner
- Composition: self-contained dinner this week; no extra side is required.

## Dinner 3 — Baked Pork Chops
- Why it made the cut: easy to cook; low ingredient friction; trusted house
  recipe; good family-table fit; needs side support
- Composition: treat this as a main that wants a side: Garlic Mashed Potatoes.
- Suggested side: Garlic Mashed Potatoes — dinner explicitly asks for
  garlic mashed potatoes.
```

Every pick shows why it made the cut. If a plan feels wrong, the reasons tell you where the pressure came from, so you can swap with intent instead of re-rolling the whole week.

## What it does

- **Plans a week, not just a dinner.** Preset-driven, history-aware, composition-aware, with per-pick explanations and suggested sides pulled from your own pairing notes.
- **Catalogs your recipes.** Authored markdown in a consistent schema, validated on write, indexed for querying and planning.
- **Remembers inventory.** Explicit add and confirmed-use flows. The planner will nudge toward dinners you already have ingredients for, but it never fakes stock math.
- **Triages weekly deals.** Saved stores, per-store retrieval notes that remember what worked last time, and a combined deal sheet grouped by category (meat, starch, dairy, produce, beverages, misc).

## What it does not

- **Scrape retailer circulars autonomously.** Deal retrieval is manual or guided. The per-store retrieval notes capture what worked last time, so it gets easier with repetition.
- **Plan breakfast, lunch, snacks, or desserts.** v1 is dinner plus side. Other meal types can live in the schema, but the planner will not use them.
- **Track real-time stock.** Inventory is remembered approximate state, not a live count.
- **Wash your car.**

## Design principles

**Explainability over cleverness.** Every pick comes with reason strings. A plan that seems wrong can be debugged instead of re-rolled.

**Hard constraints and soft signals stay separated.** Whether a recipe is *allowed* in the week is a different question from how it *ranks*. Preserving that boundary is what keeps a high-scoring week from being a miserable one.

**Your recipes, not somebody else's.** Kitchen Compass is not a recipe discovery tool. It operates on the dinners you already know how to make, which is what most households actually need help with.

**Portable engine, separate user data.** The skill ships no real household data. The engine points at a `--data-root` you own. Move it, back it up, or version it independently.

**Authored vs. generated is enforced.** Recipes, household config, inventory state, history, and deal inputs are things you author. Everything under `generated/` is rebuildable from those inputs. Nothing under `generated/` is ever read back in as an input.

## How the planner works

Under the hood, Kitchen Compass runs a strict five-level signal hierarchy:

1. **Hard constraints.** Preset-level caps on involved meals, expensive meals, friction-heavy meals, aspirational or testing meals, and side-dependent dinners. These kick candidates out of the week entirely, regardless of how well they would otherwise score.
2. **Core scoring signals.** Weighted preferences over effort, friction, cost, trustedness, serving profile, composition, and context.
3. **Week-balance shaping.** Penalties for repeating a protein family, stacking side-dependent dinners, stacking moderate-or-involved meals.
4. **History-aware shaping.** Recent-repeat penalties, long-gap bonuses, recent protein and role concentration penalties. Dinners you actually made count more than dinners you only planned.
5. **Optional signals.** Remembered inventory contributes a small capped bonus that can nudge tie-breakers but cannot repair a bad week.

Weekly deal briefs sit **outside** that stack. They can inform a human decision to pivot the week, but they never enter planner scoring. Letting sale prices into the loop is how you end up eating what's on sale instead of what fits the week.

Presets (`balanced`, `easy`, `cheap`, `low-carb`, `hosting-friendly`) change both hard caps and scoring weights. Full explanation in `references/planning-logic.md`. Exact numbers live in `scripts/planner/presets.py`.

## Repository layout

- `SKILL.md` — instructions for an agent operating Kitchen Compass
- `scripts/` — CLI entrypoints plus the `planner/` package (candidates, scoring, history, render)
- `scripts/contract.py` — single source of truth for schema constants and enums
- `references/` — recipe schema, runtime contract, planning logic, inventory logic, setup flow, deal brief contract, portability boundary
- `assets/sample-household/` — seeded sample recipes and household config
- `assets/recipe-template.md` — authoring template for new recipes
- `tests/` — pytest suite: contract alignment, validation, planner scoring, history, end-to-end golden path
- `Makefile` — `test`, `smoke`, `plan`

## Key scripts

Each takes `--data-root <path>` or reads `KITCHEN_COMPASS_DATA_ROOT`. The legacy `FOOD_BRAIN_DATA_ROOT` still works but is deprecated.

- `setup_household.py` — bootstrap a fresh data root from the sample household
- `validate_recipes.py` — enforce the recipe schema
- `build_recipe_query_index.py` — rebuild the query catalog from validated recipes
- `build_weekly_plan.py` — render a weekly plan against a preset
- `query_recipes.py` — filter recipes by meal type, composition, diet, etc.
- `manage_inventory.py` — explicit inventory updates
- `record_meal_history.py` — append history events
- `manage_deal_sources.py` — saved stores, retrieval recipes, scan schedule
- `prepare_weekly_deal_scan.py` — weekly scan packet and per-store stubs
- `render_weekly_deal_brief.py` — single-store weekly brief
- `render_combined_weekly_deal_sheet.py` — combined weekly sheet grouped by category

## Developing

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

make test    # pytest: contract alignment, validation, planner scoring, history, golden path
make smoke   # full CLI golden path against a throwaway data root
make plan    # bootstrap a sample root and render one plan
```

Both `make test` and `make smoke` should pass before opening a PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for the invariants, especially the frozen recipe schema and the rule against casually tuning planner weights.

## Status

v1. The active planner guarantees dinner plus side. The deal workflow is manual or guided by design. Inventory is approximate household memory, not real-time stock. Everything documented here is honest about its seams.

## License

[MIT](LICENSE)
