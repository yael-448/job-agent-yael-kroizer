"""External tool backend: live remote dev job listings from the Jobicy public API.

Jobicy asks clients to credit Jobicy and link to the original job URL, so every result
carries `source` and `url`. The raw feed is cached on disk for CACHE_TTL seconds
(polite to the API, and repeated searches cost no network); filtering is done locally.
"""
import html
import json
import re
import time
from pathlib import Path

import httpx

JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_TTL = 12 * 3600

SENIOR = re.compile(r"\b(senior|sr\.?|lead|staff|principal|head|director|manager|architect|vp|vice president)\b", re.I)
JUNIOR = re.compile(r"\b(junior|jr\.?|entry|new grad|graduate|intern(ship)?|trainee|associate|student)\b", re.I)
SENIOR_LEVELS = {"Senior", "Director", "Lead", "Manager"}


def _fetch() -> list[dict]:
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / "jobicy_dev.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < CACHE_TTL:
        return json.loads(cache.read_text(encoding="utf-8"))
    resp = httpx.get(JOBICY_URL, params={"count": 100, "industry": "dev"}, timeout=30,
                     headers={"User-Agent": "job-agent-student/1.0"})
    resp.raise_for_status()
    jobs = resp.json().get("jobs", [])
    cache.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
    return jobs


def _compact(j: dict) -> dict:
    return {
        "id": f"jb-{j['id']}",
        "title": html.unescape(j.get("jobTitle", "")).strip(),
        "company": html.unescape(j.get("companyName", "")).strip(),
        "location": re.sub(r"\s+", " ", j.get("jobGeo") or "Remote").strip(),
        "level": j.get("jobLevel") or "Any",
        "posted": (j.get("pubDate") or "")[:10],
        "url": j.get("url", ""),
        "source": "jobicy",
    }


def is_junior_friendly(j: dict) -> bool:
    return not SENIOR.search(j.get("jobTitle", "")) and j.get("jobLevel") not in SENIOR_LEVELS


def search(query: str, limit: int = 5, fetch=_fetch) -> list[dict]:
    """Return up to `limit` non-senior jobs matching all words of `query`, juniors first, newest first."""
    terms = [re.compile(rf"(?<!\w){re.escape(t)}(?!\w)", re.I) for t in query.split() if t.strip()]
    matches = []
    for j in fetch():
        if not is_junior_friendly(j):
            continue
        hay = " ".join([j.get("jobTitle", ""), j.get("jobExcerpt", ""), html.unescape(j.get("jobDescription", ""))])
        if all(t.search(hay) for t in terms):
            matches.append(j)
    matches.sort(key=lambda j: j.get("pubDate", ""), reverse=True)
    matches.sort(key=lambda j: not JUNIOR.search(j.get("jobTitle", "")))  # stable: juniors first
    return [_compact(j) for j in matches[:limit]]
