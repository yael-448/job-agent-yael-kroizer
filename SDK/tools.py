"""The shared domain tools exposed to Claude Code as an in-process MCP server."""
from pathlib import Path

from claude_agent_sdk import create_sdk_mcp_server, tool

from shared.store import Store
from shared.tools_impl import FUNCTIONS, TOOL_SPECS, ToolError

SERVER = "jobs"
TOOL_NAMES = [f"mcp__{SERVER}__{s['name']}" for s in TOOL_SPECS]  # replaces: tools


def write_claude_md(store: Store) -> None:
    """Render profile.json as CLAUDE.md; Claude Code loads it at session start."""
    entries = store.profile()["entries"]  # replaces: memory
    lines = ["# User profile (long-term memory)", ""]  # replaces: memory
    lines += [f"- {k} ({e['kind']}): {e['value']}" for k, e in sorted(entries.items())] or ["- (empty)"]  # replaces: memory
    (store.dir / "CLAUDE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")  # replaces: memory


def _make(spec: dict, store: Store):
    name, fn = spec["name"], FUNCTIONS[spec["name"]]

    @tool(name, spec["description"], spec["input_schema"])  # replaces: tools
    async def handler(args: dict) -> dict:
        try:
            text = fn(store, **args)  # replaces: tools
        except (ToolError, TypeError) as e:
            return {"content": [{"type": "text", "text": f"error: {e}"}], "is_error": True}  # replaces: tools
        if name == "remember":
            write_claude_md(store)  # replaces: memory
        return {"content": [{"type": "text", "text": text}]}  # replaces: tools

    return handler


def build_server(state_dir: Path):
    store = Store(state_dir)
    write_claude_md(store)
    return create_sdk_mcp_server(SERVER, tools=[_make(s, store) for s in TOOL_SPECS])  # replaces: tools
