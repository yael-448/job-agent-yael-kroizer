"""Context-window management: once the prompt passes a threshold, summarize the whole
conversation into one message. Runs between turns, so no tool call is left half-done.

The summary request reuses the same tools + system prompt as normal calls, so it is
served mostly from the prompt cache. history.py records the compaction append-only.
"""
from . import caching, log

THRESHOLD_TOKENS = 12_000  # low on purpose so the 7-turn scenario can exercise it

SUMMARY_PROMPT = (
    "Summarize this conversation for your own future use, in at most 200 words: the user's goals, "
    "every job id discussed with its status, applications sent, and any open question. "
    "Stored preferences are in memory already; do not repeat them. Plain text only, no tool calls."
)


def needs_compaction(last_prompt_tokens: int) -> bool:
    return last_prompt_tokens > THRESHOLD_TOKENS


def compact(client, request: dict, system: list[dict], history, usage) -> None:
    n = len(history.messages)
    log(__file__, f"prompt reached {usage.last_prompt_tokens} tokens > {THRESHOLD_TOKENS}; summarizing {n} messages")
    sys_blocks, messages = caching.apply(system, history.messages + [{"role": "user", "content": SUMMARY_PROMPT}])
    resp = client.messages.create(**request, system=sys_blocks, messages=messages, tool_choice={"type": "none"})
    usage.add(resp.usage)
    summary = "".join(b.text for b in resp.content if b.type == "text").strip()
    history.append_compaction(summary, replaced=n)
    log(__file__, f"summary: {len(summary)} chars")
