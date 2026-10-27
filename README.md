# Job-search agent: one agent, two harnesses

An agent that finds junior hi-tech jobs, keeps a job tracker, remembers preferences
across sessions, and sends applications (a tailored cover letter plus the CV) to an outbox.
It is built twice:

- `API/` uses the raw Messages API. The whole harness is hand-written in `API/harness/`, one file per responsibility.
- `SDK/` uses the Claude Agent SDK. Claude Code runs the harness, and `SDK/` only configures it. Each line that replaces a harness file is marked `# replaces: <name>`.

Both versions use the same domain code in `shared/`: the tools, the state on disk, the live job board (Jobicy), the scenario runner and the checks.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Put your CV in `shared/data/cv.md`. That file is git-ignored. If it is missing, `cv.example.md` is used.

## Run

```powershell
# offline tests, no key needed
.venv\Scripts\python -m pytest -q tests

# SDK version: runs on your Claude Code login (ANTHROPIC_API_KEY must not be set)
.venv\Scripts\python SDK/main.py --scenario scenario.json --out results/sdk.json

# API version: needs a Claude Console key, set only in the terminal
$env:ANTHROPIC_API_KEY = "sk-ant-..."
.venv\Scripts\python API/main.py --scenario scenario.json --out results/api.json
```

Both runs use `claude-opus-5-5` with effort `medium`, and each run starts from a clean state in `results/state_<impl>/`.

## Tools

| Tool | What it does |
|---|---|
| `search_jobs` | External: live remote dev jobs from the Jobicy API, with senior roles filtered out |
| `read_cv` | File: reads the user's CV |
| `save_job`, `list_jobs`, `update_status` | The job tracker (`jobs.json`) |
| `apply_to_job` | Writes the cover letter plus the CV to `outbox/` and marks the job as applied. It never applies twice. |
| `remember`, `recall` | Long-term memory (`profile.json`). Old values are kept in history. |

Applications are written to the outbox and are not sent to employers automatically. Job boards forbid automated submissions, so the user reviews each application and sends it.

See `REPORT.md` for the comparison between the two versions.
