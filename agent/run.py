"""
Entry point for running the energy management agent on dummy data.

Usage:
    python -m agent.run
    python -m agent.run --pretty   # pretty-print only (no JSON dump)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from agent.agent import run_agent
from agent.dummy_data import make_dummy_bundle


async def main(pretty: bool = False) -> None:
    print("Building dummy ObservationBundle...", file=sys.stderr)
    bundle = make_dummy_bundle()

    print(f"Invoking energy agent (now={bundle.now.isoformat()})...", file=sys.stderr)
    plan = await run_agent(bundle)

    if pretty:
        print(f"\nplan_id:   {plan.plan_id}")
        print(f"objective: {plan.objective}")
        print(f"generated: {plan.generated_at.isoformat()}")
        print(f"valid_until: {plan.valid_until.isoformat()}")
        print(f"total_actions: {plan.plan_summary.total_actions}")
        print(f"\nContext:")
        print(f"  grid_price:       ${plan.context.current_grid_price_per_kwh}/kWh")
        print(f"  solar_next_6h:    {plan.context.forecast_solar_kwh_next_6h} kWh")
        print(f"  load_next_6h:     {plan.context.forecast_load_kwh_next_6h} kWh")
        print(f"  home_occupied:    {plan.context.home_occupied}")

        for cls, actions in [
            ("vehicles", plan.actions.vehicles),
            ("chargers", plan.actions.chargers),
            ("batteries", plan.actions.batteries),
            ("hvacs", plan.actions.hvacs),
        ]:
            if actions:
                print(f"\n{cls.upper()}:")
                for alias, act in actions.items():
                    print(f"  [{alias}]")
                    print(f"    action:   {act.action}")
                    print(f"    schedule: {act.schedule.model_dump()}")
                    print(f"    reason:   {act.reason}")
                    print(f"    priority: {act.priority}")

        if plan.unmet_preferences:
            print("\nUNMET PREFERENCES:")
            for u in plan.unmet_preferences:
                print(f"  [{u.severity}] {u.preference_id}: {u.reason}")
        else:
            print("\nAll preferences satisfied.")
    else:
        print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run energy agent on dummy data")
    parser.add_argument("--pretty", action="store_true", help="Human-readable output instead of JSON")
    args = parser.parse_args()
    asyncio.run(main(pretty=args.pretty))
