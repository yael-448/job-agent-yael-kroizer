"""The agent loop: call the model; while stop_reason == "tool_use", run every requested
tool and send all tool_result blocks back in ONE user message."""
from . import caching, log

MAX_ROUNDS = 12  # safety stop for a runaway loop


def run(client, request: dict, system: list[dict], history, toolbox, usage) -> tuple[str, list[str]]:
    tools_called: list[str] = []
    for round_no in range(1, MAX_ROUNDS + 1):
        sys_blocks, messages = caching.apply(system, history.messages)
        log(__file__, f"round {round_no}: calling model with {len(messages)} messages")
        resp = client.messages.create(**request, system=sys_blocks, messages=messages)
        usage.add(resp.usage)
        history.append("assistant", resp.content)  # full content, thinking blocks included
        log(__file__, f"stop_reason={resp.stop_reason}")

        if resp.stop_reason != "tool_use":
            if resp.stop_reason in ("max_tokens", "refusal"):
                log(__file__, f"turn ended early: {resp.stop_reason}")
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            return text, tools_called

        uses = [b for b in resp.content if b.type == "tool_use"]
        tools_called += [b.name for b in uses]
        results = [toolbox.run(b) for b in uses]
        history.append("user", results)  # all results together, in one message
    log(__file__, f"stopped after {MAX_ROUNDS} rounds")
    return "(stopped: too many tool rounds)", tools_called
