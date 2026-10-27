"""Interactive chat with either version: python SDK/main.py --chat

State lives in results/state_chat_<impl>/ and is NOT wiped, so the agent remembers
you between chats. VS Code's terminal renders Hebrew correctly; for a console that
shows it mirrored, set JOB_AGENT_BIDI=1 to reorder it.
"""
import os
import sys

from .runner import ROOT


def get_display(text: str) -> str:
    if os.environ.get("JOB_AGENT_BIDI") != "1":
        return text
    from bidi import get_display as reorder
    return reorder(text)


def show(text: str) -> None:
    for line in text.splitlines() or [""]:
        print(get_display(line))


def run_chat(impl: str, make_agent) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    state_dir = ROOT / "results" / f"state_chat_{impl}"
    state_dir.mkdir(parents=True, exist_ok=True)
    agent = make_agent(state_dir)
    show(f"צ'אט עם סוכן חיפוש העבודה ({impl}). כדי לצאת, כתבי: יציאה")
    show(f"המועמדות נשמרות בתיקייה: {state_dir / 'outbox'}")
    try:
        while True:
            try:
                text = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if text in ("יציאה", "exit", "quit"):
                break
            if text:
                rec = agent.run_turn(text)
                print()
                show(rec["reply"])
                print(f"  (tools: {', '.join(rec['tools_called']) or '-'} | cost ${rec['cost_usd']:.4f})")
    finally:
        agent.close()
