"""What goes into each turn.

Stable, cached every call : tool schemas + system prompt (never changes during a run)
Per user turn (appended)  : a short <context> block - memory digest + tracker counts
Fetched on demand by tools: job listings, full tracker, memory details, the CV

The full tracker, the CV and job descriptions are never pushed into the prompt.
"""
from collections import Counter

from shared.store import Store
from shared.tools_impl import SYSTEM_PROMPT

from . import log
from .memory import Memory


def system_blocks() -> list[dict]:
    return [{"type": "text", "text": SYSTEM_PROMPT}]


def user_turn(text: str, memory: Memory, store: Store) -> list[dict]:
    counts = Counter(j["status"] for j in store.jobs().values())
    tracker = ", ".join(f"{s}: {n}" for s, n in sorted(counts.items())) or "empty"
    ctx = f"<context>\nStored profile:\n{memory.summary()}\nTracker: {tracker}\n</context>"
    log(__file__, f"turn context: {len(ctx)} chars (profile digest + tracker counts: {tracker})")
    return [{"type": "text", "text": ctx}, {"type": "text", "text": text}]
