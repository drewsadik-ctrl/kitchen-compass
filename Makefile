.PHONY: test smoke plan

test:
	pytest tests/ -v

smoke:
	@SMOKE=$$(mktemp -d); \
	set -e; \
	python3 scripts/setup_household.py --data-root "$$SMOKE" > /dev/null; \
	python3 scripts/validate_recipes.py --data-root "$$SMOKE" > /dev/null; \
	python3 scripts/build_recipe_query_index.py --data-root "$$SMOKE" > /dev/null; \
	python3 scripts/manage_inventory.py --data-root "$$SMOKE" add \
	  --label "Ground beef" --location freezer --kind protein --amount 3 --unit lb > /dev/null; \
	python3 scripts/build_weekly_plan.py --data-root "$$SMOKE" --preset balanced > /dev/null; \
	python3 scripts/record_meal_history.py --data-root "$$SMOKE" --event-type made --recipe burger-bowls > /dev/null; \
	python3 scripts/query_recipes.py --data-root "$$SMOKE" --meal-type dinner > /dev/null; \
	echo "SMOKE TEST PASSED ($$SMOKE)"

plan:
	@SMOKE=$$(mktemp -d); \
	python3 scripts/setup_household.py --data-root "$$SMOKE" > /dev/null; \
	python3 scripts/build_recipe_query_index.py --data-root "$$SMOKE" > /dev/null; \
	python3 scripts/build_weekly_plan.py --data-root "$$SMOKE" --preset balanced
