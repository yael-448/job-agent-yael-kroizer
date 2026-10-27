"""Tool schemas, dispatch, and errors returned to the model as is_error results."""
import json

from shared.store import Store
from shared.tools_impl import FUNCTIONS, TOOL_SPECS, ToolError

from . import log

MAX_RESULT_CHARS = 2000  # hard cap so one tool result can never flood the context


def schemas() -> list[dict]:
    """JSON schemas sent to the model, in a fixed order (a stable prefix keeps the cache valid)."""
    return [dict(spec) for spec in TOOL_SPECS]


class ToolBox:
    def __init__(self, store: Store, fetch=None):
        self.store = store
        self.fetch = fetch  # injectable job-board fetcher for offline tests

    def run(self, block) -> dict:
        """Execute one tool_use block and return its tool_result block."""
        name, args = block.name, dict(block.input)
        fn = FUNCTIONS.get(name)
        try:
            if fn is None:
                raise ToolError(f"unknown tool '{name}'")
            if name == "search_jobs" and self.fetch:
                args["fetch"] = self.fetch
            text = fn(self.store, **args)
            is_error = False
        except ToolError as e:
            text, is_error = f"error: {e}", True
        except TypeError as e:  # wrong / missing arguments
            text, is_error = f"error: bad arguments for {name}: {e}", True
        if len(text) > MAX_RESULT_CHARS:
            text = text[:MAX_RESULT_CHARS] + " ...[truncated]"
        shown = json.dumps({k: v for k, v in args.items() if k != "fetch"}, ensure_ascii=False)[:120]
        log(__file__, f"{name}({shown}) -> {'ERROR ' if is_error else ''}{text.splitlines()[0][:100]}")
        result = {"type": "tool_result", "tool_use_id": block.id, "content": text}
        if is_error:
            result["is_error"] = True
        return result
