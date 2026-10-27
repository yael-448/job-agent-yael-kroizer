"""The same job-search agent on the Claude Agent SDK. Claude Code runs the harness;
this file only configures it. Lines marked `# replaces: <name>` stand in for API/harness/<name>.py.
"""
import asyncio
import json
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, ToolUseBlock

from shared.tools_impl import SYSTEM_PROMPT

from tools import SERVER, TOOL_NAMES, build_server

MODEL = "claude-opus-5-5"
EFFORT = "medium"


class SdkAgent:
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.session_file = self.state_dir / "sdk_session.json"
        resume = json.loads(self.session_file.read_text())["session_id"] if self.session_file.exists() else None  # replaces: history
        options = ClaudeAgentOptions(
            model=MODEL,
            effort=EFFORT,
            thinking={"type": "adaptive"},
            system_prompt=SYSTEM_PROMPT,  # replaces: context
            tools=[],  # no built-in Claude Code tools
            mcp_servers={SERVER: build_server(self.state_dir)},  # replaces: tools
            allowed_tools=TOOL_NAMES,  # replaces: tools
            strict_mcp_config=True,
            permission_mode="dontAsk",
            setting_sources=["project"],  # replaces: memory
            cwd=str(self.state_dir),  # replaces: memory
            resume=resume,  # replaces: history
        )
        print(f"[SDK/agent.py] agent ready: model={MODEL} effort={EFFORT} resume={resume}")
        self.runner = asyncio.Runner()
        self.client = ClaudeSDKClient(options)  # replaces: compaction, caching (both automatic in Claude Code)
        self.runner.run(self.client.connect())

    async def _turn(self, text: str) -> dict:
        await self.client.query(text)  # replaces: loop
        tools_called, call_ids, reply, result = [], set(), [], None
        async for msg in self.client.receive_response():  # replaces: loop
            if isinstance(msg, AssistantMessage):
                call_ids.add(msg.message_id)
                for b in msg.content:
                    if isinstance(b, ToolUseBlock):
                        tools_called.append(b.name.removeprefix(f"mcp__{SERVER}__"))
                        print(f"[SDK/agent.py] tool {b.name}({json.dumps(b.input, ensure_ascii=False)[:120]})")
                    elif getattr(b, "text", None):
                        reply.append(b.text)
            elif isinstance(msg, ResultMessage):
                result = msg
        usage = result.usage or {}  # replaces: tokens
        # total_cost_usd is cumulative for the session (also across resume), so take the delta
        prev = json.loads(self.session_file.read_text()).get("cost_so_far", 0.0) if self.session_file.exists() else 0.0
        turn_cost = (result.total_cost_usd or 0.0) - prev  # replaces: tokens
        self.session_file.write_text(json.dumps({"session_id": result.session_id,  # replaces: history
                                                 "cost_so_far": result.total_cost_usd or 0.0}))
        tokens = {
            "input": usage.get("input_tokens", 0),  # replaces: tokens
            "cache_read": usage.get("cache_read_input_tokens", 0),  # replaces: tokens
            "cache_write": usage.get("cache_creation_input_tokens", 0),  # replaces: tokens
            "output": usage.get("output_tokens", 0),  # replaces: tokens
        }
        print(f"[SDK/agent.py] result: {tokens} turn_cost=${turn_cost:.4f} turns={result.num_turns}")
        return {
            "reply": (result.result or "\n".join(reply)).strip(),
            "tokens": tokens,
            "model_calls": len(call_ids),
            "tools_called": tools_called,
            "cost_usd": round(turn_cost, 5),  # replaces: tokens
        }

    def run_turn(self, text: str) -> dict:
        return self.runner.run(self._turn(text))

    def close(self) -> None:
        self.runner.run(self.client.disconnect())
        self.runner.close()
