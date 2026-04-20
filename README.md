# Kitchen Compass

Kitchen Compass is a portable household meal-planning skill focused on three practical jobs:

- **plan dinners** from a reusable recipe catalog
- **remember inventory** without pretending to track it automatically
- **surface weekly store deals** in a manual/guided, retailer-aware workflow

It is designed as a reusable skill/engine. Household-specific live data stays outside the published skill.

## What it does today

### 1. Weekly dinner planning
Kitchen Compass can build weekly dinner plans from a structured recipe catalog and household preferences.

Core planning behavior includes:
- preset-driven weekly planning
- history-aware shaping
- optional inventory influence
- plain-language planner explanations

### 2. Inventory-aware planning
Inventory is a real signal in the planner.

Kitchen Compass supports:
- structured remembered inventory state
- explicit add / set / confirmed-use flows
- a boolean `planning.prioritize_inventory` toggle
- planner explanations when inventory helped

It does **not** pretend to track inventory in real time.

### 3. Manual/guided weekly deal workflow
Deals are **not** planner scoring input.

Instead, Kitchen Compass supports:
- saved store definitions
- saved source URLs
- per-store `retrieval_recipe` notes for brittle retailer-specific flows
- a preferred weekly scan schedule in config
- per-store weekly deal brief stubs
- a combined weekly deal sheet grouped by category

Current grouped output categories:
- meat
- starch
- dairy
- fruit-veg
- beverages
- misc

Display format is intentionally simple:

`Store — Product — Sale Price — Normal Price`

## Product boundary
Kitchen Compass is honest about what is manual versus automated.

### It does
- preserve household structure and context
- preserve retailer-specific retrieval recipes
- prepare scan packets and combined outputs
- support manual/guided curation cleanly

### It does not
- promise universal autonomous retailer scraping
- pretend every store works the same way
- silently change meal plans based on deals
- hide brittle store-specific retrieval behavior

## Important directories

### Canonical skill contents
- `SKILL.md` — skill instructions and usage
- `references/` — contracts, flow docs, and feature boundaries
- `scripts/` — canonical runtime scripts
- `assets/sample-household/` — sample seeded household structure

### Key scripts
- `setup_household.py` — bootstrap a fresh household data root
- `build_weekly_plan.py` — render weekly dinner plans
- `manage_inventory.py` — explicit inventory updates
- `manage_deal_sources.py` — saved stores, retrieval recipes, and scan schedule
- `prepare_weekly_deal_scan.py` — create weekly scan packet + per-store stubs
- `render_weekly_deal_brief.py` — render a single-store weekly brief
- `render_combined_weekly_deal_sheet.py` — combine store briefs into one grouped output

## Typical workflow

### Household setup
```bash
python3 scripts/setup_household.py --data-root ~/kitchen-compass-data
```

### Configure weekly deal stores
```bash
python3 scripts/manage_deal_sources.py --data-root ~/kitchen-compass-data add-store \
  --label "GIANT - Boot Rd" \
  --retailer giant \
  --source-type circular-url \
  --source-url "https://example.com/circular" \
  --retrieval-step "Resolve saved store before trusting the flyer" \
  --default
```

### Set preferred scan time
```bash
python3 scripts/manage_deal_sources.py --data-root ~/kitchen-compass-data set-scan-schedule \
  --day-of-week friday \
  --time-local 12:00 \
  --timezone America/New_York
```

### Prepare the weekly scan packet
```bash
python3 scripts/prepare_weekly_deal_scan.py --data-root ~/kitchen-compass-data --week-of 2026-04-21
```

### Render the combined deal sheet
```bash
python3 scripts/render_combined_weekly_deal_sheet.py --data-root ~/kitchen-compass-data
```

## Publish truth
This repo contains the **canonical portable skill only**.

It intentionally excludes:
- private household data
- live personal store setup
- daily notes / memory
- other workspace-specific context

## Status
Kitchen Compass is publishable as a **manual/guided MVP**.

That means:
- the data model is real
- the workflow is real
- the boundaries are explicit
- retailer-specific brittleness is acknowledged rather than hidden
