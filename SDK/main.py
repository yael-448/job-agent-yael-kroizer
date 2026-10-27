"""Run the scenario on the Agent SDK version.

    python SDK/main.py --scenario scenario.json --out results/sdk.json

Runs on your Claude Code login. ANTHROPIC_API_KEY must NOT be set, or billing moves to the key.
"""
import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

from agent import SdkAgent  # noqa: E402
from shared.chat import run_chat  # noqa: E402
from shared.runner import run_scenario  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario")
    ap.add_argument("--out")
    ap.add_argument("--chat", action="store_true", help="talk to the agent yourself")
    args = ap.parse_args()
    if os.environ.pop("ANTHROPIC_API_KEY", None):
        print("[SDK/main.py] ANTHROPIC_API_KEY removed for this run, so it uses your Claude Code login")
    if args.chat:
        run_chat("sdk", SdkAgent)
    elif args.scenario and args.out:
        run_scenario("sdk", SdkAgent, args.scenario, args.out)
    else:
        ap.error("use --chat, or --scenario and --out")


if __name__ == "__main__":
    main()
