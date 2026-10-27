"""Token usage and cost per model call and per turn."""
from . import log

# USD per million tokens, claude-opus-5-5 (cache write = 1.25x input for the 5-minute TTL)
PRICES = {
    "claude-opus-5-5": {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00},
}


class TurnUsage:
    def __init__(self, model: str):
        self.price = PRICES[model]
        self.input = self.cache_read = self.cache_write = self.output = 0
        self.calls = 0
        self.last_prompt_tokens = 0  # size of the latest request, used by compaction.py

    def add(self, usage) -> None:
        i = usage.input_tokens or 0
        r = usage.cache_read_input_tokens or 0
        w = usage.cache_creation_input_tokens or 0
        o = usage.output_tokens or 0
        self.input += i
        self.cache_read += r
        self.cache_write += w
        self.output += o
        self.calls += 1
        self.last_prompt_tokens = i + r + w
        log(__file__, f"call {self.calls}: in={i} cache_read={r} cache_write={w} out={o} "
                      f"cost=${self._cost(i, r, w, o):.4f}")

    def _cost(self, i, r, w, o) -> float:
        p = self.price
        return (i * p["input"] + r * p["cache_read"] + w * p["cache_write"] + o * p["output"]) / 1e6

    @property
    def cost(self) -> float:
        return self._cost(self.input, self.cache_read, self.cache_write, self.output)

    def as_dict(self) -> dict:
        return {"input": self.input, "cache_read": self.cache_read,
                "cache_write": self.cache_write, "output": self.output}

    def report(self) -> None:
        log(__file__, f"turn total: {self.as_dict()} calls={self.calls} cost=${self.cost:.4f}")
