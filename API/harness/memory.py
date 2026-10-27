"""Long-term memory: preferences, decisions and facts in <state>/profile.json.

Written by the `remember` tool (kept across sessions, old values kept in history).
Read two ways:
  - summary(): a compact one-line-per-entry digest injected by context.py every turn
  - the `recall` tool, when the model needs an entry's details or change history
"""
from shared.store import Store

from . import log

MAX_SUMMARY_ENTRIES = 12
MAX_VALUE_CHARS = 80


class Memory:
    def __init__(self, store: Store):
        self.store = store
        n = len(store.profile()["entries"])
        log(__file__, f"profile.json has {n} entries")

    def summary(self) -> str:
        entries = self.store.profile()["entries"]
        if not entries:
            return "(no stored preferences yet)"
        recent = sorted(entries.items(), key=lambda kv: kv[1]["updated_at"], reverse=True)[:MAX_SUMMARY_ENTRIES]
        lines = []
        for key, e in sorted(recent):
            value = e["value"] if len(e["value"]) <= MAX_VALUE_CHARS else e["value"][:MAX_VALUE_CHARS] + "..."
            lines.append(f"- {key} ({e['kind']}): {value}")
        more = len(entries) - len(recent)
        if more > 0:
            lines.append(f"- ...{more} older entries, use recall")
        log(__file__, f"memory summary: {len(recent)} of {len(entries)} entries")
        return "\n".join(lines)
