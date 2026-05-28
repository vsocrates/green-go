"""
Pydantic AI agent: Home Energy Management Agent.

Receives an ObservationBundle, reasons about MER / cost / preferences,
emits a structured ActionPlan.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel

from agent.models import ActionPlan, ObservationBundle

load_dotenv()

# ---------------------------------------------------------------------------
# System prompt — loaded from CLAUDE.md at import time (file read only)
# ---------------------------------------------------------------------------

_CLAUDE_MD = Path(__file__).parent.parent / "CLAUDE.md"


def _load_system_prompt() -> str:
    if _CLAUDE_MD.exists():
        return _CLAUDE_MD.read_text()
    return (
        "You are the Home Energy Management Agent. "
        "You receive an ObservationBundle as JSON and emit a single ActionPlan JSON. "
        "Minimize marginal grid emissions and cost while respecting user preferences. "
        "Only emit actions for real Enode-supported device capabilities. "
        "Never invent device IDs or capabilities."
    )


SYSTEM_PROMPT = _load_system_prompt()

# ---------------------------------------------------------------------------
# Lazy agent construction — avoids API key requirement at import time
# ---------------------------------------------------------------------------

_energy_agent: Agent[None, ActionPlan] | None = None


def _get_agent() -> Agent[None, ActionPlan]:
    global _energy_agent
    if _energy_agent is None:
        model = AnthropicModel(os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"))
        _energy_agent = Agent(
            model=model,
            output_type=ActionPlan,
            system_prompt=SYSTEM_PROMPT,
        )
    return _energy_agent


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def run_agent(bundle: ObservationBundle) -> ActionPlan:
    """Run the energy management agent on a bundle and return the ActionPlan."""
    bundle_json = bundle.model_dump_json(indent=2)
    result = await _get_agent().run(bundle_json)
    return result.output


def run_agent_sync(bundle: ObservationBundle) -> ActionPlan:
    """Synchronous wrapper around run_agent."""
    bundle_json = bundle.model_dump_json(indent=2)
    result = _get_agent().run_sync(bundle_json)
    return result.output
