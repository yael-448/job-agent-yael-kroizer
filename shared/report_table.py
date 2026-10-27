"""Print the API-vs-SDK comparison tables (markdown) from results/*.json.

    python -m shared.report_table
"""
import json

from .runner import ROOT


def _load(name: str) -> dict | None:
    p = ROOT / "results" / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main() -> None:
    api, sdk = _load("api"), _load("sdk")

    def cell(r, key):
        if r is None:
            return "pending"
        t = r["totals"]
        return {
            "tokens": f"{t['input']:,} / {t['cache_read']:,} / {t['cache_write']:,} / {t['output']:,}",
            "cache": f"{t['cache_hit_pct']}%",
            "calls": str(t["model_calls"]),
            "cost": f"${t['cost_usd']:.4f}",
            "time": f"{t['seconds']}s",
            "checks": r["checks_passed"],
        }[key]

    rows = [("Tokens (input / cache read / cache write / output)", "tokens"), ("Cache share of prompt", "cache"),
            ("Model calls", "calls"), ("Cost", "cost"), ("Time", "time"), ("Checks passed", "checks")]
    print("| | API | SDK |\n|---|---|---|")
    for label, key in rows:
        print(f"| {label} | {cell(api, key)} | {cell(sdk, key)} |")

    loc = (sdk or api)["loc"]
    print("\n| Harness part | API (lines) | SDK (lines marked `# replaces`) |\n|---|---|---|")
    for part, n in loc["api_harness"].items():
        print(f"| {part} | {n} | {loc['sdk_replaces'].get(part, 0)} |")
    print(f"| **Total** | **{loc['api_harness_total']}** | **{sum(loc['sdk_replaces'].values())}** |")


if __name__ == "__main__":
    main()
