"""
Entry point for running the energy management agent.

Loads the ObservationBundle from a JSON file (default: data/observation_bundle_example.json).

Usage:
    python -m agent.run
    python -m agent.run --input data/observation_bundle_example.json
    python -m agent.run --pretty   # human-readable output instead of JSON
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from agent.agent import run_agent
from agent.models import ObservationBundle

_DEFAULT_INPUT = Path(__file__).parent.parent / "data" / "observation_bundle_example.json"


def load_bundle(path: Path) -> ObservationBundle:
    with open(path) as f:
        raw = json.load(f)
    return ObservationBundle.model_validate(raw)


async def main(input_path: Path, pretty: bool = False) -> None:
    print(f"Loading ObservationBundle from {input_path}...", file=sys.stderr)
    bundle = load_bundle(input_path)

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
    parser = argparse.ArgumentParser(description="Run energy agent on an ObservationBundle JSON file")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=_DEFAULT_INPUT,
        help="Path to ObservationBundle JSON (default: data/observation_bundle_example.json)",
    )
    parser.add_argument("--pretty", action="store_true", help="Human-readable output instead of JSON")
    args = parser.parse_args()
    asyncio.run(main(input_path=args.input, pretty=args.pretty))
