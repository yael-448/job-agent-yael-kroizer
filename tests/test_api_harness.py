"""Offline tests of the API harness with a scripted fake client (no key, no network)."""
import json

from anthropic.types import Message

from agent import ApiAgent
from harness import compaction


def _msg(content, stop, usage=(100, 0, 0, 20)):
    i, r, w, o = usage
    return Message.model_validate({
        "id": "msg_x", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "content": content, "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": i, "cache_read_input_tokens": r, "cache_creation_input_tokens": w, "output_tokens": o},
    })


def _tool(id_, name, inp):
    return {"type": "tool_use", "id": id_, "name": name, "input": inp}


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.messages = self

    def create(self, **req):
        self.requests.append(json.loads(json.dumps(req, default=str)))
        return self.script.pop(0)


def test_loop_runs_tools_and_returns_all_results_in_one_message(tmp_path, fake_fetch):
    client = FakeClient([
        _msg([{"type": "thinking", "thinking": "", "signature": "sig"},
              _tool("t1", "remember", {"kind": "preference", "key": "excluded_roles", "value": "frontend"}),
              _tool("t2", "search_jobs", {"query": "python"}),
              _tool("t3", "save_job", {"job_id": "jb-404"})], "tool_use"),
        _msg([{"type": "text", "text": "Done."}], "end_turn", usage=(10, 500, 0, 5)),
    ])
    agent = ApiAgent(client, tmp_path, fetch=fake_fetch)
    rec = agent.run_turn("remember: no frontend, and find python jobs")

    assert rec["reply"] == "Done."
    assert rec["model_calls"] == 2
    assert rec["tools_called"] == ["remember", "search_jobs", "save_job"]
    second = client.requests[1]["messages"]
    results = second[-1]["content"]
    assert [b["type"] for b in results] == ["tool_result"] * 3          # one user message
    assert results[2].get("is_error") is True                            # unknown id -> is_error
    assert second[-2]["content"][0]["type"] == "thinking"                # thinking passed back unchanged
    assert rec["tokens"] == {"input": 110, "cache_read": 500, "cache_write": 0, "output": 25}
    assert abs(rec["cost_usd"] - (110 * 4 + 500 * 0.2 + 25 * 20) / 1e6) < 1e-9


def test_cache_breakpoints_and_context_injection(tmp_path, fake_fetch):
    client = FakeClient([_msg([{"type": "text", "text": "hi"}], "end_turn")])
    ApiAgent(client, tmp_path, fetch=fake_fetch).run_turn("hello")
    req = client.requests[0]
    assert req["system"][-1]["cache_control"] == {"type": "ephemeral"}
    last = req["messages"][-1]["content"]
    assert last[-1]["cache_control"] == {"type": "ephemeral"}
    assert last[0]["text"].startswith("<context>")
    assert req["output_config"] == {"effort": "medium"} and req["model"] == "claude-opus-5-5"
    # markers live only in the request copy, never in the history file
    assert "cache_control" not in (tmp_path / "api_history.jsonl").read_text(encoding="utf-8")


def test_new_instance_loads_history_and_memory_from_disk(tmp_path, fake_fetch):
    c1 = FakeClient([
        _msg([_tool("t1", "remember", {"kind": "preference", "key": "role", "value": "backend"})], "tool_use"),
        _msg([{"type": "text", "text": "ok"}], "end_turn"),
    ])
    ApiAgent(c1, tmp_path, fetch=fake_fetch).run_turn("I want backend")
    c2 = FakeClient([_msg([{"type": "text", "text": "backend"}], "end_turn")])
    agent2 = ApiAgent(c2, tmp_path, fetch=fake_fetch)
    assert len(agent2.history.messages) == 4
    agent2.run_turn("what do I want?")
    sent = c2.requests[0]["messages"]
    assert len(sent) == 5
    assert "role (preference): backend" in sent[-1]["content"][0]["text"]


def test_compaction_summarizes_and_is_append_only(tmp_path, fake_fetch):
    client = FakeClient([
        _msg([{"type": "text", "text": "first"}], "end_turn", usage=(compaction.THRESHOLD_TOKENS + 1, 0, 0, 5)),
        _msg([{"type": "text", "text": "SUMMARY: user wants backend"}], "end_turn"),
        _msg([{"type": "text", "text": "second"}], "end_turn"),
    ])
    agent = ApiAgent(client, tmp_path, fetch=fake_fetch)
    agent.run_turn("one")
    agent.run_turn("two")
    assert client.requests[1]["tool_choice"] == {"type": "none"}
    sent = client.requests[2]["messages"]
    assert "SUMMARY: user wants backend" in sent[0]["content"][0]["text"]
    assert len(sent) == 2
    records = [json.loads(l) for l in (tmp_path / "api_history.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["type"] for r in records] == ["message", "message", "compaction", "message", "message"]
    assert len(ApiAgent(FakeClient([]), tmp_path).history.messages) == 3
