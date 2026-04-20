---
name: kitchen-compass
description: Build and operate a portable Kitchen Compass meal-planning workspace. Use when setting up a Kitchen Compass household data root, converting recipes into the Kitchen Compass markdown contract, building/querying the dinner-and-side catalog, generating weekly dinner plans, or recording meal history without mixing the reusable engine with household-specific data.
---

# Kitchen Compass

Use this skill to keep the reusable Kitchen Compass engine separate from household data.

## Operating rules

- Keep the skill directory portable. Do not store a user's real recipes, inventory, or history inside the skill.
- Treat the user-data root as the authored source of truth. Generated files are rebuildable.
- Inventory changes must be explicit; never silently subtract or fabricate real-time stock state.
- Treat the installed skill directory as the canonical source for portable engine logic, templates, and contract docs. If a separate live or development copy exists, sync changes deliberately instead of editing both copies independently.
- Preserve the frozen recipe contract. Exact recipe labels, section order, enum sets, and composition semantics live in `references/recipe-schema.md`.
- Preserve runtime assumptions and history shape from `references/runtime-contract.md`.
- If machine-used contract constants must change, update `scripts/contract.py` deliberately and then keep the reference docs aligned.
- Stay conservative: this v1 engine only guarantees dinner + side query/planner support.

## Decide what to read first

- For setup or folder creation, read `references/setup-flow.md`.
- For recipe editing, migration, validation, or exact field values, read `references/recipe-schema.md`.
- For history editing or runtime expectations, read `references/runtime-contract.md`.
- For optional weekly deal brief setup or output shape, read `references/weekly-deal-brief.md`.
- For portability questions or boundary rules, read `references/user-data-layout.md` and `references/live-vs-portable-boundary.md`.

## Use the bundled scripts

Assume the shell is currently in the installed `kitchen-compass` skill directory:

```bash
cd /path/to/kitchen-compass
```

Then run scripts from `scripts/` against a household data root.

### Initialize a new household data root

```bash
python3 scripts/setup_household.py --data-root /path/to/kitchen-compass-data
```

This creates the canonical user-data layout and copies the sample household stub, the sample `burger-bowls.md` recipe, and `_recipe-template.md`.

### Build the query catalog

```bash
python3 scripts/build_recipe_query_index.py --data-root /path/to/kitchen-compass-data
```

### Query recipes

```bash
python3 scripts/query_recipes.py --data-root /path/to/kitchen-compass-data --meal-type dinner --wants-side
```

### Add or update remembered inventory

```bash
python3 scripts/manage_inventory.py --data-root /path/to/kitchen-compass-data add --label "Ground beef" --location freezer --kind protein --amount 3 --unit lb
python3 scripts/manage_inventory.py --data-root /path/to/kitchen-compass-data use --item freezer-ground-beef --amount 1 --unit lb --confirmed
```

### Build a weekly plan

```bash
python3 scripts/build_weekly_plan.py --data-root /path/to/kitchen-compass-data --preset balanced
```

### Manage optional weekly deal sources

```bash
python3 scripts/manage_deal_sources.py --data-root /path/to/kitchen-compass-data show
python3 scripts/manage_deal_sources.py --data-root /path/to/kitchen-compass-data add-store --label "Giant - Boot Rd" --retailer giant --source-type circular-url --source-url "https://example.com/circular" --retrieval-step "Resolve saved store before trusting the flyer" --default
python3 scripts/manage_deal_sources.py --data-root /path/to/kitchen-compass-data set-scan-schedule --day-of-week friday --time-local 12:00 --timezone America/New_York
```

### Prepare the weekly deal scan and combine store outputs

```bash
python3 scripts/prepare_weekly_deal_scan.py --data-root /path/to/kitchen-compass-data --week-of 2026-04-21
python3 scripts/render_combined_weekly_deal_sheet.py --data-root /path/to/kitchen-compass-data
```

### Render a manual single-store weekly deal brief

```bash
python3 scripts/render_weekly_deal_brief.py --data-root /path/to/kitchen-compass-data
```

### Record history

```bash
python3 scripts/record_meal_history.py --data-root /path/to/kitchen-compass-data --event-type made --recipe burger-bowls
```

## Workflow

1. Initialize or inspect the user-data root.
2. Add or normalize recipe markdown files using the frozen template.
3. Validate recipes against the frozen contract.
4. Rebuild the query catalog after recipe changes.
5. Query or plan from generated outputs.
6. Optionally add or confirm inventory state.
7. Optionally configure manual weekly deal brief store/source setup and preferred scan schedule.
8. Prepare the weekly deal scan packet, curate per-store briefs, and render the combined weekly deal sheet.
9. Record meal history so planning can use recency.

## Assets

- `assets/recipe-template.md` is the reusable authored template.
- `assets/sample-household/` is seed content only. It now includes a sample `burger-bowls.md` dinner recipe; replace or expand it with real household data as needed.
