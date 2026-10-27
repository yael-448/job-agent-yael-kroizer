"""Run the scenario on the raw-API version.

    python API/main.py --scenario scenario.json --out results/api.json

Needs ANTHROPIC_API_KEY set in the terminal (never in code or git).
"""
import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

import anthropic  # noqa: E402

from agent import ApiAgent  # noqa: E402
from shared.runner import run_scenario  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. In PowerShell: $env:ANTHROPIC_API_KEY = \"sk-ant-...\"")
    client = anthropic.Anthropic()
    run_scenario("api", lambda state_dir: ApiAgent(client, state_dir), args.scenario, args.out)


if __name__ == "__main__":
    main()
