"""cache_control breakpoints (max 4 per request; this harness uses 2).

1. last system block  -> caches tools + system prompt (render order: tools, system, messages)
2. last block of the last message -> caches the whole conversation so far; the next
   call (next tool round or next turn) reads it back and only pays for the new tail.

Markers are added to a copy of the messages, so history on disk never changes.
"""
import copy

from . import log

EPHEMERAL = {"type": "ephemeral"}


def apply(system: list[dict], messages: list[dict]) -> tuple[list[dict], list[dict]]:
    system = copy.deepcopy(system)
    system[-1]["cache_control"] = EPHEMERAL
    messages = copy.deepcopy(messages)
    last = messages[-1]
    if isinstance(last["content"], str):
        last["content"] = [{"type": "text", "text": last["content"]}]
    last["content"][-1]["cache_control"] = EPHEMERAL
    log(__file__, f"breakpoints: system[-1], messages[{len(messages) - 1}].content[-1]")
    return system, messages
