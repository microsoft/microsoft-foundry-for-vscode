"""Copilot skills agent.

Auto-discovers skill directories (folders containing SKILL.md)
and serves the agent via the Foundry responses protocol.
"""

import os
import pathlib
import sys

from dotenv import load_dotenv
load_dotenv(override=False)

from agent import CopilotAgent
from server import CopilotFoundryAdapter


def _discover_skill_directories() -> list[str]:
    """Return the project root if any child folder contains SKILL.md."""
    root = pathlib.Path(__file__).parent
    if any(root.glob("*/SKILL.md")):
        return [str(root.resolve())]
    return []


def create_agent() -> CopilotAgent:
    return CopilotAgent(skill_directories=_discover_skill_directories())


def _resolve_port() -> int | None:
    raw = os.environ.get("PORT")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        print(f"Invalid PORT value {raw!r}; defaulting to framework port.")
        return None


if __name__ == "__main__":
    if not os.environ.get("GITHUB_TOKEN"):
        print("Missing GitHub Token. Make sure the .env file has one. See README for details.")
        sys.exit(1)
    adapter = CopilotFoundryAdapter(create_agent())
    adapter.run(port=_resolve_port())
