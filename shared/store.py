"""Domain state on disk, shared by the API and SDK versions.

Layout of a state directory:
  profile.json   long-term memory: preferences / decisions / facts, with change history
  jobs.json      the job tracker (saved / applied jobs)
  seen.json      the last search results, so save/apply can refer to jobs by id
  outbox/        one file per application (cover letter + CV), the "sent" CVs
"""
import json
import time
from pathlib import Path


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class Store:
    def __init__(self, state_dir: str | Path):
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "outbox").mkdir(exist_ok=True)

    # -- generic json helpers -------------------------------------------------
    def _read(self, name: str, default):
        p = self.dir / name
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))

    def _write(self, name: str, data) -> None:
        p = self.dir / name
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(p)

    # -- profile (memory) -----------------------------------------------------
    def profile(self) -> dict:
        return self._read("profile.json", {"entries": {}})

    def remember(self, kind: str, key: str, value: str) -> str | None:
        """Store an entry. Returns the previous value if this replaced a different one."""
        prof = self.profile()
        entries = prof["entries"]
        old = entries.get(key)
        previous = None
        history = []
        if old:
            history = old.get("history", [])
            if old["value"] != value:
                previous = old["value"]
                history.append({"value": old["value"], "replaced_at": _now()})
        entries[key] = {"kind": kind, "value": value, "updated_at": _now(), "history": history}
        self._write("profile.json", prof)
        return previous

    # -- jobs -----------------------------------------------------------------
    def jobs(self) -> dict:
        return self._read("jobs.json", {})

    def save_jobs(self, jobs: dict) -> None:
        self._write("jobs.json", jobs)

    def seen(self) -> dict:
        return self._read("seen.json", {})

    def add_seen(self, results: list[dict]) -> None:
        seen = self.seen()
        for r in results:
            seen[r["id"]] = r
        self._write("seen.json", seen)

    def write_outbox(self, job_id: str, text: str) -> Path:
        p = self.dir / "outbox" / f"{job_id}.md"
        p.write_text(text, encoding="utf-8")
        return p
