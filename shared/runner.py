"""Scenario runner shared by API/main.py and SDK/main.py.

An agent factory is called once per session (session 2 = a fresh instance that must
load everything from disk). The agent exposes run_turn(text) -> dict and close().
"""
import ast
import json
import re
import shutil
import time
from pathlib import Path

from .checks import run_checks
from .store import Store

ROOT = Path(__file__).resolve().parent.parent


def snapshot(state_dir: Path) -> dict:
    store = Store(state_dir)
    outbox = sorted(p.name for p in (state_dir / "outbox").glob("*.md"))
    return {
        "jobs": {k: v["status"] for k, v in store.jobs().items()},
        "outbox": outbox,
        "outbox_text": {n: (state_dir / "outbox" / n).read_text(encoding="utf-8") for n in outbox},
        "profile": store.profile()["entries"],
        "seen_ids": sorted(store.seen()),
    }


def _code_lines(path: Path) -> int:
    """Lines of code, not counting blank lines, comments and docstrings."""
    src = path.read_text(encoding="utf-8")
    doc_lines: set[int] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                doc_lines.update(range(first.lineno, first.end_lineno + 1))
    return sum(1 for n, line in enumerate(src.splitlines(), start=1)
               if line.strip() and not line.strip().startswith("#") and n not in doc_lines)


def count_loc() -> dict:
    api = {p.stem: _code_lines(p) for p in sorted((ROOT / "API" / "harness").glob("*.py")) if p.stem != "__init__"}
    sdk: dict[str, int] = {}
    for p in sorted((ROOT / "SDK").glob("*.py")):
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.search(r"#\s*replaces:\s*([\w, .]+)", line)
            if m:
                for name in m.group(1).split(","):
                    name = name.strip().removesuffix(".py")
                    if name:
                        sdk[name] = sdk.get(name, 0) + 1
    return {
        "api_harness": api,
        "api_harness_total": sum(api.values()),
        "sdk_replaces": sdk,
        "sdk_total": sum(_code_lines(p) for p in (ROOT / "SDK").glob("*.py")),
        "shared_total": sum(_code_lines(p) for p in (ROOT / "shared").glob("*.py")),
    }


def run_scenario(impl: str, make_agent, scenario_path: str, out_path: str) -> dict:
    scenario = json.loads(Path(scenario_path).read_text(encoding="utf-8"))
    state_dir = ROOT / "results" / f"state_{impl}"
    if state_dir.exists():
        shutil.rmtree(state_dir)  # every run starts from a clean state
    state_dir.mkdir(parents=True)

    turns: dict[str, dict] = {}
    for s_idx, session in enumerate(scenario["sessions"], start=1):
        print(f"\n===== {impl.upper()} session {s_idx} (new agent instance) =====")
        agent = make_agent(state_dir)
        try:
            for turn in session["turns"]:
                print(f"\n--- {turn['id']} user: {turn['user']}")
                t0 = time.perf_counter()
                rec = agent.run_turn(turn["user"])
                rec["seconds"] = round(time.perf_counter() - t0, 2)
                rec.update(id=turn["id"], session=s_idx, user=turn["user"], state=snapshot(state_dir))
                turns[turn["id"]] = rec
                print(f"--- {turn['id']} reply: {rec['reply'][:400]}")
        finally:
            agent.close()

    checks = run_checks(scenario["checks"], turns)
    totals = {k: sum(t["tokens"][k] for t in turns.values())
              for k in ("input", "cache_read", "cache_write", "output")}
    prompt_total = totals["input"] + totals["cache_read"] + totals["cache_write"]
    result = {
        "impl": impl,
        "model": scenario["model"],
        "effort": scenario["effort"],
        "turns": [{k: v for k, v in t.items() if k != "state"} | {"state": _small_state(t["state"])}
                  for t in turns.values()],
        "totals": totals | {
            "cache_hit_pct": round(100 * totals["cache_read"] / prompt_total, 1) if prompt_total else 0.0,
            "model_calls": sum(t["model_calls"] for t in turns.values()),
            "cost_usd": round(sum(t["cost_usd"] for t in turns.values()), 4),
            "seconds": round(sum(t["seconds"] for t in turns.values()), 1),
        },
        "checks": checks,
        "checks_passed": f"{sum(c['passed'] for c in checks)}/{len(checks)}",
        "loc": count_loc(),
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nchecks passed: {result['checks_passed']}")
    for c in checks:
        print(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['id']}: {c['detail']}")
    print(f"totals: {result['totals']}\nwritten to {out_path}")
    return result


def _small_state(st: dict) -> dict:
    return {"jobs": st["jobs"], "outbox": st["outbox"],
            "profile": {k: e["value"] for k, e in st["profile"].items()}}
