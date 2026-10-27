"""Offline tests of the SDK tool wrappers and of the scenario runner + checks."""
import asyncio
import json

from shared import runner, tools_impl
from shared.store import Store
from shared.tools_impl import TOOL_SPECS

import tools as sdk_tools


def _handler(name, store):
    spec = next(s for s in TOOL_SPECS if s["name"] == name)
    return sdk_tools._make(spec, store).handler


def test_sdk_tools_errors_and_claude_md(store):
    out = asyncio.run(_handler("save_job", store)({"job_id": "jb-404"}))
    assert out["is_error"] is True
    asyncio.run(_handler("remember", store)({"kind": "preference", "key": "role", "value": "backend"}))
    assert "role (preference): backend" in (store.dir / "CLAUDE.md").read_text(encoding="utf-8")
    assert sdk_tools.TOOL_NAMES[0] == "mcp__jobs__search_jobs"


class ScriptedAgent:
    """Performs the scenario's intended actions directly, to validate runner + checks."""
    def __init__(self, state_dir, fetch):
        self.store, self.fetch = Store(state_dir), fetch

    def run_turn(self, text):
        s, tools = self.store, []
        letter = "Dear team, I am a junior developer with Python, React and SQL experience."
        step = len(json.loads((s.dir / "steps.json").read_text())) if (s.dir / "steps.json").exists() else 0
        if step == 0:
            tools_impl.remember(s, "preference", "excluded_roles", "frontend"); tools = ["remember"]
        elif step == 1:
            tools_impl.search_jobs(s, "python", fetch=self.fetch)
            tools_impl.save_job(s, "jb-1"); tools_impl.save_job(s, "jb-3"); tools = ["search_jobs", "save_job"]
        elif step == 2:
            tools_impl.apply_to_job(s, "jb-1", letter); tools = ["apply_to_job"]
        elif step == 5:
            tools_impl.remember(s, "preference", "excluded_roles", "none")
            tools_impl.apply_to_job(s, "jb-3", letter); tools = ["remember", "apply_to_job"]
        (s.dir / "steps.json").write_text(json.dumps([0] * (step + 1)))
        reply = "You prefer backend roles." if step == 3 else "ok"
        return {"reply": reply, "tokens": {"input": 1, "cache_read": 0, "cache_write": 0, "output": 1},
                "model_calls": 1, "tools_called": tools, "cost_usd": 0.0}

    def close(self):
        pass


def test_runner_all_checks_pass_on_intended_behaviour(tmp_path, fake_fetch, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    out = tmp_path / "out.json"
    res = runner.run_scenario("fake", lambda d: ScriptedAgent(d, fake_fetch),
                              str(runner.Path(__file__).parent.parent / "scenario.json"), str(out))
    failed = [c for c in res["checks"] if not c["passed"]]
    assert not failed, failed
    assert len(res["checks"]) >= 5 and json.loads(out.read_text(encoding="utf-8"))["turns"][0]["id"] == "t1"


def test_loc_counts_cover_every_harness_file():
    loc = runner.count_loc()
    assert set(loc["api_harness"]) == {"loop", "tools", "history", "memory", "context", "compaction", "caching", "tokens"}
    assert {"loop", "tools", "history", "memory", "tokens"} <= set(loc["sdk_replaces"])
