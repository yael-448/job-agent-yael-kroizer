"""Conversation history on disk, append-only (JSON lines).

Records:
  {"type": "message", "message": {...}}           one API message, content blocks verbatim
  {"type": "compaction", "summary": "...", ...}   written by compaction.py; earlier messages
                                                  are replaced by the summary when loading
Nothing is ever rewritten or deleted, so the full transcript stays on disk.
"""
import json
from pathlib import Path

from . import log


def to_dict(block) -> dict:
    """SDK content block -> plain dict, unchanged (thinking blocks must round-trip exactly)."""
    if isinstance(block, dict):
        return block
    return block.model_dump(mode="json", exclude_none=True)


class History:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.messages: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            log(__file__, f"no history at {self.path.name}, starting a new conversation")
            return
        records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]
        for rec in records:
            if rec["type"] == "compaction":
                self.messages = [summary_message(rec["summary"])]
            else:
                self.messages.append(rec["message"])
        log(__file__, f"loaded {len(records)} records -> {len(self.messages)} messages in context")

    def _write(self, rec: dict) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def append(self, role: str, content) -> None:
        if not isinstance(content, str):
            content = [to_dict(b) for b in content]
        msg = {"role": role, "content": content}
        self.messages.append(msg)
        self._write({"type": "message", "message": msg})
        log(__file__, f"appended {role} message (#{len(self.messages)})")

    def append_compaction(self, summary: str, replaced: int) -> None:
        self._write({"type": "compaction", "summary": summary, "replaced_messages": replaced})
        self.messages = [summary_message(summary)]
        log(__file__, f"compaction record appended; {replaced} messages -> 1 summary")


def summary_message(summary: str) -> dict:
    return {"role": "user", "content": [{"type": "text", "text": f"<conversation_summary>\n{summary}\n</conversation_summary>"}]}
