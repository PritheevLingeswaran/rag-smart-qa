# Contributing

## Setup
```bash
make install
cp .env.example .env
```

## Quality gates
- `make lint` (ruff on `src`, `tests`, and `evaluation/resume_metrics.py`)
- `make typecheck` (mypy on the same maintained paths)
- `make test` (pytest)

CI runs three separate jobs:
- `lint` on Python 3.11
- `typecheck` on Python 3.11
- `test` on Python 3.11

Workflow behavior:
- Pull requests run CI for every update.
- Pushes run CI only on `main`, which avoids duplicate `push` + `pull_request` runs for the same feature-branch commit.
- Superseded runs on the same PR or branch are cancelled automatically so only the newest run continues.

To reproduce the GitHub Actions pipeline locally from a clean checkout:
```bash
python3.11 -m venv .ci-venv
source .ci-venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m pip install -e .
make lint
make typecheck
RAG_SKIP_STARTUP_VALIDATION=1 OPENAI_API_KEY=test OPENAI_BASE_URL=http://localhost:9999/v1 OPENAI_ORG='' make test
```

## Expectations
- Keep behavior config-driven.
- Add tests for new logic.
- Prefer simple, explicit code over framework magic.
