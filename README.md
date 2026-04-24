# Kitchen Compass

A deterministic, explainable weekly dinner planner. Not a random weekly recipe picker — a weighted candidate ranker with hard constraints, history-aware drift control, and composition-aware explanations. Optionally, it remembers freezer/pantry inventory and helps you triage weekly grocery circulars.

The thesis: one great dinner is not enough if it makes the whole week annoying. Kitchen Compass optimizes for a good **week**, not a good single pick.

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

Every pick shows *why* it made the cut. If a plan feels wrong, the reasons tell you where the pressure came from.

## How the planner works

Kitchen Compass runs a strict five-level signal hierarchy:

1. **Hard constraints** — preset-level caps on involved meals, expensive meals, friction-heavy meals, aspirational/testing meals, side-dependent dinners. These kick candidates out of the week entirely, regardless of how well they'd score.
2. **Core scoring signals** — weighted preferences over effort, friction, cost, status, serving profile, composition, and context.
3. **Week-balance shaping** — penalties for repeating a protein family, stacking side-dependent dinners, stacking moderate-or-involved effort meals.
4. **History-aware shaping** — recent-repeat penalties, long-gap bonuses, recent protein/role concentration penalties. `made` events count more than `planned` events.
5. **Optional signals** — remembered inventory contributes a small capped bonus that can nudge tie-breakers but cannot repair a bad week.

Weekly deal briefs sit **outside** that stack. They can inform a human decision to pivot the week, but they never enter planner scoring. Letting sale prices into the loop is how you end up eating what's on sale instead of what fits the week.

Presets (`balanced`, `easy`, `cheap`, `low-carb`, `hosting-friendly`) change both hard caps and scoring weights. Full explanation in `references/planning-logic.md`; exact numbers in `scripts/planner/presets.py`.

## What it does

Plan a week: preset-driven, history-aware, composition-aware dinner planning with per-pick explanations and suggested sides pulled from pairing intelligence. Catalog recipes: authored markdown in a frozen schema, validated on write, indexed for query and planning. Remember inventory: explicit add/use/confirm flows, no silent subtraction — the planner never fakes stock math. Triage weekly deals: saved stores, per-store retrieval recipes, weekly scan packets, a combined deal sheet grouped by category.

## What it does not

- Autonomously scrape retailer circulars. Deal retrieval is manual or guided; per-store `retrieval_recipe` notes capture what worked last time.
- Plan breakfast, lunch, snacks, or desserts. v1 is dinner + side. Other meal types can live in the schema, but the planner won't use them.
- Track real-time stock. Inventory is remembered approximate state, not a live count.
- Wash your car.

## Design principles

**Explainability over cleverness.** Every pick comes with reason strings. A plan that seems wrong can be debugged instead of re-rolled.

**Hard constraints and soft signals stay separated.** Whether a recipe is *allowed* in the week is a different question from how it *ranks*. Preserving that boundary is what keeps a high-scoring week from being a miserable one.

**Docs and code cannot silently drift.** The recipe schema lives in `references/recipe-schema.md` (human-readable) *and* `scripts/contract.py` (machine-used). A test parses the schema doc and diffs its enums against the code. Any change to one requires a matching change to the other in the same commit.

**Portable engine, separate user data.** The skill ships no real household data. The engine points at a `--data-root` you own. Move it, back it up, or version it independently.

**Authored vs generated is enforced.** Recipes, household config, inventory state, history, and deal inputs are authored. Everything under `generated/` is rebuildable. Nothing under `generated/` is ever an input.

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

Each takes `--data-root <path>` (or reads `KITCHEN_COMPASS_DATA_ROOT`). The legacy `FOOD_BRAIN_DATA_ROOT` still works but is deprecated.

- `setup_household.py` — bootstrap a fresh data root from the sample household
- `validate_recipes.py` — enforce the frozen recipe schema
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

make test    # pytest: contract, validation, planner scoring, history, golden path
make smoke   # full CLI golden path against a throwaway data root
make plan    # bootstrap a sample root and render one plan
```

Both `make test` and `make smoke` must pass before opening a PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for the invariants — especially the frozen recipe schema and the rule against casually tuning planner weights.

## Status

v1. The active planner guarantees dinner + side. The deal workflow is manual or guided by design. Inventory is approximate household memory, not real-time stock. Everything documented here is honest about its seams.

## License

[MIT](LICENSE)
