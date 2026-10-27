"""Domain tools for the junior hi-tech job-search agent.

Every tool returns a short plain-text string (compact output = fewer tokens).
Invalid requests raise ToolError; each harness turns that into an is_error result.

TOOL_SPECS holds the name / description / JSON schema of every tool, so both the
API and the SDK versions expose exactly the same tools to the model.
"""
from pathlib import Path

from . import jobs_source
from .store import Store

_DATA = Path(__file__).parent / "data"
# the real CV is git-ignored (personal details); the example keeps the repo runnable
CV_PATH = _DATA / "cv.md" if (_DATA / "cv.md").exists() else _DATA / "cv.example.md"
STATUSES = ("saved", "applied", "interview", "rejected", "offer")
KINDS = ("preference", "decision", "fact")


class ToolError(Exception):
    pass


def _line(j: dict) -> str:
    return f"{j['id']} | {j['title']} | {j['company']} | {j['location']} | {j['posted']}"


def search_jobs(store: Store, query: str, limit: int = 5, fetch=None) -> str:
    limit = max(1, min(int(limit), 10))
    kwargs = {"fetch": fetch} if fetch else {}
    try:
        results = jobs_source.search(query, limit=limit, **kwargs)
    except Exception as e:  # network / HTTP problems go back to the model
        raise ToolError(f"job board unavailable: {type(e).__name__}: {e}") from e
    if not results:
        return f"no junior-level jobs match '{query}'. Try fewer or broader words."
    store.add_seen(results)
    lines = [_line(j) for j in results]
    return f"{len(results)} jobs (source: Remotive)\n" + "\n".join(lines)


def save_job(store: Store, job_id: str, note: str = "") -> str:
    jobs = store.jobs()
    if job_id in jobs:
        raise ToolError(f"{job_id} is already in the tracker (status: {jobs[job_id]['status']})")
    seen = store.seen()
    if job_id not in seen:
        raise ToolError(f"unknown job id {job_id}. Use an id returned by search_jobs.")
    job = dict(seen[job_id], status="saved", note=note)
    jobs[job_id] = job
    store.save_jobs(jobs)
    return f"saved {job_id} ({job['title']} @ {job['company']})"


def list_jobs(store: Store, status: str = "") -> str:
    jobs = store.jobs()
    if status:
        if status not in STATUSES:
            raise ToolError(f"status must be one of {', '.join(STATUSES)}")
        jobs = {k: v for k, v in jobs.items() if v["status"] == status}
    if not jobs:
        return "tracker is empty" + (f" for status '{status}'" if status else "")
    return "\n".join(f"{_line(j)} | {j['status']}" for j in jobs.values())


def update_status(store: Store, job_id: str, status: str) -> str:
    jobs = store.jobs()
    if job_id not in jobs:
        raise ToolError(f"{job_id} is not in the tracker")
    if status not in STATUSES:
        raise ToolError(f"status must be one of {', '.join(STATUSES)}")
    old = jobs[job_id]["status"]
    jobs[job_id]["status"] = status
    store.save_jobs(jobs)
    return f"{job_id}: {old} -> {status}"


def apply_to_job(store: Store, job_id: str, cover_letter: str) -> str:
    """'Sends' the CV: writes the application (cover letter + CV) to the outbox."""
    jobs = store.jobs()
    if job_id not in jobs:
        raise ToolError(f"{job_id} is not in the tracker. save_job it first.")
    job = jobs[job_id]
    if job["status"] != "saved":
        raise ToolError(f"{job_id} already has status '{job['status']}'; not applying twice")
    if len(cover_letter.strip()) < 40:
        raise ToolError("cover_letter is too short; write a few tailored sentences")
    cv = CV_PATH.read_text(encoding="utf-8")
    text = (
        f"To: {job['company']}\nRole: {job['title']}\nApply at: {job['url']}\n\n"
        f"## Cover letter\n\n{cover_letter.strip()}\n\n## CV\n\n{cv}"
    )
    path = store.write_outbox(job_id, text)
    job["status"] = "applied"
    store.save_jobs(jobs)
    return f"application for {job_id} written to outbox/{path.name}; status -> applied"


def remember(store: Store, kind: str, key: str, value: str) -> str:
    if kind not in KINDS:
        raise ToolError(f"kind must be one of {', '.join(KINDS)}")
    key = key.strip().lower().replace(" ", "_")
    if not key or not value.strip():
        raise ToolError("key and value must not be empty")
    previous = store.remember(kind, key, value.strip())
    if previous is not None:
        return f"updated {key}: '{previous}' -> '{value.strip()}' (old value kept in history)"
    return f"remembered {kind} {key} = {value.strip()}"


def recall(store: Store, key: str = "") -> str:
    entries = store.profile()["entries"]
    if key:
        key = key.strip().lower().replace(" ", "_")
        if key not in entries:
            raise ToolError(f"nothing stored under '{key}'. Known keys: {', '.join(sorted(entries)) or 'none'}")
        e = entries[key]
        hist = "; ".join(f"was '{h['value']}'" for h in e["history"])
        return f"{key} ({e['kind']}) = {e['value']}" + (f" [{hist}]" if hist else "")
    if not entries:
        return "memory is empty"
    return "\n".join(f"{k} ({e['kind']}) = {e['value']}" for k, e in sorted(entries.items()))


def read_cv(store: Store) -> str:
    """File tool: the user's CV, read only when the model needs it (e.g. for a cover letter)."""
    text = "\n".join(line.strip() for line in CV_PATH.read_text(encoding="utf-8").splitlines() if line.strip())
    return text


FUNCTIONS = {
    "read_cv": read_cv,
    "search_jobs": search_jobs,
    "save_job": save_job,
    "list_jobs": list_jobs,
    "update_status": update_status,
    "apply_to_job": apply_to_job,
    "remember": remember,
    "recall": recall,
}


def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


TOOL_SPECS = [
    {
        "name": "search_jobs",
        "description": "Search live remote software job listings (Remotive) for junior/entry-level roles. "
                       "Senior roles are filtered out. Returns one line per job: id | title | company | location | date.",
        "input_schema": _obj({
            "query": {"type": "string", "description": "keywords, e.g. 'python' or 'react frontend'"},
            "limit": {"type": "integer", "description": "max results, 1-10 (default 5)"},
        }, ["query"]),
    },
    {
        "name": "read_cv",
        "description": "Read the user's CV file (skills, experience, projects). Use it before writing a cover letter.",
        "input_schema": _obj({}, []),
    },
    {
        "name": "save_job",
        "description": "Add a job from the last search results to the user's tracker (status 'saved').",
        "input_schema": _obj({
            "job_id": {"type": "string"},
            "note": {"type": "string", "description": "optional short note"},
        }, ["job_id"]),
    },
    {
        "name": "list_jobs",
        "description": "List jobs in the tracker, optionally filtered by status "
                       "(saved, applied, interview, rejected, offer).",
        "input_schema": _obj({"status": {"type": "string"}}, []),
    },
    {
        "name": "update_status",
        "description": "Change the status of a tracked job.",
        "input_schema": _obj({
            "job_id": {"type": "string"},
            "status": {"type": "string", "enum": list(STATUSES)},
        }, ["job_id", "status"]),
    },
    {
        "name": "apply_to_job",
        "description": "Send the user's CV to a saved job: writes the application (your tailored cover letter "
                       "+ the user's CV) to the outbox and sets status 'applied'. Never applies twice.",
        "input_schema": _obj({
            "job_id": {"type": "string"},
            "cover_letter": {"type": "string", "description": "3-6 sentences tailored to this job and the CV"},
        }, ["job_id", "cover_letter"]),
    },
    {
        "name": "remember",
        "description": "Save something to long-term memory (kept across sessions). Re-using a key replaces "
                       "the old value and keeps it in history - use that when the user changes their mind.",
        "input_schema": _obj({
            "kind": {"type": "string", "enum": list(KINDS)},
            "key": {"type": "string", "description": "short snake_case key, e.g. 'excluded_roles'"},
            "value": {"type": "string"},
        }, ["kind", "key", "value"]),
    },
    {
        "name": "recall",
        "description": "Read long-term memory. Without a key: all entries. With a key: that entry and its history.",
        "input_schema": _obj({"key": {"type": "string"}}, []),
    },
]

SYSTEM_PROMPT = """You are a job-search assistant for a junior software developer in Israel looking for their first hi-tech job.
You find junior roles, keep their job tracker, and send applications (CV + a short tailored cover letter) through your tools.

Rules:
- Before applying, check the job against the user's stored preferences. If a request conflicts with a stored preference, say so in one sentence; if the user is clearly changing their mind, update the memory with `remember` (same key) and then continue.
- Save anything the user states as a lasting preference, decision or fact with `remember`.
- Use `recall` when you need memory details that are not in the profile summary you are given.
- Only refer to jobs by ids that your tools returned. Do not invent listings.
- Reply briefly, in the user's language."""
