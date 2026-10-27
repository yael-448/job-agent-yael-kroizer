"""Interactive chat with either version: python SDK/main.py --chat

State lives in results/state_chat_<impl>/ and is NOT wiped, so the agent remembers
you between chats. Hebrew is reordered for terminals that do not render
right-to-left text (most Windows consoles show it mirrored).
"""
import sys

from .runner import ROOT

try:
    from bidi import get_display
except ImportError:  # optional dependency
    def get_display(text: str) -> str:
        return text


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
