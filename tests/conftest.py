import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "API"), str(ROOT / "SDK")]

FAKE_JOBS = [
    {"id": 1, "url": "https://jobicy.com/jobs/1", "jobTitle": "Junior Python Developer", "companyName": "Acme",
     "jobGeo": "Israel", "jobLevel": "Any", "pubDate": "2026-10-20 10:00:00", "jobExcerpt": "Python, SQL",
     "jobDescription": "Backend work in Python and SQL"},
    {"id": 2, "url": "https://jobicy.com/jobs/2", "jobTitle": "Senior Python Engineer", "companyName": "Big",
     "jobGeo": "Anywhere", "jobLevel": "Senior", "pubDate": "2026-10-21 10:00:00", "jobExcerpt": "Python",
     "jobDescription": "Python"},
    {"id": 3, "url": "https://jobicy.com/jobs/3", "jobTitle": "Frontend Engineer", "companyName": "Pixel",
     "jobGeo": "EMEA", "jobLevel": "Any", "pubDate": "2026-10-22 10:00:00", "jobExcerpt": "React",
     "jobDescription": "React and TypeScript, some Python tooling"},
]


@pytest.fixture
def fake_fetch():
    return lambda: FAKE_JOBS


@pytest.fixture
def store(tmp_path):
    from shared.store import Store
    return Store(tmp_path)
