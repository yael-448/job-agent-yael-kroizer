import pytest

from shared import jobs_source
from shared.tools_impl import ToolError, apply_to_job, list_jobs, recall, remember, save_job, search_jobs


def test_search_filters_seniors_and_puts_juniors_first(fake_fetch):
    res = jobs_source.search("python", fetch=fake_fetch)
    assert [r["id"] for r in res] == ["jb-1", "jb-3"]
    assert all(r["source"] == "jobicy" and r["url"] for r in res)


def test_search_output_is_compact(store, fake_fetch):
    out = search_jobs(store, "python", fetch=fake_fetch)
    assert out.splitlines()[1].startswith("jb-1 | Junior Python Developer | Acme")
    assert "Backend work" not in out  # descriptions never reach the model


def test_save_apply_and_no_double_apply(store, fake_fetch):
    search_jobs(store, "python", fetch=fake_fetch)
    with pytest.raises(ToolError):
        save_job(store, "jb-999")
    save_job(store, "jb-1")
    with pytest.raises(ToolError):
        save_job(store, "jb-1")
    apply_to_job(store, "jb-1", "I am a junior Python developer and would love to join Acme's backend team.")
    assert (store.dir / "outbox" / "jb-1.md").read_text(encoding="utf-8").count("## CV") == 1
    with pytest.raises(ToolError):
        apply_to_job(store, "jb-1", "Applying a second time to the very same job, which must be refused.")
    assert "applied" in list_jobs(store)


def test_remember_keeps_history_on_change(store):
    remember(store, "preference", "excluded_roles", "frontend")
    out = remember(store, "preference", "excluded roles", "none")
    assert "'frontend' -> 'none'" in out
    assert "was 'frontend'" in recall(store, "excluded_roles")


def test_read_cv_returns_the_cv_without_blank_lines(store):
    from shared.tools_impl import read_cv
    out = read_cv(store)
    assert out and "\n\n" not in out
