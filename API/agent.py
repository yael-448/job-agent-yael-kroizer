"""The job-search agent on the raw Messages API, wired from the harness/ modules."""
from pathlib import Path

from shared.store import Store

from harness import compaction, context, log, loop
from harness.history import History
from harness.memory import Memory
from harness.tokens import TurnUsage
from harness.tools import ToolBox, schemas

MODEL = "claude-opus-5-5"
EFFORT = "medium"


class ApiAgent:
    def __init__(self, client, state_dir: Path, fetch=None):
        self.client = client
        self.store = Store(state_dir)
        self.history = History(Path(state_dir) / "api_history.jsonl")
        self.memory = Memory(self.store)
        self.toolbox = ToolBox(self.store, fetch=fetch)
        self.system = context.system_blocks()
        self.request = {
            "model": MODEL,
            "max_tokens": 16000,
            "tools": schemas(),
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": EFFORT},
        }
        self.last_prompt_tokens = 0
        log(__file__, f"agent ready: model={MODEL} effort={EFFORT}")

    def run_turn(self, text: str) -> dict:
        usage = TurnUsage(MODEL)
        if compaction.needs_compaction(self.last_prompt_tokens) and self.history.messages:
            usage.last_prompt_tokens = self.last_prompt_tokens
            compaction.compact(self.client, self.request, self.system, self.history, usage)
        self.history.append("user", context.user_turn(text, self.memory, self.store))
        reply, tools_called = loop.run(self.client, self.request, self.system, self.history, self.toolbox, usage)
        self.last_prompt_tokens = usage.last_prompt_tokens
        usage.report()
        return {
            "reply": reply,
            "tokens": usage.as_dict(),
            "model_calls": usage.calls,
            "tools_called": tools_called,
            "cost_usd": round(usage.cost, 5),
        }

    def close(self) -> None:
        log(__file__, "session closed; state is on disk")
