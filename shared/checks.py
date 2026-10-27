"""Pass/fail checks declared in scenario.json. Most of them inspect the saved state
(snapshots taken after each turn), not only the reply text."""


def _snap(turns: dict, tid: str) -> dict:
    return turns[tid]["state"]


def _profile_text(state: dict) -> str:
    return " ".join(f"{k} {e['value']}" for k, e in state["profile"].items()).lower()


def run_check(c: dict, turns: dict) -> tuple[bool, str]:
    kind = c["kind"]
    if kind == "tool_called":
        tids = [t for t, r in turns.items() if r["session"] == c["session"]]
        used = sorted({name for t in tids for name in turns[t]["tools_called"]})
        return c["tool"] in used, f"tools in session {c['session']}: {used}"
    if kind == "seen_jobs_from_source":
        ids = _snap(turns, c["after_turn"])["seen_ids"]
        ok = any(i.startswith(c["prefix"]) for i in ids)
        return ok, f"{len(ids)} listings fetched"
    if kind == "jobs_at_least":
        jobs = _snap(turns, c["after_turn"])["jobs"]
        return len(jobs) >= c["min"], f"{len(jobs)} jobs in tracker"
    if kind == "outbox_count":
        box = _snap(turns, c["after_turn"])["outbox"]
        return len(box) == c["equals"], f"outbox: {box}"
    if kind == "outbox_contains":
        st = _snap(turns, c["after_turn"])
        texts = st["outbox_text"]
        ok = bool(texts) and all(c["text"] in t for t in texts.values())
        applied = [j for j, s in st["jobs"].items() if s == "applied"]
        ok = ok and sorted(applied) == sorted(f.removesuffix(".md") for f in texts)
        return ok, f"applied jobs {applied}"
    if kind == "profile_mentions":
        text = _profile_text(_snap(turns, c["after_turn"]))
        hits = [w for w in c["any"] if w.lower() in text]
        return bool(hits), f"matched {hits}"
    if kind == "profile_changed":
        prof = _snap(turns, c["after_turn"])["profile"]
        changed = [k for k, e in prof.items() if e["history"]]
        return bool(changed), f"entries with history: {changed}"
    if kind == "reply_mentions":
        reply = turns[c["turn"]]["reply"].lower()
        hits = [w for w in c["any"] if w.lower() in reply]
        return bool(hits), f"matched {hits}"
    raise ValueError(f"unknown check kind {kind}")


def run_checks(checks: list[dict], turns: dict) -> list[dict]:
    out = []
    for c in checks:
        try:
            ok, detail = run_check(c, turns)
        except KeyError as e:
            ok, detail = False, f"missing data: {e}"
        out.append({"id": c["id"], "description": c["description"], "passed": ok, "detail": detail})
    return out
